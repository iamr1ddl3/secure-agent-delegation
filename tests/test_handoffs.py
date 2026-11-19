"""Contract tests for the typed hand-offs (src/secure_agent_delegation/handoffs.py)."""
import json
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from secure_agent_delegation import handoffs as h

ROOT = Path(__file__).resolve().parents[1]
GATE = yaml.safe_load((ROOT / "evals/compound/gate.yaml").read_text())
P1_REFUSED = json.loads((ROOT / "interface/p1/examples/response.refused.json").read_text())
P1_ANSWERED = json.loads((ROOT / "interface/p1/examples/response.answered.json").read_text())


def st(i, sp, uses=()):
    return {"id": i, "specialist": sp, "instruction": "x", "uses": list(uses)}


def plan(*subtasks):
    return h.Plan.model_validate({"subtasks": list(subtasks)})


def test_valid_plan():
    plan(st("a", "sql"), st("b", "policy"), st("c", "writer", "ab"), st("d", "draft", "ab"))


@pytest.mark.parametrize("subtasks, why", [
    ([st("a", "email"), st("b", "writer", "a")], "unknown specialist"),
    ([st("a", "sql"), st("b", "writer", "z")], "uses a later or missing subtask"),
    ([st("b", "writer", "a"), st("a", "sql")], "writer before the data it uses"),
    ([st("a", "sql"), st("b", "writer"), st("c", "policy")], "policy after writer"),
    ([st("a", "sql"), st("b", "writer"), st("c", "writer")], "two writers"),
    ([st("a", "sql")], "no writer"),
    ([st("a", "sql"), st("a", "policy"), st("b", "writer")], "duplicate id"),
    ([st("a", "sql"), st("b", "sql", "a"), st("c", "writer")], "sql reading another result"),
    ([st(c, "sql") for c in "abcdefgh"] + [st("i", "writer")], "more than 8 subtasks"),
    ([{**st("a", "sql"), "token": "eyJ"}, st("b", "writer")], "extra field"),
])
def test_invalid_plans_rejected(subtasks, why):
    with pytest.raises(ValidationError):
        plan(*subtasks)


def test_sql_result_carries_p1_status_unchanged():
    h.SpecialistResult(subtask_id="a", specialist="sql", status="refused", p1_response=P1_REFUSED)
    with pytest.raises(ValidationError):  # a refusal relabelled as an answer
        h.SpecialistResult(subtask_id="a", specialist="sql", status="answered", p1_response=P1_REFUSED)
    with pytest.raises(ValidationError):  # a sql result without P1's response
        h.SpecialistResult(subtask_id="a", specialist="sql", status="answered")
    with pytest.raises(ValidationError):  # only sql carries a P1 response
        h.SpecialistResult(subtask_id="b", specialist="writer", status="answered", p1_response=P1_ANSWERED)


def test_policy_answer_needs_a_citation():
    with pytest.raises(ValidationError):
        h.SpecialistResult(subtask_id="b", specialist="policy", status="answered", answer="Yes.")
    h.SpecialistResult(subtask_id="b", specialist="policy", status="refused", answer="Not covered.")


def test_only_draft_waits_for_approval():
    with pytest.raises(ValidationError):
        h.SpecialistResult(subtask_id="c", specialist="writer", status="awaiting_approval")


def _result(sp, status):
    p1 = {"answered": P1_ANSWERED, "refused": P1_REFUSED}.get(status) if sp == "sql" else None
    return h.SpecialistResult(subtask_id="a", specialist=sp, status=status, p1_response=p1,
                              citations=[h.Citation(page="kyc-refresh", section="x")] if sp == "policy" else [])


def test_task_status_must_match_parts():
    parts = [_result("sql", "refused"), _result("policy", "answered"), _result("writer", "answered")]
    h.TaskResult(task_id="t", status="partial", results=parts, summary="s")
    with pytest.raises(ValidationError):
        h.TaskResult(task_id="t", status="completed", results=parts, summary="s")


def test_draft_present_exactly_with_a_draft_result():
    parts = [_result("sql", "answered"), _result("writer", "answered"), _result("draft", "awaiting_approval")]
    with pytest.raises(ValidationError):
        h.TaskResult(task_id="t", status="awaiting_approval", results=parts, summary="s")
    h.TaskResult(task_id="t", status="awaiting_approval", results=parts, summary="s",
                 draft=h.Draft(subject="Reminder", body="Dear customer", uses=["a"]))


def test_no_handoff_can_carry_a_token_or_identity():
    words = ("token", "identity", "jwt", "password", "secret", "credential")
    for model in (m for m in vars(h).values() if isinstance(m, type) and issubclass(m, BaseModel)):
        for field in model.model_fields:
            assert not any(w in field.lower() for w in words), f"{model.__name__}.{field}"


@pytest.mark.parametrize("task", GATE, ids=lambda t: t["id"])
def test_every_gate_task_is_a_valid_plan(task):
    plan(*({"id": p["id"], "specialist": p["specialist"],
            "instruction": p.get("question") or p.get("key_point") or "summarise",
            "uses": p.get("uses", [])} for p in task["parts"]))
