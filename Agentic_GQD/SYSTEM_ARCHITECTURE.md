<!-- Created: 2026-11-13 22:47 CST -->

# System architecture: the planned agent prototype

The end goal of the research: a user asks for a material, an agent designs it, physics checks it, and the user gets tested candidates. Three views of the same system, from the discussions of 2026-11-13. Update this file when the design changes; add an `Updated:` line.

## View 1: pipeline for one design request

```
USER: "Design a graphene material for detecting NO₂ in humid air,
       recovery under 5 minutes."
          │
          ▼
1. LLM AGENT ──► proposes shapes (hexagon lists), uses its chemistry knowledge
          │
          ▼
2. CODE CHECKS (instant) ──► real molecule? closed-shell? not a radical (FOD)?
          │                   failures go back to the LLM with "fix this"
          ▼
3. FAST ML PREDICTOR (milliseconds) ──► throw away hopeless designs
          │
          ▼
4. xTB (about 1–10 min per design, CPU) ──► NO₂/water/CO binding, charge
          │
          ▼
5. SENSOR TWIN (seconds) ──► predicted signal at 20 ppb, recovery time,
          │                   humidity effect
          ▼
6. DFT CHECK (about 1 hour per design, GPU) ──► confirms the top 3–5 only
          │
          ▼
RESULT TO USER
```

## View 2: who does what

```
USER ──► AGENT (Studio / LangGraph) = the front door
            │  designs, checks, scores (xTB → twin → DFT queue)
            ▼
     NOVEL GQD LIBRARY = the single memory of everything ever found
            ▲   (by the agent, by search runs, by anyone)
            │
     SEARCH RUNS (evolution loop) = the agent's "deep search" mode
```

## View 3: combined

```
USER: "Design a graphene material for NO₂ in humid air, recovery < 5 min"
  │
  ▼
AGENT (front door, LangGraph) ─ chooses a mode:
  │
  ├── QUICK MODE: a few designs ──────────────────────────────┐
  │                                                           │
  └── DEEP SEARCH MODE: evolution loop, many rounds ──────────┤
        (repeats steps 1–5 hundreds of times, keeps the best) │
                                                              ▼
   ┌─────────────── PIPELINE for each design (view 1) ────────────────────┐
   │ 0. LIBRARY LOOKUP: already known?  ──yes──► reuse its saved scores   │
   │        │ no                                    (skip xTB/DFT: free) │
   │ 1. LLM proposes the hexagon list                                     │
   │ 2. Code checks (valid, closed-shell, FOD radical filter)             │
   │ 3. Fast ML predictor (drop hopeless designs)                         │
   │ 4. xTB (binding, charge)                                             │
   │ 5. Sensor twin (signal at 20 ppb, recovery, humidity)                │
   │ 6. DFT (top 3–5 only, GPU queue)                                     │
   └────┬─────────────────────────────────────────────────────────────────┘
        │ every result is written back
        ▼
   NOVEL GQD LIBRARY (single memory: structure + every score + DFT status)
        │
        ▼
RESULT TO USER: top designs, structures, predicted sensor performance,
                confidence label (DFT-checked or xTB estimate), warnings
```

## How the pieces fit

1. **The agent is the front door.** It chooses quick mode (a few designs) or deep search (the evolution loop).
2. **Steps 1–6 are the same in both modes.** Deep search repeats them over many rounds.
3. **The library is the memory.**
   - It is checked before any calculation (step 0), so nothing is computed twice.
   - Every result is written back.
4. **The library becomes training data** for the fast predictor (step 3) and for the fine-tuned LLM (step 1). The system gets cheaper and smarter with use.

## Status (2026-11-13 22:47 CST)

| Piece | Status | Where |
|---|---|---|
| Agent (front door) | ✅ exists; does steps 1–2 and saves to its own folder | `studio/agent.py`, `accepted_gqds/` |
| Code checks + radical (FOD) filter | ✅ | `Stage1/`, `Stage4/fod_screen.py` |
| Fast ML predictor | ✅ for the gap; ❌ for the sensing score | `Stage2/` |
| xTB sensing evaluation | ✅ | `Stage3a/sensing.py`, `Stage3d/sensing_linked.py` |
| Sensor twin | ✅ v1 | `Stage3c/twin.py` |
| Score v2 (DFT-corrected) | ✅, being validated | `Stage4/score_v2.py` |
| DFT check on the GPU | ✅ | `Stage3a/dft_gpu.py` (server) |
| Deep search (evolution loop) | ✅ run by scripts, not yet by the agent | `Stage3/evolve.py` |
| Novel GQD library | ✅ built from search runs | `novel_gqds/` |
| Step 0 (library lookup) and write-back | ❌ to build (decision D25) | — |
| Agent calling steps 3–6 and the deep search | ❌ to build (final prototype step) | — |
| Fine-tuned LLM in step 1 | ❌ later (Stage 5) | `AGENTS.MD` datasets 1–3 |
