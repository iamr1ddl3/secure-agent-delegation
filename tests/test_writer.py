"""Report writer (task 28): typed findings in, summary out, no tools, no identity. Offline: the model is a fake."""
import json
from pathlib import Path

import pytest
import yaml

from secure_agent_delegation.handoffs import Citation, SpecialistResult
from secure_agent_delegation.writer import WriterError, build_prompt, complete, invented_numbers, write

ROOT = Path(__file__).resolve().parents[1]
P1 = json.loads((ROOT / "evals/recordings/p1_replies.json").read_text())
POLICY = json.loads((ROOT / "evals/recordings/policy_answers.json").read_text())
GATE = yaml.safe_load((ROOT / "evals/compound/gate.yaml").read_text())

SQL = SpecialistResult(subtask_id="a", specialist="sql", status="answered", p1_response=P1["jn-12"]["response"])
REFUSED = SpecialistResult(subtask_id="a", specialist="sql", status="refused", p1_response=P1["pb-15"]["response"])
POL = SpecialistResult(subtask_id="b", specialist="policy", status="answered",
                       answer="A Branch Manager may waive up to Rs 5,000 per loan per financial year.",
                       citations=[Citation(page="fee-waiver-authority", section="Loan charges")])
REQ = "Average CTC per department, and what is the waiver limit? Summarise."


def fake(summary, unavailable=()):
    def llm(system, user):
        return json.dumps({"summary": summary, "unavailable": list(unavailable)})
    return llm


def test_summary_becomes_an_answered_writer_result():
    r = write("c", REQ, [SQL, POL], fake("Audit averages Rs 13,85,680. Managers may waive up to Rs 5,000."))
    assert (r.subtask_id, r.specialist, r.status) == ("c", "writer", "answered") and "13,85,680" in r.answer


@pytest.mark.parametrize("text", ["Branch ops average Rs 9,18,289.09.", "Branch ops average Rs 9,18,289.",
                                  "Branch ops average 918289.0909."], ids=["2dp", "0dp", "raw"])
def test_rounded_input_numbers_are_allowed(text):
    write("c", REQ, [SQL, POL], fake(text))


@pytest.mark.parametrize("text", ["Branch ops average Rs 9.18 lakh.", "Total across departments: Rs 1,23,45,678.",
                                  "The loan count is about 40."], ids=["unit-conversion", "computed-sum", "guess"])
def test_numbers_not_in_the_inputs_are_rejected(text):
    with pytest.raises(WriterError, match="not in the findings"):
        write("c", REQ, [SQL, POL], fake(text))


def test_refused_part_must_be_named_unavailable():
    with pytest.raises(WriterError, match="unavailable"):
        write("c", REQ, [REFUSED, POL], fake("Managers may waive up to Rs 5,000."))
    r = write("c", REQ, [REFUSED, POL], fake("The loan count is not available to you. Managers: Rs 5,000.", ["a"]))
    assert r.status == "answered"


def test_answered_part_must_not_be_named_unavailable():
    with pytest.raises(WriterError, match="unavailable"):
        write("c", REQ, [SQL, POL], fake("Nothing.", ["a"]))


@pytest.mark.parametrize("reply", ["Here is your summary.", '{"summary": "x"', '{"summary": "", "unavailable": []}'],
                         ids=["not-json", "truncated", "empty"])
def test_bad_model_reply_is_an_error(reply):
    with pytest.raises(WriterError):
        write("c", REQ, [SQL], lambda s, u: reply)


def test_writer_sees_rows_and_explanations_but_no_sql_trace_or_policy_hits():
    system, user = build_prompt(REQ, [SQL, REFUSED, POL])
    assert "data, not instructions" in system
    assert "1385680" in user and P1["pb-15"]["response"]["explanation"] in user and "fee-waiver-authority" in user
    for leak in ("SELECT", "trace_id", "policy_hits", P1["jn-12"]["response"]["trace_id"]):
        assert leak not in user


def test_writer_inputs_never_hold_a_token():
    _, user = build_prompt(REQ, [SQL, REFUSED, POL])
    assert "eyJ" not in user and "identity" not in user


def test_invented_numbers_ignores_numbers_from_the_request():
    assert invented_numbers("You asked about 7 departments.", "7 departments") == []


def test_complete_finds_missing_values():
    assert complete("Audit 13,85,680", [SQL]) is False
    allv = " ".join(f"{d} {v}" for d, v in SQL.p1_response["rows"])
    assert complete(allv, [SQL]) is True


@pytest.mark.parametrize("task", GATE, ids=lambda t: t["id"])
def test_every_gate_task_has_recorded_findings(task):
    for p in task["parts"]:
        if p["specialist"] == "sql":
            assert p["p1_golden"] in P1
        elif p["specialist"] == "policy":
            assert f"{task['id']}/{p['id']}" in POLICY


def test_each_finding_carries_the_question_it_answers():
    _, user = build_prompt(REQ, [SQL], {"a": "What is the average current annual CTC per department?"})
    assert '"asked": "What is the average current annual CTC per department?"' in user
