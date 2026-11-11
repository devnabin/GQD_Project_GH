# Created date: 2026-11-10 (America/Chicago)
"""Graph neural network for the xTB gap of a GQD (pure PyTorch, no extra graph library).

Graph   : carbon atoms are nodes, C-C bonds are edges.
Node    : edge-carbon flag (has H), number of hexagons it belongs to,
          on-a-hole flag, and its weight in the Hückel HOMO-1/HOMO/LUMO/LUMO+1
          orbitals (squared coefficients x number of atoms).
Global  : the molecule-level physics features from features.py (standardised).
Target  : residual = xTB gap - Hückel linear fit (the network learns the correction).
Model   : 5 message-passing layers (GIN-style, residual + LayerNorm), then
          sum/mean/max pooling, concatenated with global features -> MLP -> 1 value.
"""

from dataclasses import dataclass

import numpy as np
import torch
from rdkit import Chem
from torch import nn

N_NODE_FEATURES = 7


@dataclass
class Graph:
    x: np.ndarray        # (n_atoms, N_NODE_FEATURES)
    edges: np.ndarray    # (2, 2 * n_bonds), both directions


def mol_to_graph(mol: Chem.Mol) -> Graph:
    adjacency = Chem.GetAdjacencyMatrix(mol).astype(float)
    n = adjacency.shape[0]
    degree = adjacency.sum(axis=1)

    values, vectors = np.linalg.eigh(adjacency)
    order = np.argsort(values)[::-1]
    vectors = vectors[:, order]
    n_occ = n // 2
    orbital_weight = [vectors[:, k] ** 2 * n for k in (n_occ - 2, n_occ - 1, n_occ, n_occ + 1)]

    hexagons = [ring for ring in mol.GetRingInfo().AtomRings() if len(ring) == 6]
    hex_count = np.zeros(n)
    for ring in hexagons:
        hex_count[list(ring)] += 1
    big_ring_atoms = {a for ring in mol.GetRingInfo().AtomRings() if len(ring) > 6 for a in ring}
    on_hole = np.array([1.0 if a in big_ring_atoms else 0.0 for a in range(n)])

    x = np.column_stack([(degree == 2).astype(float), hex_count / 3, on_hole, *orbital_weight]).astype(np.float32)
    rows, cols = np.nonzero(adjacency)
    return Graph(x=x, edges=np.vstack([rows, cols]).astype(np.int64))


def collate(graphs: list[Graph], globals_: np.ndarray, device) -> tuple:
    """Merge graphs into one big disconnected graph for a batch."""
    xs, edges, batch, offset = [], [], [], 0
    for i, g in enumerate(graphs):
        xs.append(g.x)
        edges.append(g.edges + offset)
        batch.append(np.full(len(g.x), i))
        offset += len(g.x)
    x = torch.as_tensor(np.concatenate(xs), dtype=torch.float32, device=device)
    e = torch.as_tensor(np.concatenate(edges, axis=1), dtype=torch.long, device=device)
    b = torch.as_tensor(np.concatenate(batch), dtype=torch.long, device=device)
    g = torch.as_tensor(globals_, dtype=torch.float32, device=device)
    return x, e, b, g, len(graphs)


class GINLayer(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.eps = nn.Parameter(torch.zeros(1))
        self.mlp = nn.Sequential(nn.Linear(hidden, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
        self.norm = nn.LayerNorm(hidden)

    def forward(self, h, edges):
        message = torch.zeros_like(h).index_add_(0, edges[1], h[edges[0]])
        return self.norm(h + self.mlp((1 + self.eps) * h + message))


class GapGNN(nn.Module):
    def __init__(self, n_global: int, hidden: int = 128, layers: int = 5, dropout: float = 0.1):
        super().__init__()
        self.embed = nn.Linear(N_NODE_FEATURES, hidden)
        self.layers = nn.ModuleList(GINLayer(hidden) for _ in range(layers))
        self.head = nn.Sequential(
            nn.Linear(3 * hidden + n_global, 256), nn.SiLU(), nn.Dropout(dropout),
            nn.Linear(256, 128), nn.SiLU(), nn.Linear(128, 1),
        )

    def forward(self, x, edges, batch, globals_, n_graphs):
        h = self.embed(x)
        for layer in self.layers:
            h = layer(h, edges)
        hidden = h.shape[1]
        total = torch.zeros(n_graphs, hidden, device=h.device).index_add_(0, batch, h)
        counts = torch.zeros(n_graphs, device=h.device).index_add_(0, batch, torch.ones_like(batch, dtype=h.dtype))
        mean = total / counts.unsqueeze(1)
        maximum = torch.full((n_graphs, hidden), -1e9, device=h.device).scatter_reduce(
            0, batch.unsqueeze(1).expand_as(h), h, reduce="amax")
        return self.head(torch.cat([total / 50, mean, maximum, globals_], dim=1)).squeeze(1)


def train_gnn(graphs, globals_, target, train_idx, val_idx, seed: int, device="cpu",
              epochs: int = 300, patience: int = 40, batch_size: int = 64, lr: float = 1e-3, log=print):
    """Train one GNN; return the model with the best validation MAE."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = GapGNN(globals_.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    best, best_state, waited = np.inf, None, 0

    for epoch in range(epochs):
        model.train()
        order = rng.permutation(train_idx)
        for start in range(0, len(order), batch_size):
            idx = order[start:start + batch_size]
            batch = collate([graphs[i] for i in idx], globals_[idx], device)
            loss = nn.functional.smooth_l1_loss(model(*batch), torch.as_tensor(target[idx], dtype=torch.float32, device=device), beta=0.05)
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
        scheduler.step()

        val_mae = np.abs(predict_gnn(model, graphs, globals_, val_idx, device) - target[val_idx]).mean()
        if val_mae < best - 1e-5:
            best, waited = val_mae, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            waited += 1
        if epoch % 20 == 0 or waited == 0 and epoch > 0 and epoch % 10 == 0:
            log(f"    seed {seed} epoch {epoch:3d}  val MAE {val_mae:.4f}  best {best:.4f}")
        if waited >= patience:
            break
    model.load_state_dict(best_state)
    log(f"    seed {seed} done at epoch {epoch}, best val MAE {best:.4f}")
    return model


@torch.no_grad()
def predict_gnn(model, graphs, globals_, idx, device="cpu", batch_size: int = 256) -> np.ndarray:
    model.eval()
    out = []
    for start in range(0, len(idx), batch_size):
        part = idx[start:start + batch_size]
        out.append(model(*collate([graphs[i] for i in part], globals_[part], device)).cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0)
