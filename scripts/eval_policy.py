"""Run the policy mini-eval (evals/policy/questions.yaml) against the loaded policy store and a real model.

Writes evals/policy/results.md (committed: numbers, model, misses) and reports/policy-<time>.json (full answers).
Usage: python scripts/eval_policy.py [model-id]   (default: config/models.yaml roles.policy)
Needs OPENROUTER_API_KEY (from .env) and a loaded store (scripts/load_policies.py).
"""
import json
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import yaml

from secure_agent_delegation.llm import CONFIG, LLM
from secure_agent_delegation.policy_agent import REPLY_SCHEMA, PolicyAgentError, answer
from secure_agent_delegation.policy_eval import score, summarise
from secure_agent_delegation.policy_store import MODEL, embed_query_with_model, search

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"hit_rate_at_5": 16 / 17, "mrr": 0.80, "faithfulness": 15 / 17, "refusal_score": 1.0}


def env_file() -> None:
    for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
        k, sep, v = line.partition("=")
        if sep and not line.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip())


def main(model_id: str) -> None:
    env_file()
    items = yaml.safe_load((ROOT / "evals/policy/questions.yaml").read_text())
    llm, rows, scores = LLM(model_id, schema=REPLY_SCHEMA), [], []
    url = os.environ.get("STATE_DATABASE_URL", "postgresql://p2:p2-local@localhost:5433/p2")
    with psycopg.connect(url) as conn:
        for item in items:
            t0 = time.perf_counter()
            hits = search(conn, item["question"], embed_query_with_model(item["question"]))
            try:
                r = answer("p", item["question"], hits, llm)
                status, text, cited = r.status, r.answer or "", [(c.page, c.section) for c in r.citations]
            except PolicyAgentError as e:
                status, text, cited = "error", str(e), []
            s = score(item, [h.page for h in hits], status, text, [p for p, _ in cited])
            scores.append(s)
            rows.append({**s, "question": item["question"], "status": status, "answer": text, "cited": cited,
                         "retrieved": [(h.page, h.section) for h in hits], "ms": (time.perf_counter() - t0) * 1000})
            print(f"{item['id']} {status:9} {s}")
    m = summarise(scores)
    p95 = statistics.quantiles([r["ms"] for r in rows], n=20)[-1]
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / f"reports/policy-{stamp}.json").write_text(json.dumps({"model": model_id, "metrics": m, "rows": rows},
                                                                  indent=1, ensure_ascii=False))
    lines = [(f"# Policy mini-eval results\n\nLatest run {stamp}: answer model `{model_id}`, embeddings `{MODEL}`, "
              f"hybrid retrieval (dense + keyword, RRF), top 5.\n"),
             "| Metric | Result | Target | Pass |", "| --- | --- | --- | --- |"]
    for k, target in TARGETS.items():
        lines.append(f"| {k} | {m[k]:.3f} | {target:.3f} | {'yes' if m[k] >= target - 1e-9 else '**no**'} |")
    lines += [f"\nCost: ${llm.cost_usd:.4f} for {len(items)} questions. p95 time per question: {p95 / 1000:.1f} s.\n",
              "## Misses\n"]
    misses = [r for r in rows if r.get("rank") == 0 or r.get("faithful") is False or r.get("refused_ok") is False]
    lines += [f"- **{r['id']}** ({r['status']}): {r['question']}\n  - answer: {r['answer']}\n  - cited: {r['cited']}"
              for r in misses] or ["None."]
    (ROOT / "evals/policy/results.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(m, indent=1), f"cost ${llm.cost_usd:.4f}", f"p95 {p95:.0f} ms")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else CONFIG["roles"]["policy"])
