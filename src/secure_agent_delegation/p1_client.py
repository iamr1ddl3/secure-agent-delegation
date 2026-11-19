"""Client for P1's `query_bank_data` tool over MCP streamable HTTP.

Every request is checked against the vendored v1 schema before it is sent, and every reply before it is returned.
A reply that breaks the contract raises; it is never repaired or turned into an answer. The user's token is passed
through unchanged: P1 (and its database) decide access, P2 never looks inside the token.
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from jsonschema import Draft202012Validator

from . import __version__

TOOL = "query_bank_data"
AGENT_ID = "secure-agent-delegation"
# ponytail: read from the repo checkout; ship as package data if P2 is ever installed as a wheel.
_SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "interface/p1/query_bank_data.v1.schema.json").read_text())


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": _SCHEMA["$defs"]})


_REQUEST, _RESPONSE = _validator("QueryRequest"), _validator("QueryResponse")


class P1ContractError(Exception):
    """A request or reply that does not match the query_bank_data v1 schema."""


class P1CallError(Exception):
    """The MCP call itself failed (tool error, no structured result)."""


def _check(validator: Draft202012Validator, obj: object, what: str) -> None:
    errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    if errors:  # path + rule only: jsonschema messages echo values, which could be a token or row data
        raise P1ContractError(f"{what} breaks query_bank_data v1: " +
                              "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.validator}" for e in errors[:5]))


def check_response(reply: object) -> dict:
    _check(_RESPONSE, reply, "P1 reply")
    return reply  # type: ignore[return-value]


Call = Callable[[dict], Awaitable[object]]


class P1Client:
    def __init__(self, url: str, call: Call | None = None):
        self.url = url
        self._call = call or self._mcp_call

    async def _mcp_call(self, args: dict) -> object:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        # ponytail: one session per call; keep a session open if per-call latency shows up in the p95.
        async with streamable_http_client(self.url) as (read, write, *_), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(TOOL, args)
        text = "".join(getattr(c, "text", "") for c in getattr(result, "content", None) or [])
        if getattr(result, "is_error", False):
            raise P1CallError(f"{TOOL} failed: {text[:200] or type(result).__name__}")
        if getattr(result, "structured_content", None) is not None:
            return result.structured_content
        # P1 v1.0.1 annotates the tool as `-> dict`, so the SDK sends the reply as JSON text, not structured content.
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise P1ContractError(f"P1 reply is not JSON ({e.msg})") from None

    async def query(self, question: str, identity: str, *, task_id: str | None = None, max_rows: int = 100) -> dict:
        args = {
            "question": question,
            "identity": identity,
            # informational only; P1 decides access from `identity` alone
            "on_behalf_of_chain": [{"agent_id": AGENT_ID, "agent_version": __version__, "task_id": task_id}],
            "max_rows": max_rows,
        }
        _check(_REQUEST, args, "request to P1")
        return check_response(await self._call(args))
