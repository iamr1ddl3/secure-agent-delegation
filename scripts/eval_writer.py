"""Run the report-writer eval (evals/writer/README.md) on the gate tasks, from recorded findings, with a real model.

Writes evals/writer/results.md (committed) and reports/writer-<time>.json (full summaries).
Usage: python scripts/eval_writer.py [model-id]   (default: config/models.yaml roles.writer). Needs OPENROUTER_API_KEY.
"""
import json
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from secure_agent_delegation.handoffs import SpecialistResult
from secure_agent_delegation.llm import CONFIG, LLM, LLMError
from secure_agent_delegation.writer import REPLY_SCHEMA, WriterError, complete, write

ROOT = Path(__file__).resolve().parents[1]
P1 = json.loads((ROOT / "evals/recordings/p1_replies.json").read_text())
POLICY = json.loads((ROOT / "evals/recordings/policy_answers.json").read_text())


def findings(task: dict, uses: list[str]) -> list[SpecialistResult]:
    out = []
    for p in (p for p in task["parts"] if p["id"] in uses):
        if p["specialist"] == "sql":
            reply = P1[p["p1_golden"]]["response"]
            out.append(SpecialistResult(subtask_id=p["id"], specialist="sql", status=reply["status"],
                                        p1_response=reply))
        else:
            out.append(SpecialistResult.model_validate(POLICY[f"{task['id']}/{p['id']}"]["result"]))
    return out


def main(model_id: str) -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and not line.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip())
    llm, rows = LLM(model_id, schema=REPLY_SCHEMA, max_tokens=4000), []  # ct-03 lists 54 customers
    for task in yaml.safe_load((ROOT / "evals/compound/gate.yaml").read_text()):
        w = next(p for p in task["parts"] if p["specialist"] == "writer")
        f, t0 = findings(task, w["uses"]), time.perf_counter()
        asked = {p["id"]: p.get("question") or p.get("key_point") for p in task["parts"]}
        row = {"id": task["id"], "refusals_ok": True, "invented": False, "complete": False, "error": None}
        try:
            row["summary"] = write(w["id"], task["request"], f, llm, asked).answer
            row["complete"] = complete(row["summary"], f)
        except LLMError as e:
            row["error"] = f"model call failed: {e}"
        except WriterError as e:
            row["error"] = str(e)
            row["refusals_ok"] = "unavailable" not in str(e)
            row["invented"] = "not in the findings" in str(e)
        row["passed"] = row["refusals_ok"] and not row["invented"] and row["complete"] and not row["error"]
        row["ms"] = (time.perf_counter() - t0) * 1000
        rows.append(row)
        print(task["id"], {k: row[k] for k in ("passed", "refusals_ok", "invented", "complete", "error")})
    n = len(rows)
    m = {"passed": sum(r["passed"] for r in rows), "invented": sum(r["invented"] for r in rows),
         "refusals_ok": sum(r["refusals_ok"] for r in rows), "complete": sum(r["complete"] for r in rows)}
    p95 = statistics.quantiles([r["ms"] for r in rows], n=20)[-1]
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / f"reports/writer-{stamp}.json").write_text(json.dumps({"model": model_id, "metrics": m, "rows": rows},
                                                                  indent=1, ensure_ascii=False))
    lines = [f"# Report writer eval results\n\nLatest run {stamp}: model `{model_id}`, 10 gate tasks, recorded findings.\n",
             "| Metric | Result | Target | Pass |", "| --- | --- | --- | --- |",
             f"| Tasks passing all checks | {m['passed']} / {n} | ≥ 9 / {n} | {'yes' if m['passed'] >= 9 else '**no**'} |",
             f"| Tasks with an invented number | {m['invented']} | 0 | {'yes' if m['invented'] == 0 else '**no**'} |",
             (f"| Unavailable parts named correctly | {m['refusals_ok']} / {n} | {n} / {n} | "
             f"{'yes' if m['refusals_ok'] == n else '**no**'} |"),
             f"| Complete (every value present) | {m['complete']} / {n} | | |",
             f"\nCost: ${llm.cost_usd:.4f} for {n} tasks. p95 time per task: {p95 / 1000:.1f} s.\n", "## Misses\n"]
    lines += [f"- **{r['id']}**: {r['error'] or 'incomplete: a value from the data is missing'}"
              for r in rows if not r["passed"]] or ["None."]
    (ROOT / "evals/writer/results.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(m), f"${llm.cost_usd:.4f}", f"p95 {p95:.0f} ms")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else CONFIG["roles"]["writer"])
