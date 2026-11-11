import asyncio
import csv
import importlib.util
import os
import shutil
import sys
from pathlib import Path
from typing import Literal, NotRequired

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from rdkit import Chem, RDConfig, RDLogger
from rdkit.Chem import rdDepictor
from rdkit.Chem.rdchem import HybridizationType

from send_one_gqd import random_smiles
from Stage1.gqd_hex import HexError, hex_to_smiles

RDLogger.DisableLog("rdApp.*")

# SA scorer ships with RDKit's Contrib folder; skip the SA check if it is missing.
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
try:
    import sascorer
except ImportError:
    sascorer = None

# Acceptance thresholds (same defaults as the reference generation script).
MIN_HEX, MAX_HEX = 20, 40
MIN_SP2 = 0.95
MAX_SA = 8.0

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "accepted_gqds"
ACCEPTED_CSV = OUTPUT_DIR / "accepted_gqds.csv"
CSV_FIELDS = ["Structure_Name", "SMILES", "InChIKey", "N_Hex", "SP2", "SA_Score"]


class AgentState(MessagesState):
    software_available: NotRequired[bool]
    missing_software: NotRequired[list[str]]
    # Validation results for the structure currently being checked.
    smiles: NotRequired[str]
    inchikey: NotRequired[str]
    n_hex: NotRequired[int]
    sp2: NotRequired[float]
    sa_score: NotRequired[float | None]
    rejection: NotRequired[str | None]


async def generate_gqd() -> str:
    """Return one GQD SMILES structure after a five-second delay."""
    await asyncio.sleep(5)
    return random_smiles()


def build_gqd_from_hexagons(hexagons: list[list[int]]) -> str:
    """Build a GQD from hexagon positions on a honeycomb grid and return its SMILES.

    Each hexagon is [q, r] in axial coordinates. The six neighbours of [q, r] are
    [q+1, r], [q-1, r], [q, r+1], [q, r-1], [q+1, r-1], [q-1, r+1].
    All hexagons must be connected, with no duplicates.
    Example (naphthalene): [[0, 0], [1, 0]].
    """
    return hex_to_smiles(hexagons)


def software_check(state: AgentState) -> dict:
    """Check that required chemistry packages and the xtb executable are available."""
    required_modules = ("rdkit", "numpy", "scipy", "pyscf", "geometric")
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]

    project_xtb = Path(__file__).resolve().parents[2] / ".env" / "bin" / "xtb"
    if shutil.which("xtb") is None and shutil.which(str(project_xtb)) is None:
        missing.append("xtb executable")

    result = {"software_available": not missing, "missing_software": missing}
    if missing:
        result["messages"] = [AIMessage(content=f"Required software is missing: {', '.join(missing)}")]
    return result


def decide_node(state: AgentState) -> Literal["assistant", "__end__"]:
    return "assistant" if state.get("software_available") else END


# ---------------------------------------------------------------------------
# Validation nodes: graph -> uniqueness -> ring count -> sp2 -> SA -> save
# ---------------------------------------------------------------------------
def reject(step: str, reason: str) -> dict:
    return {
        "rejection": f"{step}: {reason}",
        "messages": [AIMessage(content=f"GQD rejected at {step} check: {reason}")],
    }


def saved_inchikeys() -> set[str]:
    if not ACCEPTED_CSV.exists():
        return set()
    with ACCEPTED_CSV.open(newline="", encoding="utf-8") as handle:
        return {row["InChIKey"] for row in csv.DictReader(handle)}


def check_molecular_graph(state: AgentState) -> dict:
    """Parse and sanitize the generated SMILES; require one connected structure."""
    tool_output = next(m for m in reversed(state["messages"]) if isinstance(m, ToolMessage))
    smiles = str(tool_output.content).strip()
    # Clear results from any previous structure before checking this one.
    fresh = {"smiles": smiles, "inchikey": None, "n_hex": None, "sp2": None, "sa_score": None, "rejection": None}

    if tool_output.status == "error":  # e.g. disconnected or open-shell hexagon list
        return fresh | {"smiles": None} | reject("molecular graph", smiles)
    mol = Chem.MolFromSmiles(smiles)  # returns None if parsing or sanitization fails
    if mol is None:
        return fresh | reject("molecular graph", "RDKit could not parse or sanitize the SMILES")
    canonical = Chem.MolToSmiles(mol, canonical=True)
    if "." in canonical:
        return fresh | reject("molecular graph", "structure has disconnected fragments")
    return fresh | {"smiles": canonical}


def check_uniqueness(state: AgentState) -> dict:
    """Reject structures whose InChIKey is already in the accepted CSV."""
    key = Chem.MolToInchiKey(Chem.MolFromSmiles(state["smiles"]))
    if not key:
        return reject("uniqueness", "could not compute an InChIKey")
    if key in saved_inchikeys():
        return reject("uniqueness", f"{key} is already saved")
    return {"inchikey": key}


def check_ring_count(state: AgentState) -> dict:
    """Require MIN_HEX to MAX_HEX six-membered rings."""
    mol = Chem.MolFromSmiles(state["smiles"])  # keep a reference; RingInfo dies with the mol
    rings = mol.GetRingInfo().AtomRings()
    n_hex = sum(1 for ring in rings if len(ring) == 6)
    if not MIN_HEX <= n_hex <= MAX_HEX:
        return {"n_hex": n_hex} | reject("ring count", f"{n_hex} hexagons, need {MIN_HEX}-{MAX_HEX}")
    return {"n_hex": n_hex}


def check_sp2(state: AgentState) -> dict:
    """Require at least MIN_SP2 of heavy atoms to be sp2."""
    mol = Chem.MolFromSmiles(state["smiles"])
    heavy = [a for a in mol.GetAtoms() if a.GetAtomicNum() != 1]
    sp2 = sum(a.GetHybridization() == HybridizationType.SP2 for a in heavy) / len(heavy)
    if sp2 < MIN_SP2:
        return {"sp2": round(sp2, 3)} | reject("sp2 fraction", f"{sp2:.3f}, need >= {MIN_SP2}")
    return {"sp2": round(sp2, 3)}


def check_sa_score(state: AgentState) -> dict:
    """Require SA score <= MAX_SA; skipped when sascorer is unavailable."""
    if sascorer is None:
        return {"sa_score": None}
    try:
        sa = round(sascorer.calculateScore(Chem.MolFromSmiles(state["smiles"])), 3)
    except Exception as error:
        return reject("SA score", f"scoring failed ({error})")
    if sa > MAX_SA:
        return {"sa_score": sa} | reject("SA score", f"{sa}, need <= {MAX_SA}")
    return {"sa_score": sa}


def save_gqd(state: AgentState) -> dict:
    """Append the accepted structure to the CSV and write a .mol file."""
    (OUTPUT_DIR / "mol_files").mkdir(parents=True, exist_ok=True)
    is_new_file = not ACCEPTED_CSV.exists()
    name = f"gqd_agent_{len(saved_inchikeys()) + 1:06d}"
    row = {
        "Structure_Name": name, "SMILES": state["smiles"], "InChIKey": state["inchikey"],
        "N_Hex": state["n_hex"], "SP2": state["sp2"], "SA_Score": state["sa_score"],
    }
    with ACCEPTED_CSV.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerow(row)

    mol = Chem.MolFromSmiles(state["smiles"])
    rdDepictor.Compute2DCoords(mol)
    Chem.MolToMolFile(mol, str(OUTPUT_DIR / "mol_files" / f"{name}.mol"))

    sa_text = "skipped (sascorer unavailable)" if state["sa_score"] is None else state["sa_score"]
    return {"messages": [AIMessage(content=(
        f"GQD accepted and saved as {name}: {state['n_hex']} hexagons, "
        f"sp2 fraction {state['sp2']}, SA score {sa_text}, InChIKey {state['inchikey']}."
    ))]}


def next_if_passed(next_node: str):
    """Route to next_node when the check passed, otherwise back to the assistant."""
    def route(state: AgentState) -> str:
        return "assistant" if state.get("rejection") else next_node
    return route


tools = [generate_gqd, build_gqd_from_hexagons]

# Define LLM with bound tools
llm = AzureChatOpenAI(
    model = os.getenv('AZURE_OPENAI_MODEL'),
    # model_provider="azure_openai",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version="2024-02-01",
)

# One tool call per turn: the validation nodes check the latest tool result only.
llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

# System message
sys_msg = SystemMessage(content=(
    "You are a helpful assistant tasked with generate GQD, validate software and environment. "
    "To design a GQD yourself, call build_gqd_from_hexagons with hexagon coordinates (never write SMILES). "
    "Call one tool at a time. "
    "Each generated GQD is validated automatically and then accepted or rejected. "
    "Report the result to the user; only generate another GQD if the user asked for more."
))

# Node
async def assistant(state: AgentState):
   return {"messages": [await llm_with_tools.ainvoke([sys_msg] + state["messages"])]}

# Build graph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_node("software_check", software_check)
# A bad hexagon list (HexError) becomes an error ToolMessage instead of crashing the run.
builder.add_node("tools", ToolNode(tools, handle_tool_errors=HexError))
builder.add_node("check_molecular_graph", check_molecular_graph)
builder.add_node("check_uniqueness", check_uniqueness)
builder.add_node("check_ring_count", check_ring_count)
builder.add_node("check_sp2", check_sp2)
builder.add_node("check_sa_score", check_sa_score)
builder.add_node("save_gqd", save_gqd)


builder.add_edge(START, "software_check")
builder.add_conditional_edges("software_check", decide_node, ["assistant", END])
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
# Every generated structure goes through the checks in order; a failure returns to the assistant.
builder.add_edge("tools", "check_molecular_graph")
validation_steps = ["check_molecular_graph", "check_uniqueness", "check_ring_count",
                    "check_sp2", "check_sa_score", "save_gqd"]
for step, next_step in zip(validation_steps, validation_steps[1:]):
    builder.add_conditional_edges(step, next_if_passed(next_step), [next_step, "assistant"])
builder.add_edge("save_gqd", "assistant")

# Compile graph
graph = builder.compile()
