<!-- Created date: 2026-11-12 (America/Chicago) -->

# Report: thesis draft

This folder holds the thesis draft for the Agentic_GQD project: **LLM-guided design of graphene quantum dots for NO₂ gas sensing**. It covers the work from the first agent (`studio/agent.py`) to the current experiments, in the order the stages were built.

The draft is updated after every new experiment or result. The rule for this, including which chapter to update, is at the top of `../AGENTS.MD`.

## Build

```bash
cd Report
latexmk -pdf -interaction=nonstopmode main.tex     # -> main.pdf
latexmk -c                                         # remove build files
```

This needs a TeX distribution (MacTeX is installed on the Mac). For Overleaf, upload the whole `Report/` folder; `main.tex` is the main file.

## Layout

| Path | Contents |
|---|---|
| `main.tex` | Preamble, title page, front matter, chapter list. Title-page fields are placeholders in square brackets. |
| `chapters/00_abstract.tex` | Abstract |
| `chapters/01_introduction.tex` | Motivation, research questions (RQ1 to RQ4), hypotheses (H1 to H4), contributions |
| `chapters/02_literature_review.tex` | Background and literature review |
| `chapters/03_methods.tex` | Agent, hexagon representation, gap predictor, sensing score, evolutionary loop, DFT, computing setup; four algorithms and three diagrams |
| `chapters/04_experimental_design.tex` | Experiments E1 to E6 and how each tests a hypothesis |
| `chapters/05_results.tex` | Results of each stage and experiment |
| `chapters/06_discussion.tex` | Answers to the research questions so far, limitations, cost |
| `chapters/07_conclusion.tex` | Conclusion and future work |
| `chapters/appendix_*.tex` | A: LLM prompts (verbatim); B: logged fields; C: commands to reproduce |
| `references.bib` | Bibliography. Entries marked `% check` were written from memory and must be checked against the publisher before submission. |
| `figures/` | Figures used in the thesis (see below) |

## Figures

| File | Copied from | Made by |
|---|---|---|
| `figures/stage3a_sensing_vs_gap.png` | `Stage3a/results/sensing_vs_gap.png` | `Stage3a/analyze.py` |
| `figures/stage3a_score_vs_gap.png` | `Stage3a/results/score_vs_gap.png` | `Stage3a/analyze.py` |
| `figures/stage3_pilot_compare.png` | `Stage3/results/compare.png` | `Stage3/compare.py llm_s0 random_s0` |
| `figures/stage4_compare_v2.png` | `Stage3/results/compare_v2.png` | `Stage3/compare.py <six v2 runs> --name v2` |

The diagrams in Chapter 3 (loop, agent graph, hexagon grid) are drawn with TikZ inside `03_methods.tex`.

## Open items (status 2026-11-12, evening)

Results that are not in yet are marked in the text with `\pending{...}` (orange in the PDF). Notes for the author are marked with `\authornote{...}` (blue). Search for both before submission.

Pending results:
- **E5b** is done (Section 5.7, Tables `tab:main` and `tab:main-mutator`, Figure `fig:main`).
- **E4**, the GPU DFT benchmark (running on the server). Add:
  - the per-complex comparison;
  - the Spearman correlations;
  - the decision by the rule in Section 4.4;
  - the DFT O₂ results.
- **E6**, the baseline without evolution (planned).
- **Best GQDs:** a structural analysis and a figure of their shapes.

Author items:
- title-page fields;
- acknowledgements;
- the statement on the use of AI tools (check the university policy);
- confirming the literature gap with a systematic search;
- checking the 8 `% check` references.
