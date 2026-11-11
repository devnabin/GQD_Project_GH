# Created date: 2026-11-10 (America/Chicago)
"""Train the xTB HOMO-LUMO gap predictor (ensemble + uncertainty).

Input : data/features_labelled.parquet (from build_features.py)
Output: models/  - huckel_linear.json, lgbm_fold*.txt, xgb_fold*.json, gnn_fold*.pt,
                   error_model.txt, ensemble.json (features, weights, scaling, calibration)
        results/ - metrics.json, test_predictions.csv, train.log, gnn.log

Steps
  1. Fixed split: 90% development / 10% test, stratified by gap (data/split.csv;
     the development part is further split 80/10 train/val for tuning).
  2. Baseline: xTB gap ≈ a·(Hückel gap) + b.
  3. All ML models predict the RESIDUAL (xTB - baseline). LightGBM and XGBoost
     are Optuna-tuned on train/val. Then 5-fold cross-validation on the
     development set: per fold one LightGBM, one XGBoost and one GNN
     (GNNs run in parallel in separate processes, see train_gnn.py).
     This gives honest out-of-fold (OOF) predictions for every structure.
  4. Ensemble = weighted mean of the three model types (weights fitted on OOF).
  5. Uncertainty = error model (LightGBM) predicting |error| from the features
     and the disagreement between model types; scaled on OOF so that
     ±1.96·σ covers 95% of errors.
  6. Test-set report + extrapolation checks (gap tails, larger sizes).

Usage (from Agentic_GQD/):  .venv/bin/python Stage2/train.py [--trials 100] [--folds 5] [--gnn-epochs 300]
"""

import argparse
import json
import sys
import time
import subprocess
from pathlib import Path

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr
from sklearn.model_selection import StratifiedKFold, train_test_split

HERE = Path(__file__).resolve().parent

DATA = HERE / "data" / "features_labelled.parquet"
SPLIT = HERE / "data" / "split.csv"
MODELS = HERE / "models"
RESULTS = HERE / "results"
PHYSICS_PREFIXES = ("huckel", "orb", "kekule", "clar", "edge", "perim", "hole", "shape")
LOG_FILE = None


def log(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    if LOG_FILE:
        with open(LOG_FILE, "a") as handle:
            handle.write(line + "\n")


def metrics(true: np.ndarray, pred: np.ndarray) -> dict:
    err = pred - true
    return {"n": int(len(true)), "MAE": float(np.abs(err).mean()), "RMSE": float(np.sqrt((err ** 2).mean())),
            "R2": float(1 - (err ** 2).sum() / ((true - true.mean()) ** 2).sum()),
            "max_abs_error": float(np.abs(err).max())}


def make_split(y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = np.arange(len(y))
    bins = pd.qcut(y, 10, labels=False)
    train, test = train_test_split(idx, test_size=0.10, random_state=42, stratify=bins)
    train, val = train_test_split(train, test_size=1 / 9, random_state=42, stratify=bins[train])
    return np.sort(train), np.sort(val), np.sort(test)


# ---------------------------------------------------------------------------
# Gradient boosting
# ---------------------------------------------------------------------------
def tune_lgbm(X, r, tr, va, trials):
    def objective(trial):
        params = dict(
            n_estimators=20000, learning_rate=trial.suggest_float("learning_rate", 0.005, 0.08, log=True),
            num_leaves=trial.suggest_int("num_leaves", 15, 255, log=True),
            min_child_samples=trial.suggest_int("min_child_samples", 3, 80, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0), subsample_freq=1,
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 1.0),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-8, 5.0, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-8, 5.0, log=True),
            objective=trial.suggest_categorical("objective", ["l2", "huber", "l1"]),
            verbose=-1, n_jobs=8, random_state=0)
        model = lgb.LGBMRegressor(**params)
        model.fit(X[tr], r[tr], eval_set=[(X[va], r[va])], eval_metric="l1",
                  callbacks=[lgb.early_stopping(300, verbose=False)])
        trial.set_user_attr("best_iteration", model.best_iteration_)
        return float(np.abs(model.predict(X[va]) - r[va]).mean())

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=0))
    study.optimize(objective, n_trials=trials)
    log(f"  LightGBM best val MAE (residual) {study.best_value:.4f}  params {study.best_params}")
    return study.best_params


def tune_xgb(X, r, tr, va, trials):
    def objective(trial):
        params = dict(
            n_estimators=20000, learning_rate=trial.suggest_float("learning_rate", 0.005, 0.08, log=True),
            max_depth=trial.suggest_int("max_depth", 3, 12),
            min_child_weight=trial.suggest_float("min_child_weight", 0.5, 30, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 1.0),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-8, 5.0, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-8, 5.0, log=True),
            objective=trial.suggest_categorical("objective", ["reg:squarederror", "reg:pseudohubererror", "reg:absoluteerror"]),
            tree_method="hist", early_stopping_rounds=300, eval_metric="mae", n_jobs=8, random_state=0)
        model = xgb.XGBRegressor(**params)
        model.fit(X[tr], r[tr], eval_set=[(X[va], r[va])], verbose=False)
        return float(np.abs(model.predict(X[va]) - r[va]).mean())

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=0))
    study.optimize(objective, n_trials=trials)
    log(f"  XGBoost best val MAE (residual) {study.best_value:.4f}  params {study.best_params}")
    return study.best_params


def fit_lgbm(params, X, r, tr, va, seed):
    model = lgb.LGBMRegressor(n_estimators=20000, subsample_freq=1, verbose=-1, n_jobs=8,
                              random_state=seed, **params)
    model.fit(X[tr], r[tr], eval_set=[(X[va], r[va])], eval_metric="l1",
              callbacks=[lgb.early_stopping(300, verbose=False)])
    return model


def fit_xgb(params, X, r, tr, va, seed):
    model = xgb.XGBRegressor(n_estimators=20000, tree_method="hist", early_stopping_rounds=300,
                             eval_metric="mae", n_jobs=8, random_state=seed, **params)
    model.fit(X[tr], r[tr], eval_set=[(X[va], r[va])], verbose=False)
    return model


# ---------------------------------------------------------------------------
def main():
    global LOG_FILE
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=100, help="Optuna trials per boosting model")
    parser.add_argument("--folds", type=int, default=5, help="cross-validation folds = ensemble members per model type")
    parser.add_argument("--gnn-epochs", type=int, default=300, help="max GNN epochs (early stopping)")
    args = parser.parse_args()

    MODELS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    LOG_FILE = RESULTS / "train.log"
    LOG_FILE.write_text("")
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    df = pd.read_parquet(DATA)
    features = [c for c in df.columns if c.split("_")[0] in PHYSICS_PREFIXES]
    X = df[features].to_numpy(np.float32)
    y = df["xtb_gap_eV"].to_numpy(float)
    tr, va, te = make_split(y)
    pd.DataFrame({"Structure_Name": df["Structure_Name"],
                  "split": np.select([np.isin(np.arange(len(y)), tr), np.isin(np.arange(len(y)), va)],
                                     ["train", "val"], "test")}).to_csv(SPLIT, index=False)
    log(f"{len(y):,} structures, {len(features)} physics features; train {len(tr)}, val {len(va)}, test {len(te)}")

    dev = np.sort(np.concatenate([tr, va]))  # everything except the test set

    # 1. Hückel baseline -----------------------------------------------------
    slope, intercept = np.polyfit(df["huckel_gap"].to_numpy()[dev], y[dev], 1)
    baseline = slope * df["huckel_gap"].to_numpy() + intercept
    r = y - baseline
    (MODELS / "huckel_linear.json").write_text(json.dumps({"slope": slope, "intercept": intercept}))
    log(f"Hückel baseline: gap = {slope:.4f}·huckel + {intercept:.4f}; test {metrics(y[te], baseline[te])}")

    # 2. Hyper-parameter tuning on the train/val split ------------------------
    log(f"Tuning LightGBM ({args.trials} trials)...")
    lgbm_params = tune_lgbm(X, r, tr, va, args.trials)
    log(f"Tuning XGBoost ({args.trials} trials)...")
    xgb_params = tune_xgb(X, r, tr, va, args.trials)

    # 3. K-fold ensemble: each fold model never sees its own fold -------------
    #    -> honest out-of-fold (OOF) predictions for every non-test structure.
    folds = list(StratifiedKFold(args.folds, shuffle=True, random_state=42)
                 .split(dev, pd.qcut(y[dev], 10, labels=False)))
    fold_sets = []
    for k, (fit_pos, hold_pos) in enumerate(folds):
        fit, hold = dev[fit_pos], dev[hold_pos]
        fit_tr, fit_es = train_test_split(fit, test_size=0.1, random_state=k)  # es = early stopping
        fold_sets.append((fit_tr, fit_es, hold))

    members: dict[str, list[np.ndarray]] = {"lgbm": [], "xgb": [], "gnn": []}
    for k, (fit_tr, fit_es, hold) in enumerate(fold_sets):
        m = fit_lgbm(lgbm_params, X, r, fit_tr, fit_es, k)
        m.booster_.save_model(str(MODELS / f"lgbm_fold{k}.txt"))
        members["lgbm"].append(m.predict(X))
        m = fit_xgb(xgb_params, X, r, fit_tr, fit_es, k)
        m.save_model(str(MODELS / f"xgb_fold{k}.json"))
        members["xgb"].append(m.predict(X))
        log(f"  fold {k}: LGBM held-out MAE {np.abs(r[hold] - members['lgbm'][-1][hold]).mean():.4f}, "
            f"XGB held-out MAE {np.abs(r[hold] - members['xgb'][-1][hold]).mean():.4f}")

    mean, std = X[dev].mean(axis=0), X[dev].std(axis=0) + 1e-8
    globals_ = np.nan_to_num((X - mean) / std).astype(np.float32)
    log(f"Training {args.folds} GNNs in parallel processes (progress in results/gnn.log)...")
    (RESULTS / "gnn.log").write_text("")
    processes = []
    for k, (fit_tr, fit_es, hold) in enumerate(fold_sets):
        inputs = HERE / "data" / f"gnn_inputs_fold{k}.npz"
        np.savez(inputs, smiles=df["SMILES"].to_numpy(), globals=globals_, residual=r.astype(np.float32),
                 train_idx=fit_tr, val_idx=fit_es)
        command = [sys.executable, str(HERE / "train_gnn.py"), "--inputs", str(inputs), "--seed", str(k),
                   "--model", str(MODELS / f"gnn_fold{k}.pt"), "--preds", str(RESULTS / f"gnn_preds_fold{k}.npy"),
                   "--log", str(RESULTS / "gnn.log"), "--epochs", str(args.gnn_epochs)]
        processes.append(subprocess.Popen(command))
    for k, process in enumerate(processes):
        if process.wait() != 0:
            raise RuntimeError(f"GNN fold {k} failed; see results/gnn.log")
        members["gnn"].append(np.load(RESULTS / f"gnn_preds_fold{k}.npy"))
        hold = fold_sets[k][2]
        log(f"  fold {k}: GNN held-out MAE {np.abs(r[hold] - members['gnn'][-1][hold]).mean():.4f}")

    # Per model type: OOF prediction on dev, fold-average on test/new structures.
    oof = {t: np.zeros(len(y)) for t in members}
    for t, preds in members.items():
        for k, (_, _, hold) in enumerate(fold_sets):
            oof[t][hold] = preds[k][hold]
        oof[t][te] = np.mean(preds, axis=0)[te]

    # 4. Ensemble weights (fitted on OOF) --------------------------------------
    best_w, best_mae = None, np.inf
    for w1 in np.arange(0, 1.001, 0.05):
        for w2 in np.arange(0, 1.001 - w1, 0.05):
            w = {"lgbm": round(w1, 2), "xgb": round(w2, 2), "gnn": round(1 - w1 - w2, 2)}
            mae = np.abs(sum(w[t] * oof[t][dev] for t in w) - r[dev]).mean()
            if mae < best_mae:
                best_w, best_mae = w, mae
    ensemble = baseline + sum(best_w[t] * oof[t] for t in best_w)
    log(f"Ensemble weights {best_w}; OOF MAE {best_mae:.4f}")

    # 5. Uncertainty: an error model predicts |error| from features + disagreement
    def error_inputs(preds):
        disagreement = np.column_stack([np.abs(preds["lgbm"] - preds["xgb"]), np.abs(preds["lgbm"] - preds["gnn"]),
                                        np.abs(preds["xgb"] - preds["gnn"])])
        return np.column_stack([X, disagreement]).astype(np.float32)

    E = error_inputs(oof)
    abs_err = np.abs(ensemble - y)
    error_params = dict(n_estimators=600, learning_rate=0.03, num_leaves=31, min_child_samples=40,
                        subsample=0.8, subsample_freq=1, colsample_bytree=0.7, verbose=-1, n_jobs=8)
    err_oof = np.zeros(len(y))
    for k, (_, _, hold) in enumerate(fold_sets):
        others = np.setdiff1d(dev, hold)
        em = lgb.LGBMRegressor(random_state=k, **error_params).fit(E[others], abs_err[others])
        err_oof[hold] = em.predict(E[hold])
    err_oof = np.clip(err_oof, 0.005, None)
    scale = float(np.quantile(abs_err[dev] / err_oof[dev], 0.95) / 1.96)
    error_model = lgb.LGBMRegressor(random_state=0, **error_params).fit(E[dev], abs_err[dev])
    error_model.booster_.save_model(str(MODELS / "error_model.txt"))
    sigma = scale * np.clip(error_model.predict(E), 0.005, None)
    log(f"Uncertainty: error model trained; scale {scale:.2f}")

    (MODELS / "ensemble.json").write_text(json.dumps({
        "features": features, "weights": best_w, "folds": args.folds,
        "global_mean": mean.tolist(), "global_std": std.tolist(),
        "uncertainty_scale": scale, "error_floor": 0.005,
        "lgbm_params": lgbm_params, "xgb_params": xgb_params,
    }, indent=2))
    type_mean = oof  # for the report: test rows already hold fold-averaged predictions

    # 6. Report ----------------------------------------------------------------
    holes = df["hole_count"].to_numpy() > 0
    report = {"test": {
        "huckel_linear": metrics(y[te], baseline[te]),
        **{name: metrics(y[te], baseline[te] + type_mean[name][te]) for name in members},
        "ensemble": metrics(y[te], ensemble[te]),
        "ensemble_no_holes": metrics(y[te][~holes[te]], ensemble[te][~holes[te]]),
        "ensemble_with_holes": metrics(y[te][holes[te]], ensemble[te][holes[te]]),
    }, "oof_dev": metrics(y[dev], ensemble[dev])}
    err = np.abs(ensemble[te] - y[te])
    report["uncertainty_test"] = {
        "coverage_95": float((err <= 1.96 * sigma[te]).mean()),
        "spearman_error_vs_sigma": float(spearmanr(err, sigma[te]).correlation),
        "mean_sigma": float(sigma[te].mean()),
        "mean_sigma_no_holes": float(sigma[te][~holes[te]].mean()),
        "mean_sigma_with_holes": float(sigma[te][holes[te]].mean()),
    }
    bins = pd.cut(y[te], [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.1])
    report["test_by_gap_range"] = {str(b): metrics(y[te][bins == b], ensemble[te][bins == b])
                                   for b in bins.categories if (bins == b).sum() > 0}

    # Extrapolation checks with the tuned LightGBM (one seed): can it predict outside its training range?
    report["extrapolation"] = {}
    q05, q95 = np.quantile(y, [0.05, 0.95])
    n_hex = df["n_hex"].to_numpy()
    for name, inside in [("gap_tails (train 5-95% quantile, test outside)", (y >= q05) & (y <= q95)),
                         ("large_size (train n_hex<=34, test n_hex>=35)", n_hex <= 34)]:
        inner = np.nonzero(inside)[0]
        outer = np.nonzero(~inside)[0]
        tr2, va2 = train_test_split(inner, test_size=0.1, random_state=0)
        s2, i2 = np.polyfit(df["huckel_gap"].to_numpy()[tr2], y[tr2], 1)
        base2 = s2 * df["huckel_gap"].to_numpy() + i2
        m = fit_lgbm(lgbm_params, X, y - base2, tr2, va2, 0)
        report["extrapolation"][name] = {"huckel_linear": metrics(y[outer], base2[outer]),
                                         "lgbm": metrics(y[outer], base2[outer] + m.predict(X[outer]))}

    (RESULTS / "metrics.json").write_text(json.dumps(report, indent=2))
    pd.DataFrame({"Structure_Name": df["Structure_Name"].to_numpy()[te], "xtb_gap_eV": y[te],
                  "huckel_linear": baseline[te], "lgbm": baseline[te] + type_mean["lgbm"][te],
                  "xgb": baseline[te] + type_mean["xgb"][te], "gnn": baseline[te] + type_mean["gnn"][te],
                  "ensemble": ensemble[te], "sigma": sigma[te], "has_hole": holes[te]}
                 ).to_csv(RESULTS / "test_predictions.csv", index=False)
    log("TEST RESULTS")
    for name, m in report["test"].items():
        log(f"  {name:22} MAE {m['MAE']:.4f}  RMSE {m['RMSE']:.4f}  R2 {m['R2']:.4f}  (n={m['n']})")
    log(f"  uncertainty: {report['uncertainty_test']}")
    for name, v in report["extrapolation"].items():
        log(f"  extrapolation {name}: Hückel MAE {v['huckel_linear']['MAE']:.4f}, LGBM MAE {v['lgbm']['MAE']:.4f}")
    log("done")


if __name__ == "__main__":
    main()
