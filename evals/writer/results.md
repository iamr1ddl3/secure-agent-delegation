# Report writer eval results

Latest run 2026-11-19T1210Z: model `anthropic/claude-haiku-5.5`, 10 gate tasks, recorded findings.

| Metric | Result | Target | Pass |
| --- | --- | --- | --- |
| Tasks passing all checks | 10 / 10 | ≥ 9 / 10 | yes |
| Tasks with an invented number | 0 | 0 | yes |
| Unavailable parts named correctly | 10 / 10 | 10 / 10 | yes |
| Complete (every value present) | 10 / 10 | | |

Cost: $0.0039 for 10 tasks. p95 time per task: 9.0 s.

## Misses

None.

## Read by hand (2026-11-19 run)

ct-03 lists all 54 expired-KYC customers and the KYC rules; ct-04 says the loan count is not available to a teller
and gives no estimate; ct-10 says nothing was deleted and refuses to confirm it. Style note: the writer says
"Part (a)", an internal label; harmless, tidied when the supervisor writes the final answer.
