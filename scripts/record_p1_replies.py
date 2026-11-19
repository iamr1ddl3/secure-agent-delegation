"""Record real P1 replies for every P1 golden item the compound tasks use, for offline tests.

Needs a running P1 (`docker compose up p1-mcp`) and one short-lived access token per demo user in the environment,
as P1_TOKEN_<USER> (e.g. P1_TOKEN_MANAGER_SURAT). Tokens come from P1's own tooling and are never written to disk:
only the question, the person and P1's reply are recorded. Every reply goes through P1Client, so it is
schema-checked on the way in.

Usage: python scripts/record_p1_replies.py [mcp-url]   (default $P1_MCP_URL or http://localhost:8001/mcp)
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml

from secure_agent_delegation.p1_client import P1Client

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals/recordings/p1_replies.json"


def golden_ids() -> list[str]:
    ids = {p["p1_golden"] for f in (ROOT / "evals/compound").glob("*.yaml")
           for t in yaml.safe_load(f.read_text()) for p in t["parts"] if p["specialist"] == "sql"}
    return sorted(ids)


async def main(url: str) -> None:
    index = json.loads((ROOT / "evals/p1_golden_index.json").read_text())["items"]
    client, out = P1Client(url), {}
    for gid in golden_ids():
        item = index[gid]
        token = os.environ[f"P1_TOKEN_{item['asked_by'].upper().replace('.', '_')}"]
        reply = await client.query(item["question"], token, task_id=f"record-{gid}")
        out[gid] = {"asked_by": item["asked_by"], "question": item["question"], "response": reply}
        print(f"{gid} {item['asked_by']}: {reply['status']} (expected {item['expect']})")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} replies to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("P1_MCP_URL", "http://localhost:8001/mcp")))
