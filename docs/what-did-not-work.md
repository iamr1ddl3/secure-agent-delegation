# What did not work

Running log. Becomes the README's "What did not work" section. Log each failure the day it happens: what we tried, why it failed, the fix, the lesson.

## 2026-11-19 · P1's MCP server was unreachable from outside its container

- **Tried:** run P1 v1.0.0 with its own compose command, `python -m secure_sql_agent.mcp_server --http`, published on port 8001.
- **Failed:** the MCP SDK v2 `run()` binds `127.0.0.1` by default, so the server only listened inside the container; the host could not connect. P1's own `docker-compose.yml` has the same problem; P1's tests never caught it because they use stdio or call the service in-process.
- **Fix:** P2's compose starts the same server object with `host='0.0.0.0'` (no P1 code change), and publishes the port on `127.0.0.1` only. Verified: server `secure-sql-agent 1.0.0`, tool `query_bank_data`, a fake token is rejected ("The identity token could not be verified").
- **Lesson:** a transport is not "supported" until something outside the process has called it. P1 follow-up: a host option on `--http` and a container smoke test in P1's CI (a P1 patch release).
