"""Record the policy agent's answers for every policy part of the compound tasks, for offline writer tests.

The part's key_point is asked as the question (in the real flow the supervisor writes it). Needs the loaded store
and OPENROUTER_API_KEY (from .env). Writes evals/recordings/policy_answers.json, keyed "<task id>/<part id>".
"""
import json
import os
from pathlib import Path

import psycopg
import yaml

from secure_agent_delegation.llm import CONFIG, LLM
from secure_agent_delegation.policy_agent import REPLY_SCHEMA, answer
from secure_agent_delegation.policy_store import embed_query_with_model, search

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    for line in (ROOT / ".env").read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and not line.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip())
    llm, out = LLM(CONFIG["roles"]["policy"], schema=REPLY_SCHEMA), {}
    with psycopg.connect(os.environ.get("STATE_DATABASE_URL", "postgresql://p2:p2-local@localhost:5433/p2")) as conn:
        for f in sorted((ROOT / "evals/compound").glob("*.yaml")):
            for task in yaml.safe_load(f.read_text()):
                for part in (p for p in task["parts"] if p["specialist"] == "policy"):
                    q = part["key_point"]
                    r = answer(part["id"], q, search(conn, q, embed_query_with_model(q)), llm)
                    out[f"{task['id']}/{part['id']}"] = {"question": q, "result": r.model_dump(mode="json")}
                    print(task["id"], part["id"], r.status, [c.page for c in r.citations], "expected", part["cites"])
    (ROOT / "evals/recordings/policy_answers.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} answers, ${llm.cost_usd:.4f}")
