<!-- Created: 2026-11-13 22:30 CST -->

# Tools

| File | What it does |
|---|---|
| `crosscheck.py` | Sends claims or numbers to the second AI model (Azure `gpt-6.1-sol`) for a CORRECT / WRONG / CANNOT VERIFY check. Decision D23; project rule 5 in `AGENTS.MD`. |
| `crosscheck_log.md` | Every check, with a timestamp and the exact model version |

```bash
.venv/bin/python tools/crosscheck.py "claim 1" "claim 2"
```

Settings come from `studio/.env`; keys are never printed. A cross-check is a second opinion, not proof: numbers are recomputed from the result files first.
