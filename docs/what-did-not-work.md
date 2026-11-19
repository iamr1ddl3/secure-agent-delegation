# What did not work

Running log. Becomes the README's "What did not work" section. Log each failure the day it happens: what we tried, why it failed, the fix, the lesson.

## 2026-11-19 · P1's MCP server was unreachable from outside its container

- **Tried:** run P1 v1.0.0 with its own compose command, `python -m secure_sql_agent.mcp_server --http`, published on port 8001.
- **Failed:** the MCP SDK v2 `run()` binds `127.0.0.1` by default, so the server only listened inside the container; the host could not connect. P1's own `docker-compose.yml` has the same problem; P1's tests never caught it because they use stdio or call the service in-process.
- **Fix:** P2's compose starts the same server object with `host='0.0.0.0'` (no P1 code change), and publishes the port on `127.0.0.1` only. Verified: server `secure-sql-agent 1.0.0`, tool `query_bank_data`, a fake token is rejected ("The identity token could not be verified").
- **Lesson:** a transport is not "supported" until something outside the process has called it. Resolved the same day by P1 v1.0.1 (`MCP_HOST`, image default `0.0.0.0`, CI container smoke test); P2 now pins v1.0.1 and the command override is gone.

## 2026-11-19 · P1's reply arrives as JSON text, not structured content

- **Tried:** the P1 client read `CallToolResult.structured_content`, as the MCP SDK v2 documents for tools that return data.
- **Failed:** against the live P1 v1.0.1 it was `None` on a good `answered` reply. P1's tool is annotated `-> dict`, which gives the SDK no output schema, so it sends the reply only as one JSON text block. The client raised a call error on a perfectly good answer.
- **Fix:** use `structured_content` when present, otherwise parse the text as JSON; anything that is not JSON, or does not match the vendored v1 schema, is rejected (never repaired). No P1 change: the wire format is P1's actual v1 behaviour.
- **Lesson:** the second "not tested until something outside the process calls it" in a day. The offline tests use recorded live replies for exactly this reason; a hand-written fake would have kept the wrong assumption.
