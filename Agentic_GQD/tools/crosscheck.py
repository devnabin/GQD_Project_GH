# Created: 2026-11-13 19:40 CST
"""Ask a second AI model (Azure gpt-6.1-sol) to fact-check claims or numbers. Decision D23.

    .venv/bin/python tools/crosscheck.py "claim 1" "claim 2" ...
    .venv/bin/python tools/crosscheck.py --file some_claims.txt

Every request and answer is appended to tools/crosscheck_log.md with a clock timestamp and the
exact model version. The answer is a second opinion only: agreement is not proof; ground truth
stays the result files, DFT, verified literature and experiments.
Settings come from studio/.env (key never printed). Deployment: --deployment or CROSSCHECK_DEPLOYMENT.
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LOG = Path(__file__).resolve().parent / "crosscheck_log.md"
SYSTEM = ("You are a careful scientific fact-checker. For each claim, say CORRECT, WRONG or CANNOT VERIFY, "
          "then one or two sentences of reasoning. Recompute any numbers yourself. Do not guess; if you cannot "
          "verify something (for example that a paper exists), say so.")


def main():
    load_dotenv(ROOT / "studio" / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("claims", nargs="*")
    ap.add_argument("--file", type=Path)
    ap.add_argument("--deployment", default=os.getenv("CROSSCHECK_DEPLOYMENT", "gpt-6.1-sol"))
    args = ap.parse_args()
    claims = list(args.claims) + (args.file.read_text().strip().split("\n\n") if args.file else [])
    if not claims:
        ap.error("give claims or --file")
    from langchain_openai import AzureChatOpenAI
    llm = AzureChatOpenAI(azure_deployment=args.deployment, api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    text = "\n\n".join(f"Claim {i}: {c}" for i, c in enumerate(claims, 1))
    reply = llm.invoke([("system", SYSTEM), ("human", text)])
    model = reply.response_metadata.get("model_name", args.deployment)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    with LOG.open("a") as handle:
        handle.write(f"\n## {stamp} — {model}\n\n**Asked:**\n\n{text}\n\n**Answer:**\n\n{reply.content.strip()}\n")
    print(reply.content.strip())
    print(f"\n[{model}; logged to {LOG.relative_to(ROOT)}]")


if __name__ == "__main__":
    main()
