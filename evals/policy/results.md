# Policy mini-eval results

Latest run 2026-11-19T1206Z: answer model `anthropic/claude-haiku-5.5`, embeddings `BAAI/bge-small-en-v1.5`, hybrid retrieval (dense + keyword, RRF), top 5.

| Metric | Result | Target | Pass |
| --- | --- | --- | --- |
| hit_rate_at_5 | 1.000 | 0.941 | yes |
| mrr | 0.828 | 0.800 | yes |
| faithfulness | 1.000 | 0.882 | yes |
| refusal_score | 1.000 | 1.000 | yes |

Cost: $0.0049 for 20 questions. p95 time per question: 3.4 s.

## Misses

None.

## Run history

| Run | Output format | Hit @5 | MRR | Faithfulness | Refusal | Cost |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-19 #1 | "JSON only" in the prompt | 17/17 | 0.828 | 15/17 | 3/3 | $0.0046 |
| 2026-11-19 #2 | strict JSON schema at the API | 17/17 | 0.828 | 17/17 | 3/3 | $0.0049 |

Faithfulness moves by ±2 between runs at temperature 0. In run #1, both misses were correct answers that the strict substring check rejects: pq-08 said "three times in any seven days" (policy: "three calls in any seven days"); pq-12 said "that approver never sees the data" (policy: "The approver never sees the data"). Neither misstated a fact. The check stays strict, and 15/17 is the number to quote.

## Retrieval: hybrid against each half alone (17 answerable items, top 5)

| Retrieval | Hit rate @5 | MRR |
| --- | --- | --- |
| Dense only (bge-small, cosine) | 15 / 17 | 0.779 |
| Keyword only (tsvector, any word) | 16 / 17 | 0.681 |
| **Hybrid, RRF in one query** | **17 / 17** | **0.828** |
