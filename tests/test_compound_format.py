"""Shape and consistency of the compound-task eval set (no database, no model). Rules: evals/compound/README.md."""
import json
from pathlib import Path

import pytest
import yaml

from secure_agent_delegation.handoffs import derive_status

ROOT = Path(__file__).resolve().parents[1]
P1_INDEX = json.loads((ROOT / "evals/p1_golden_index.json").read_text())["items"]
FILES = sorted((ROOT / "evals/compound").glob("*.yaml"))
TASKS = [t for f in FILES for t in yaml.safe_load(f.read_text())]

IDENTITIES = {"teller.surat", "teller.mumbai", "manager.surat", "manager.mumbai", "hr.officer", "auditor", "intern"}
SPECIALISTS = {"sql", "policy", "writer", "draft"}
PART_STATUSES = {"answered", "refused", "needs_review", "needs_clarification", "awaiting_approval"}
TASK_STATUSES = {"completed", "partial", "awaiting_approval", "refused", "escalated", "needs_clarification"}
POLICY_PAGES = {p.stem for p in (ROOT / "policies").glob("*.md") if p.name != "README.md"}
FIELDS = {"sql": {"id", "specialist", "p1_golden", "question", "expect"},
          "policy": {"id", "specialist", "cites", "key_point", "expect"},
          "writer": {"id", "specialist", "uses", "expect"},
          "draft": {"id", "specialist", "uses", "expect"}}


def test_derive_rules():
    assert derive_status([("sql", "answered"), ("writer", "answered")]) == "completed"
    assert derive_status([("sql", "refused"), ("writer", "answered")]) == "refused"
    assert derive_status([("sql", "refused"), ("policy", "answered")]) == "partial"
    assert derive_status([("sql", "error"), ("policy", "answered")]) == "failed"
    assert derive_status([("sql", "needs_review"), ("policy", "answered")]) == "escalated"
    assert derive_status([("sql", "answered"), ("draft", "awaiting_approval")]) == "awaiting_approval"


def test_ids_unique():
    ids = [t["id"] for t in TASKS]
    assert len(ids) == len(set(ids)) and all(i.startswith("ct-") for i in ids)


def test_gate_set_has_ten():
    assert len(yaml.safe_load((ROOT / "evals/compound/gate.yaml").read_text())) == 10


@pytest.mark.parametrize("t", TASKS, ids=lambda t: t["id"])
def test_task(t):
    assert set(t) <= {"id", "asked_by", "request", "parts", "expect", "notes", "reviewed"}
    assert t["asked_by"] in IDENTITIES
    assert isinstance(t["reviewed"], bool) and t["request"].strip()
    part_ids = [p["id"] for p in t["parts"]]
    assert len(part_ids) == len(set(part_ids))
    for p in t["parts"]:
        assert p["specialist"] in SPECIALISTS and p["expect"] in PART_STATUSES
        assert set(p) == FIELDS[p["specialist"]], f"{t['id']}/{p['id']} fields"
        if p["specialist"] == "sql":
            g = P1_INDEX[p["p1_golden"]]  # must be a reviewed P1 item
            assert (g["asked_by"], g["question"], g["expect"]) == (t["asked_by"], p["question"], p["expect"]), \
                f"{t['id']}/{p['id']} must match P1 {p['p1_golden']} exactly (same person, question, status)"
        if p["specialist"] == "policy":
            assert set(p["cites"]) <= POLICY_PAGES and p["key_point"].strip()
        if p["specialist"] in ("writer", "draft"):
            assert set(p["uses"]) <= set(part_ids) - {p["id"]}
        if p["specialist"] == "draft":
            assert p["expect"] == "awaiting_approval"
    assert [p["specialist"] for p in t["parts"]].count("writer") == 1, "exactly one summary per task"
    assert t["parts"][-1]["specialist"] in ("writer", "draft"), "writer/draft come last"
    assert t["expect"] in TASK_STATUSES and t["expect"] == derive_status([(p["specialist"], p["expect"]) for p in t["parts"]]), f"{t['id']} expect != derived"
