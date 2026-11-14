# Novel GQD library (built 2026-11-13 22:39 CST)

- Unique new GQDs (valid, closed-shell, no holes, not in the 91k dataset): **1183**
- Found by LLM edits first: 374; by random edits first: 809
- Scored by xTB: 696; with score v2: 695 (> 0: 268)
- Open-shell screen done: 58 (closed-shell, N_FOD ≤ 2.9: 6)
- InChIKey not available (RDKit InChI kekulisation limit): 97
- Went through GPU DFT: 5
- Runs included: llm_s0, llm_v2_s1, llm_v2_s2, llm_v2_s3, random_s0, random_v2_s1, random_v2_s2, random_v2_s3

Columns are described in `build_library.py`. score_v1 is the old Stage 3a score, which DFT showed rewards an xTB artefact; use score_v2 and N_FOD.
