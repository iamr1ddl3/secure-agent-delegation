"""The P1 client checks every request and every reply against the vendored query_bank_data v1 schema.

Offline: P1 is replaced by a fake transport that returns recorded real replies (evals/recordings/p1_replies.json,
made by scripts/record_p1_replies.py against a running P1).
"""
import asyncio
import copy
import json
import re
from pathlib import Path

import pytest

from secure_agent_delegation.handoffs import SpecialistResult
from secure_agent_delegation.p1_client import P1CallError, P1Client, P1ContractError, check_response

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "interface/p1/examples"
RECORDINGS = json.loads((ROOT / "evals/recordings/p1_replies.json").read_text())
GATE_GOLDEN = {"st-07", "ag-07", "st-04", "pb-15", "jn-17", "jn-12", "ag-22", "jn-05", "st-06", "jn-02", "os-06"}
TOKEN = "eyJ" + "x" * 40  # shape of a JWT; P2 never checks it, P1 does


def _client(reply, sent=None):
    async def call(args):
        if sent is not None:
            sent.append(args)
        if isinstance(reply, Exception):
            raise reply
        return copy.deepcopy(reply)
    return P1Client("http://unused", call=call)


def _ask(client, question="How many loans are overdue?", identity=TOKEN, **kw):
    return asyncio.run(client.query(question, identity, **kw))


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("response.*.json")), ids=lambda p: p.stem)
def test_contract_examples_pass(path):
    check_response(json.loads(path.read_text()))


def test_recordings_cover_every_gate_golden_item():
    assert set(RECORDINGS) >= GATE_GOLDEN


@pytest.mark.parametrize("gid", sorted(RECORDINGS))
def test_recorded_reply_passes_and_fits_a_sql_result(gid):
    rec = RECORDINGS[gid]
    reply = _ask(_client(rec["response"]), rec["question"])
    assert reply == rec["response"]
    SpecialistResult(subtask_id="a", specialist="sql", status=reply["status"], p1_response=reply)


def test_recorded_statuses_match_p1_golden_expectations():
    index = json.loads((ROOT / "evals/p1_golden_index.json").read_text())["items"]
    for gid, rec in RECORDINGS.items():
        if gid in index:
            assert rec["asked_by"] == index[gid]["asked_by"] and rec["question"] == index[gid]["question"], gid
            assert rec["response"]["status"] == index[gid]["expect"], gid


def test_recordings_hold_no_tokens():
    text = json.dumps(RECORDINGS)
    assert not re.search(r"eyJ[\w-]{10,}", text)
    assert "identity" not in {k for rec in RECORDINGS.values() for k in rec}


def _answered():
    return json.loads((EXAMPLES / "response.answered.json").read_text())


@pytest.mark.parametrize("break_it", [
    lambda r: r.pop("status"),
    lambda r: r.update(status="ok"),
    lambda r: r.update(schema_version="2"),
    lambda r: r.update(row_count=-1),
    lambda r: r["columns"][0].update(secret="x"),
    lambda r: r["confidence"].update(router=1.5),
    lambda r: r.update(error={"code": "teapot", "message": "x"}),
], ids=["no-status", "unknown-status", "v2", "negative-rows", "extra-column-field", "confidence>1", "unknown-error"])
def test_reply_that_breaks_the_contract_is_rejected(break_it):
    bad = _answered()
    break_it(bad)
    with pytest.raises(P1ContractError):
        _ask(_client(bad))


def test_non_dict_reply_is_rejected():
    with pytest.raises(P1ContractError):
        _ask(_client(None))


@pytest.mark.parametrize("kw", [
    {"question": ""}, {"question": "x" * 1001}, {"identity": "short"}, {"max_rows": 0}, {"max_rows": 1001},
], ids=["empty-question", "long-question", "short-identity", "zero-rows", "too-many-rows"])
def test_bad_request_is_rejected_before_anything_is_sent(kw):
    sent = []
    with pytest.raises(P1ContractError):
        _ask(_client(_answered(), sent), **kw)
    assert sent == []


def test_request_carries_identity_unchanged_and_names_p2_in_the_chain():
    sent = []
    _ask(_client(_answered(), sent), task_id="task-1")
    (args,) = sent
    assert args["identity"] == TOKEN
    assert args["on_behalf_of_chain"] == [{"agent_id": "secure-agent-delegation", "agent_version": "0.0.1",
                                           "task_id": "task-1"}]


def test_tool_error_is_raised_not_turned_into_an_answer():
    with pytest.raises(P1CallError):
        _ask(_client(P1CallError("tool failed")))


def test_contract_errors_never_echo_the_token():
    with pytest.raises(P1ContractError) as e:
        _ask(_client(_answered()), question="", identity=TOKEN + "!")
    assert TOKEN not in str(e.value)
