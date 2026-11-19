"""Typed hand-offs between the supervisor and the specialists. Never free text between nodes.

Two rules are enforced by the types themselves:
- A sql result carries P1's own status unchanged: its `status` must equal the status inside `p1_response`,
  so no node can turn a refusal into an answer.
- No hand-off has a field for a token or identity. The user's identity travels in the run state, outside these
  objects, so the writer and the draft step can never see it.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Specialist = Literal["sql", "policy", "writer", "draft"]
PartStatus = Literal["answered", "refused", "needs_review", "needs_clarification", "error", "awaiting_approval"]
TaskStatus = Literal["completed", "partial", "awaiting_approval", "refused", "escalated", "needs_clarification",
                     "failed"]
MAX_SUBTASKS = 8


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SubTask(_Strict):
    id: str = Field(pattern=r"^[a-z]$")
    specialist: Specialist
    instruction: str = Field(min_length=1, max_length=1000)  # for sql: the question sent to P1 as-is
    uses: list[str] = []  # earlier subtasks whose results this one reads (writer / draft)


class Plan(_Strict):
    subtasks: list[SubTask] = Field(min_length=1, max_length=MAX_SUBTASKS)

    @model_validator(mode="after")
    def _shape(self) -> Plan:
        seen: set[str] = set()
        for s in self.subtasks:
            if s.id in seen:
                raise ValueError(f"duplicate subtask id {s.id}")
            if not set(s.uses) <= seen:
                raise ValueError(f"subtask {s.id} uses a subtask that does not come before it")
            if s.uses and s.specialist not in ("writer", "draft"):
                raise ValueError(f"only writer and draft may use other results ({s.id} is {s.specialist})")
            seen.add(s.id)
        kinds = [s.specialist for s in self.subtasks]
        if kinds.count("writer") != 1 or kinds.count("draft") > 1:
            raise ValueError("a plan has exactly one writer and at most one draft")
        tail = [k for k in kinds if k in ("writer", "draft")]
        if kinds[-len(tail):] != tail:
            raise ValueError("writer and draft come after every sql and policy subtask")
        return self


class Citation(_Strict):
    page: str  # policy page id, e.g. "fee-waiver-authority"
    section: str


class SpecialistResult(_Strict):
    subtask_id: str
    specialist: Specialist
    status: PartStatus
    answer: str | None = None  # policy and writer text
    p1_response: dict | None = None  # sql only: P1's query_bank_data v1 response, unchanged
    citations: list[Citation] = []

    @model_validator(mode="after")
    def _consistent(self) -> SpecialistResult:
        if self.specialist == "sql":
            if self.p1_response is None or self.status != self.p1_response.get("status"):
                raise ValueError("a sql result must carry P1's response and P1's status unchanged")
        elif self.p1_response is not None:
            raise ValueError("only sql results carry a P1 response")
        if self.specialist == "policy" and self.status == "answered" and not self.citations:
            raise ValueError("an answered policy result must cite at least one page")
        if self.status == "awaiting_approval" and self.specialist != "draft":
            raise ValueError("only a draft waits for approval")
        return self


class Draft(_Strict):
    """Draft-only output. Nothing is sent; only the requester can approve it (decision D6)."""
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    uses: list[str]


def derive_status(parts: list[tuple[str, str]]) -> TaskStatus:
    """Task status from (specialist, part status) pairs, writer excluded. Order as in evals/compound/README.md."""
    s = [status for specialist, status in parts if specialist != "writer"]
    if s and all(x == "refused" for x in s):
        return "refused"
    if "error" in s:
        return "failed"
    if "needs_review" in s:
        return "escalated"
    if "needs_clarification" in s:
        return "needs_clarification"
    if "refused" in s:
        return "partial"
    if "awaiting_approval" in s:
        return "awaiting_approval"
    return "completed"


class TaskResult(_Strict):
    task_id: str
    status: TaskStatus
    results: list[SpecialistResult]
    summary: str
    draft: Draft | None = None

    @model_validator(mode="after")
    def _status_matches_parts(self) -> TaskResult:
        expected = derive_status([(r.specialist, r.status) for r in self.results])
        if self.status != expected:
            raise ValueError(f"task status {self.status} does not match its parts ({expected})")
        if (self.draft is None) == any(r.specialist == "draft" for r in self.results):
            raise ValueError("a draft is present exactly when a draft result is")
        return self
