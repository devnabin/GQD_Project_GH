# Created date: 2026-11-10 16:24:30 CST
# update date: 2026-11-10 16:28:34 CST
"""Read-only LangGraph scaffold for planning GQD candidate validation."""

import csv
from pathlib import Path
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph


DEFAULT_PILOT = Path(__file__).resolve().parents[2] / "AI_GQD" / "pilot" / "pilot.csv"


class GQDState(TypedDict):
    candidate_id: str
    dataset_path: NotRequired[str]
    candidate: NotRequired[dict[str, str]]
    status: NotRequired[str]
    reason: NotRequired[str]
    next_step: NotRequired[str]


# Candidate agent: find a named structure without changing the reference CSV.
def find_candidate(state: GQDState) -> dict:
    path = Path(state.get("dataset_path", str(DEFAULT_PILOT)))
    if not path.is_file():
        return {"status": "missing_dataset", "reason": f"Dataset not found: {path}"}

    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("Structure_Name") == state["candidate_id"]:
                return {"candidate": row, "status": "found"}
    return {"status": "not_found", "reason": "Candidate ID is absent from the selected CSV."}


def route_candidate(state: GQDState) -> str:
    return "screen_candidate" if state["status"] == "found" else "plan_next"


# Screening agent: use the recorded graph-check label; do not claim new chemistry validation.
def screen_candidate(state: GQDState) -> dict:
    row = state["candidate"]
    if not row.get("SMILES"):
        return {"status": "review", "reason": "SMILES is missing."}
    if row.get("Validation_Level") != "graph_checked_candidate":
        return {"status": "review", "reason": "Expected graph-check label is missing."}
    return {"status": "graph_checked", "reason": "Pilot CSV records a graph-checked candidate."}


# Planning agent: recommend work, leaving actual calculations to the user.
def plan_next(state: GQDState) -> dict:
    if state["status"] == "graph_checked":
        return {"next_step": "Step 4: prepare a 3D starting geometry, unless this ID already has a newer run."}
    return {"next_step": "Review the dataset or candidate record before running calculations."}


builder = StateGraph(GQDState)
builder.add_node("find_candidate", find_candidate)
builder.add_node("screen_candidate", screen_candidate)
builder.add_node("plan_next", plan_next)
builder.add_edge(START, "find_candidate")
builder.add_conditional_edges("find_candidate", route_candidate)
builder.add_edge("screen_candidate", "plan_next")
builder.add_edge("plan_next", END)
graph = builder.compile()
