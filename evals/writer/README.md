# Report writer eval

The writer (tracker task 28) gets the request and the typed findings of the parts it `uses`, and returns a short
summary. It has no tools and never sees the user's token: the findings carry no identity, and only the rows, column
names and P1's one-line explanation of each data part reach it (no SQL, no trace ids).

Set: the 10 gate tasks (`evals/compound/gate.yaml`). Inputs are recorded, so the writer is measured alone:
data parts from `evals/recordings/p1_replies.json` (real P1 replies), policy parts from
`evals/recordings/policy_answers.json` (real policy agent answers).

Checks per task (`secure_agent_delegation.writer`):

| Check | Rule | Enforced at run time? |
| --- | --- | --- |
| Unavailable parts named | `unavailable` lists exactly the parts that were not answered | yes: otherwise an error |
| No invented numbers | every number in the summary is a number from the inputs, possibly rounded (918289.09 → 9,18,289) | yes: otherwise an error |
| Complete | every value of every answered data part appears in the summary (numbers by the rounding rule, text case-insensitively) | no, eval only |

## Targets (set 2026-11-19, before the first run)

| Metric | Target |
| --- | --- |
| Tasks passing all three checks | ≥ 9 / 10 |
| Tasks with an invented number | 0 |
| Unavailable parts named correctly | 10 / 10 |

`scripts/eval_writer.py` writes `evals/writer/results.md`.
