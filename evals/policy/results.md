# Policy mini-eval results

Latest run 2026-11-19T1157Z: answer model `anthropic/claude-haiku-5.5`, embeddings `BAAI/bge-small-en-v1.5`, hybrid retrieval (dense + keyword, RRF), top 5.

| Metric | Result | Target | Pass |
| --- | --- | --- | --- |
| hit_rate_at_5 | 1.000 | 0.941 | yes |
| mrr | 0.828 | 0.800 | yes |
| faithfulness | 0.882 | 0.882 | yes |
| refusal_score | 1.000 | 1.000 | yes |

Cost: $0.0046 for 20 questions. p95 time per question: 3.1 s.

## Misses

- **pq-08** (answered): How many times a week can we phone a borrower about the same overdue amount?
  - answer: You may phone a borrower at most three times in any seven days about the same overdue amount. The policy also limits visits to one a week.
  - cited: [('collections-contact-rules', 'How often')]
- **pq-12** (answered): I need a list of 50 customers with their phone numbers. Who approves that, and do they see the list?
  - answer: A list of more than 20 rows with raw identifiers, such as phone numbers, is a bulk export and is held for review. A different Branch Manager or an Internal Auditor must approve or reject it, and that approver never sees the data, only the request, reason and query. You cannot approve your own export, and once approved you collect the result once.
  - cited: [('pii-masking-and-bulk-export', 'Bulk exports need a second person'), ('pii-masking-and-bulk-export', 'Raw identifiers')]

## Read by hand (2026-11-19 run)

Both misses are correct answers that the strict substring check rejects: pq-08 says "three times in any seven days"
(policy: "three calls in any seven days"); pq-12 says "that approver never sees the data" (policy: "The approver
never sees the data"). Neither misstates a fact. The check stays strict; a judge model would hide real misses too.

## Retrieval: hybrid against each half alone (17 answerable items, top 5)

| Retrieval | Hit rate @5 | MRR |
| --- | --- | --- |
| Dense only (bge-small, cosine) | 15 / 17 | 0.779 |
| Keyword only (tsvector, any word) | 16 / 17 | 0.681 |
| **Hybrid, RRF in one query** | **17 / 17** | **0.828** |
