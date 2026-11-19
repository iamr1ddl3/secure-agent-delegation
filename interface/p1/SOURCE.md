# Vendored P1 contract

Copied unchanged from `iamr1ddl3/secure-sql-agent` tag `v1.0.0` (commit `134e246c69b9631c8b846701110447e30513d613`);
identical in the pinned runtime release `v1.0.1` (commit `8f6b6991c1b0e4bf6631b8368acf1e9f85613e08`, only the MCP HTTP bind changed):
`interface/query_bank_data.v1.schema.json` and `interface/examples/*.json`.

`tests/test_p1_contract.py` pins the schema's SHA-256. To move to a new P1 release: copy the files from that tag,
update the tag, commit and hash here and in the test, and re-run the eval. Never edit these files by hand.
