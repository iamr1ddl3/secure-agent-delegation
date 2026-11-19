# Secure Multi-Agent Delegation

> Part 2 of 2. Part 1 is the [Secure SQL Agent](https://github.com/iamr1ddl3/secure-sql-agent); this project calls it, unchanged, as a specialist.

A supervisor agent that splits a bank staff member's compound request across specialist agents, one of which is the unchanged [Secure SQL Agent](https://github.com/iamr1ddl3/secure-sql-agent) (Project 1), called over MCP. It proves three things: the user's access rights travel with every delegated call, text passed between agents cannot hijack the next agent, and anything sensitive stops for a human.

> **Status: Week 0 (2026-11-19).** Decisions made, repo skeleton, pinned P1 contract with checksum test, P1 v1.0.1 running next to P2 over MCP HTTP. No agent code yet. Results below fill in from CI reports only.

## Results

| Metric | Target | Result |
| --- | --- | --- |
| Cross-agent permission leaks | 0 | not measured yet |
| Attack success by type, before / after defences | Lower after | not measured yet |
| False-block rate on benign compound tasks | Report | not measured yet |
| Task completion rate (~40 compound tasks) | Report | not measured yet |
| Cost per task (ceiling enforced in code) | Report | not measured yet |
| p95 time per task | Report | not measured yet |
| Escalation rate to a human | Report | not measured yet |

## Status

- [x] Week 0: decisions, repo, pinned P1 contract, CI skeleton
- [ ] Stage 1: supervisor, SQL + policy RAG + writer, typed hand-offs, run limits (gate: 10 tasks end to end; loop stopped)
- [ ] Stage 2: identity propagation, confused-deputy suite (gate: 0 cross-agent leaks)
- [ ] Stage 3: cross-agent injection, refusal pass-through, human approval (gate: attack success by type, before/after)
- [ ] Stage 4: durable state, trace endpoint, dashboard (gate: kill-and-resume; a trace per task)
- [ ] Release: results table, 90-second video, "What did not work", v1.0.0

## Run it

```bash
cp .env.example .env                          # P2's own settings: no bank credentials
cp ../secure-sql-agent/.env p1.env            # P1's settings, read only by the p1-mcp container
docker compose up -d --build                  # P1 v1.0.1 (MCP on localhost:8001) + P2's local Postgres
pip install -e ".[dev]" && ruff check . && pytest -q
```

The P1 contract is vendored in [`interface/p1/`](interface/p1/SOURCE.md) from tag `v1.0.0` and pinned by SHA-256, so a change to it fails CI.

## What did not work

See [docs/what-did-not-work.md](docs/what-did-not-work.md).
