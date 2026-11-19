"""The vendored P1 contract must be exactly the pinned release: any change to it fails the build loudly."""
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

P1 = Path(__file__).resolve().parents[1] / "interface/p1"
SCHEMA_FILE = P1 / "query_bank_data.v1.schema.json"
PINNED_SHA256 = "8f62c804dc72a6ba213d99806b0f5c89f16fee54345e6fc238cb0ed4a0efc5e3"  # P1 v1.0.0 and v1.0.1 (unchanged)
SCHEMA = json.loads(SCHEMA_FILE.read_text())
EXAMPLES = sorted((P1 / "examples").glob("*.json"))


def test_schema_is_pinned_v1_0_0():
    assert hashlib.sha256(SCHEMA_FILE.read_bytes()).hexdigest() == PINNED_SHA256, (
        "P1 contract changed: update it only by copying from a new P1 release tag (interface/p1/SOURCE.md)")


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_match_schema(path):
    kind = "QueryRequest" if path.name.startswith("request.") else "QueryResponse"
    Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{kind}"}).validate(json.loads(path.read_text()))


def test_delegation_chain_is_informational_only():
    # P2 relies on this: the chain is recorded, never used to grant access.
    chain = SCHEMA["$defs"]["QueryRequest"]["properties"]["on_behalf_of_chain"]["description"]
    assert "NEVER used for authorization" in chain
