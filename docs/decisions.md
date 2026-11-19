# Decisions

Each decision: date, choice, why, and what it costs. Tracker task numbers in brackets.

## D1 · 2026-11-19 · Repo name: `secure-agent-delegation` (task 4)

Public repo `github.com/iamr1ddl3/secure-agent-delegation`, next to `secure-sql-agent`.

## D2 · 2026-11-19 · P2 reaches P1 over MCP streamable HTTP (task 5)

P1's MCP server already supports it (`python -m secure_sql_agent.mcp_server --http`), so P1 needs no change. P2 runs the P1 `v1.0.0` image as a separate service and calls `query_bank_data` over HTTP, as any outside client would.
- Why: a real network boundary between the two services (closer to production than stdio, and the trace shows the hop); P1 runs and is versioned independently.
- Cost: one more service to run in compose and CI.

## D3 · 2026-11-19 · Policy RAG: Novus Bank RAG patterns, not its code or corpus (task 6)

Reuse what the Novus Bank RAG proved (`aic-production-engineering/Project-A-new`): heading-aware chunking, hybrid dense + keyword retrieval fused with RRF, cited answers, and its eval metrics (hit rate, MRR, faithfulness, refusal score). Change the rest:

| | Novus Bank RAG | P2 policy agent |
| --- | --- | --- |
| Documents | ~19 customer-facing product policies (accounts, cards, UPI, loans), "Novus" brand | ~25 **internal staff** policies for P1's bank: fee-waiver authority, overdue loans and NPA, collections, KYC, customer data sharing, salary confidentiality, escalation to the regional head, outgoing communication. New, documented synthetic text; no "Novus" naming |
| Keyword search | BM25 in Python over all chunks loaded from the DB | Postgres full-text search (`tsvector`, `ts_rank_cd`) |
| Fusion | RRF in Python | RRF in one SQL query, so retrieval is a single round trip |
| Embeddings | OpenAI `text-embedding-3-small` (1536-d), needs an OpenAI key | A small local open model (e.g. `bge-small-en-v1.5`, 384-d): no extra key, free, deterministic in CI. Check retrieval quality on the mini-eval (task 23) before committing |
| Extras | Semantic cache, difficulty router, Cohere reranker | Left out: caching is out of scope per the plan; add a reranker only if the mini-eval shows a retrieval gap |
| New in P2 | | A set of **poisoned** policy pages with canary phrases, flagged, for the stage 3 attack set |

- Why: the corpus has to match P1's bank and the delegation use case ("what does our policy say about fee waivers for overdue loans"), and moving keyword search into Postgres removes the load-all-chunks step.
- Cost: writing ~25 new documents (task 22, about 3 h); the local embedding model may score below OpenAI's; measured, not assumed.

## D4 · 2026-11-19 · Run state and policy store: one local Postgres with pgvector (task 7)

A Postgres + pgvector container in P2's docker compose holds the policy chunks and the LangGraph checkpoints, in separate schemas. It is **not** the Supabase bank database.
- Why: one database family, as in P1; free; and P2 stays completely outside the bank database, which keeps "P2 holds no bank credentials" literally true and easy to test.
- Cost: another container; checkpoints are not as fast as Redis (irrelevant at this scale).

## D5 · 2026-11-19 · Models: Haiku 5.5 plus two cheaper challengers, each role decided by measurement (task 8)

All through OpenRouter, as in P1. Prices in USD per 1M tokens (input / output), from `https://openrouter.ai/api/v1/models` on 2026-11-19:

| Model | Price | Use |
| --- | --- | --- |
| `anthropic/claude-haiku-5.5` | 0.10 / 0.50 | Default for every role at the start (proven in P1) |
| `deepseek/deepseek-v4-flash` | 0.09 / 0.18 | Cheap challenger: ~2.8x cheaper output, tools + structured output |
| `qwen/qwen3.7-flash` | 0.03 / 0.13 | Cheapest challenger: ~3.8x cheaper output, tools + structured output |
| `anthropic/claude-sonnet-5.5` | 2 / 10 | Planner-only challenger, kept only if it wins by more than noise |

Rule: per role (planner, policy agent, writer), the cheapest model wins if it is within 2 points of Haiku on that role's eval, with no extra false blocks. The writer and the policy agent are the likeliest roles to move to a cheap model; the planner decides routing, so it switches only on clear evidence.
- Why: P2 makes several model calls per task, so a cheaper default lowers cost per task for as long as the demo runs. Security does not depend on the model (the database and the graph enforce it), so a cheaper model risks quality, never leaks.
- Lesson carried from P1: qwen3-coder was as cheap as Haiku but scored 75.5% vs 96.8% on SQL, with 6.7% false blocks. Cheap is adopted per role on numbers, never by default.
- Cost: one comparison run per role (tracker task 75); model ids are pinned in P2's `config/models.yaml` and recorded in every eval report.

## D6 · 2026-11-19 · Outgoing drafts: the requester approves their own draft (task 9)

`POST /v1/tasks/{id}/approve` accepts only the user who started the task. Approving marks the draft approved; nothing is actually sent (writes are out of scope).
- Why: the draft can only contain what P1 already let the requester see, and anything that needed review never reaches the draft (it is escalated instead). P1's two-person rule stays where it matters: bulk raw PII.
- Cost: no second pair of eyes on wording. Tests (task 55): another user's approval is refused; approving twice is refused; an escalated job never produces a draft.

## D7 · 2026-11-19 · Stack (task 15)

Python 3.11, LangGraph (supervisor + specialists), MCP Python SDK v2 client over streamable HTTP, Pydantic for the hand-off types, Postgres 16 + pgvector (local container) for checkpoints and the policy store, OpenRouter for models (D5), Langfuse for traces, pytest + ruff, GitHub Actions. P1 runs from its `v1.0.0` git tag, built by compose. Same family as P1 on purpose: one set of tools to learn, and the P2 story is delegation, not new tech.
- Cost: LangGraph's checkpointer API ties run state to its format; acceptable for a demo, recorded in the wiki's StackChoices.
- Runtime dependencies are added with the code that imports them, not up front.

## Open

- **Delegation token design** (task 37): forward the user's token, or exchange it for narrowed per-specialist tokens (needs a P1 v1.1 release). Decide in stage 2.
