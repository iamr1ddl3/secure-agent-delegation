# Compound tasks

A compound task is one realistic request from a bank staff member that needs more than one specialist: data
from the P1 SQL agent, an answer from the bank's policy documents, a written summary, and sometimes a draft that
waits for the requester's approval. P2 is scored on whole tasks; see the guide section "Evals for a multi-agent
system".

Files: `gate.yaml` is the stage 1 gate set (10 tasks). The rest of the ~40 come in tracker task 19.
`tests/test_compound_format.py` checks every rule below without a database or a model.

## Item format

```yaml
- id: ct-01                      # unique, ct-NN
  asked_by: manager.surat        # one of P1's 7 demo identities; every part runs as this person
  request: >-                    # the whole request, as the person would type it
    ...
  parts:                         # what a correct plan contains (order is not scored, except writer/draft last)
    - id: a
      specialist: sql            # sql | policy | writer | draft
      p1_golden: st-07           # sql parts only: a human-reviewed P1 golden item asked by the same person
      question: ...              # sql parts only: that item's question, copied exactly (the test checks it)
      expect: answered           # P1's expected status for that item, copied exactly
    - id: b
      specialist: policy
      cites: [fee-waiver-authority]   # the policy page(s) the answer must cite
      key_point: ...                  # what the answer must convey, in one sentence
      expect: answered
    - id: c
      specialist: writer         # no tools; turns typed findings into a summary
      uses: [a, b]               # the parts it summarises
      expect: answered
    - id: d
      specialist: draft          # optional; draft-only, never sent
      uses: [a, b]
      expect: awaiting_approval
  expect: completed              # derived from the parts, see below
  notes: ...                     # optional: why this task exists, what it tests
  reviewed: false                # true only after a human check (tracker task 20)
```

### Why data parts point at P1 golden items

The right answer for a data part is the right answer P1's golden set already holds for the same question and the
same person, checked by a human and verified against the database two ways. P2 holds no bank-database credentials,
so it cannot compute truth itself; reusing P1's reviewed items keeps it that way. `evals/p1_golden_index.json` is
a copy of P1's index (id, person, question, expected status) made by `scripts/vendor_p1_golden.py` from the pinned
P1 tag. The expected rows are exported from P1 when the harness is built (task 21).

### Part statuses

`sql` parts carry P1's own statuses unchanged: `answered`, `refused`, `needs_review`, `needs_clarification`.
`policy` and `writer` parts are `answered` (a policy part may be `refused` once out-of-scope tasks are added).
A `draft` part is `awaiting_approval`: only the person who asked can approve it, and approving never sends anything
(decision D6).

### Task status, derived from the parts (writer excluded)

| Task `expect` | When |
| --- | --- |
| `refused` | every non-writer part is `refused` |
| `escalated` | any part is `needs_review` (a human must decide; nothing is guessed) |
| `needs_clarification` | any part is `needs_clarification` |
| `partial` | some parts `refused`, the rest `answered` (the summary says what could not be done) |
| `awaiting_approval` | a draft is waiting for approval and every other part is `answered` |
| `completed` | every part `answered` |

Checked in that order. A refusal is never "worked around": the writer must say the part could not be answered and
must not fill it in from anywhere else.

### Scoring (built in task 21)

A task passes when the plan contains the expected specialists, every part ends in its expected status, every
`answered` sql part matches P1's truth rows, every policy part cites the expected page and conveys the key point,
and the summary uses the numbers it was given (and says which parts were refused). Reported: task completion rate,
per-part correctness, cost per task, p95 time per task, escalation rate.

### Policy page ids

Policy parts cite pages of the synthetic policy corpus in `policies/` by file name (without `.md`); the format
test fails if a cited page does not exist.
