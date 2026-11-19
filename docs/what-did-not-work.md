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

## 2026-11-19 · The policy agent's model wrote prose before its JSON

- **Tried:** ask Haiku 5.5 for "JSON only" in the system prompt and parse the reply. It passed the 20-question policy eval.
- **Failed:** on the first new question (the KYC-refresh key point of gate task ct-03) it wrote the answer as prose, then the JSON. The parser rejected it, as designed (an error, never a silent answer), so the run stopped.
- **Fix:** request JSON at the API (`response_format: json_object`, supported by Haiku 5.5 and both challengers on OpenRouter), not by asking nicely. The parser stays strict; no "find the JSON somewhere in the text" fallback.
- **Lesson:** 20 passing questions did not cover the output format; the 21st did. Format is enforced by the API where it can be, and checked in code either way.

## 2026-11-19 · The writer distrusted correct data it could not place

- **Tried:** give the report writer each part's status, rows and P1's one-line note.
- **Failed:** on gate task ct-03 (expired-KYC customers) it told the user the 54 rows "should not be read as the expired ones", because the rows have only an ID and a name and P1's note just says "Returned 54 row(s) from bank.customers". The rows were right; the writer could not see the question they answered.
- **Fix:** every finding carries what was asked for it (`asked`: the question sent to P1, or the policy question), and the prompt says the rows answer that question.
- **Lesson:** a typed hand-off needs the question as well as the answer. Found by reading the first eval output, before any score was computed.
