<!-- Created date: 2026-11-12 (America/Chicago) -->

# Stage 3c: sensor twin (virtual NO₂ sensor)

**Why:** the Stage 3a score compares binding energies and charge per molecule. It ignores how many molecules actually sit on the GQD at real concentrations (20 ppb NO₂, about 16,000 ppm water at 50% humidity). The twin adds that step. It is the first, simple version of the "Cyber Twin" idea (`RESEARCH_OPTIONS.md`, D15).

## Model (`twin.py`, version 1)

1. **Molecule:** adsorption energy and charge of each gas, from xTB (Stage 3a). DFT values come later.
2. **Film:** competitive Langmuir coverage at 298 K, `θ_g = K_g p_g / (1 + Σ K_j p_j)`.
   - `K_g = exp(−(E_g − TΔS_g)/kT)`.
   - The entropy lost on adsorption comes from the Campbell–Sellers correlation, `S_ads = 0.70 S_gas − 3.3R`. That gives `TΔS` ≈ −0.31 eV for NO₂ and −0.26 eV for H₂O.
3. **Signal:** electrons withdrawn per site, `Σ θ_g (−q_g)`. The NO₂ response is the signal with NO₂ minus the signal in the same air without NO₂.
4. **Recovery:** `τ = exp(−E_NO₂/kT)/10¹² s`. **Spec:** recover within 5 minutes.
5. **Humidity interference:** the NO₂ concentration that gives the same signal as a change from 30% to 70% humidity ("humidity-equivalent NO₂").

**Air in the model:** 20 ppb NO₂, 50% RH, 10 ppb NH₃ and 0.5 ppm CO. O₂ is left out, because xTB is wrong for it.

## First results (2026-11-12, xTB energies, 85 GQDs)

These come from the 50 calibration GQDs plus the 35 fully checked best GQDs of the evolution runs. Full tables: `results/summary.md`, `results/twin_results.csv`. Plot: `results/twin_response_vs_binding.png`.

1. **Water does not crowd NO₂ off the surface.** Water coverage at 50% RH is at most 0.3% of sites. My earlier rough estimate, "water may cover most of the surface", was wrong: at these low coverages the gases barely compete for sites.
2. **The NO₂ signal of the current "best" GQDs is tiny.** These GQDs physisorb NO₂ at −0.43 to −0.52 eV, so at 20 ppb only about 10⁻⁸ to 10⁻⁴ of their sites hold NO₂.
   - Their signal is so small that humidity changes matter.
   - For the median physisorbing GQD, a 30→70% humidity swing gives the same signal as **32 ppb NO₂**.
3. **The twin's optimum is a different binding window.**
   - The best predicted sensors bind NO₂ at about **−0.75 to −0.82 eV** (xTB). They still recover within about a minute.
   - Their signal at 20 ppb is about 10⁴ times larger than that of the current best GQDs, and humidity becomes negligible.
   - Five calibration GQDs fall in this window: `gqd_83340`, `gqd_24021`, `gqd_58903`, `gqd_70353` and `gqd_18216`.
   - The Stage 3a score ranked them low (0.09 to 0.14), because its reversibility factor starts penalising at −0.6 eV.
4. **The two rankings disagree.** Their Spearman correlation across the 85 GQDs is 0.62.

## Caveats (why this is not a conclusion yet)

- These binding energies are xTB values for **chemisorbed** NO₂, which xTB overbinds by 0.1 to 0.55 eV (Stage 3a DFT check). The real energies of the "optimal" GQDs may be weaker, and the advantage could shrink or vanish.
  - **DFT energies are needed.** `gqd_58903` and `gqd_13400` are in the GPU DFT benchmark.
- The entropy term is a correlation with an uncertainty of about ±0.1 eV, which means about a factor of 50 in coverage.
- Desorbing chemisorbed NO₂ may need more energy than its binding energy (an extra barrier), which would slow recovery.
- The model has one site type per GQD, no film, contacts or carrier density, and no O₂. Signals are relative.

## Next

1. Rerun the twin with DFT energies and charges for the 12 benchmark GQDs, once DFT phase 1 is in.
2. If the window holds, consider the twin score as the evolution objective. This is decision D19 in `RESEARCH_OPTIONS.md`.
3. Version 2: several sites per GQD, adsorption kinetics (response time), and O₂ from DFT.

## Run

```bash
.venv/bin/python Stage3c/twin.py      # -> results/twin_results.csv, summary.md, twin_response_vs_binding.png
```
