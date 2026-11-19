# Policy agent mini-eval

20 questions for the policy agent alone (no supervisor), written before the agent (tracker task 23).

Item: `id`, `question`, `cites` (expected page ids; any one counts as a hit), `section` (the `##` heading of the
first cited page that holds the answer), `must_include` (short facts the answer must state; the format test proves
each one is in that section, so every answerable item is answerable from the corpus), `expect` (`answered` or
`refused`), optional `notes`.

Metrics (computed once the agent exists, task 27):

| Metric | Definition |
| --- | --- |
| Hit rate @5 | Share of answerable items where an expected page is among the top 5 retrieved chunks |
| MRR | Mean of 1 / rank of the first chunk from an expected page (0 if absent) |
| Faithfulness | Share of answerable items whose answer states every `must_include` fact and cites an expected page |
| Refusal score | Share of `refused` items where the agent says the policies do not cover it and cites nothing |

These are the Novus Bank RAG metrics (D3), measured on this corpus. A held-out set comes later if retrieval or
prompts get tuned against this one.

## Targets (set 2026-11-19, before the first run)

| Metric | Target | Why |
| --- | --- | --- |
| Hit rate @5 | ≥ 16 / 17 | One miss allowed; a miss means the writer gets no policy text for that part |
| MRR | ≥ 0.80 | The right page is usually first, so few excerpts are needed |
| Faithfulness | ≥ 15 / 17 | Exact-fact check (case-insensitive substring), so a correct paraphrase can fail; misses are read by hand |
| Refusal score | 3 / 3 | Inventing a policy is the failure that matters most |

`scripts/eval_policy.py` computes all four; results and the model id go in `evals/policy/results.md`.
