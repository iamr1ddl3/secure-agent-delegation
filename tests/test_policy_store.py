"""Policy store (task 26): heading-aware chunks of the policy corpus, loaded into P2's own Postgres + pgvector.

Chunk tests run everywhere. Load tests need STATE_DATABASE_URL (local compose `state-db`, or the CI service) and use
a fake embedder, so they never download a model; the real model is used by scripts/load_policies.py.
"""
import hashlib
import os
from pathlib import Path

import pytest
import yaml

from secure_agent_delegation.policy_store import DIM, MAX_CHARS, Chunk, chunk_corpus, chunk_page, load

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = chunk_corpus(ROOT / "policies")
QUESTIONS = yaml.safe_load((ROOT / "evals/policy/questions.yaml").read_text())
PAGE = """---
id: demo-page
title: Demo Page
version: 2.0
---

# Demo Page

> Synthetic notice.

## Purpose

Why this exists.

## Rules

- **Never** do X.
- Do Y within 7 days.

## Related

other-page.
"""


def test_one_chunk_per_section_without_front_matter_or_related():
    chunks = chunk_page(PAGE)
    assert [(c.page, c.section) for c in chunks] == [("demo-page", "Purpose"), ("demo-page", "Rules")]
    assert chunks[1].title == "Demo Page" and chunks[1].version == "2.0"
    assert chunks[1].body == "- **Never** do X.\n- Do Y within 7 days."
    assert all("---" not in c.body and "Synthetic notice" not in c.body for c in chunks)


def test_embedding_text_carries_title_and_section():
    c = chunk_page(PAGE)[1]
    assert c.text.startswith("Demo Page — Rules\n\n") and c.text.endswith("within 7 days.")


def test_corpus_chunks_are_unique_and_small():
    keys = [(c.page, c.section) for c in CHUNKS]
    assert len(keys) == len(set(keys))
    assert {c.page for c in CHUNKS} == {p.stem for p in (ROOT / "policies").glob("*.md")} - {"README"}
    assert all(0 < len(c.body) <= MAX_CHARS for c in CHUNKS)


@pytest.mark.parametrize("item", [q for q in QUESTIONS if q["expect"] == "answered"], ids=lambda q: q["id"])
def test_every_mini_eval_fact_lives_in_its_cited_chunk(item):
    (chunk,) = [c for c in CHUNKS if (c.page, c.section) == (item["cites"][0], item["section"])]
    flat = " ".join(chunk.body.replace("**", "").split())
    for fact in item["must_include"]:
        assert fact in flat


# --- load into Postgres ----------------------------------------------------------------------------------------

DB = os.environ.get("STATE_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB, reason="STATE_DATABASE_URL not set")


def fake_embed(texts: list[str]) -> list[list[float]]:
    return [[b / 255 for b in hashlib.sha256(t.encode()).digest()] * (DIM // 32) for t in texts]


@pytest.fixture
def conn():
    import psycopg
    with psycopg.connect(DB, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS policy_test CASCADE")
        yield c
        c.execute("DROP SCHEMA IF EXISTS policy_test CASCADE")


@needs_db
def test_load_is_complete_and_idempotent(conn):
    for _ in range(2):
        n = load(conn, CHUNKS, fake_embed, model="fake", schema="policy_test")
    assert n == len(CHUNKS)
    rows = conn.execute("SELECT count(*), count(DISTINCT embedding_model), min(vector_dims(embedding)) "
                        "FROM policy_test.chunks").fetchone()
    assert rows == (len(CHUNKS), 1, DIM)


@needs_db
def test_keyword_search_finds_the_section(conn):
    load(conn, CHUNKS, fake_embed, model="fake", schema="policy_test")
    top = conn.execute("SELECT page, section FROM policy_test.chunks, websearch_to_tsquery('english', %s) q "
                       "WHERE tsv @@ q ORDER BY ts_rank_cd(tsv, q) DESC LIMIT 1",
                       ("teller waive loan charge late-payment",)).fetchone()
    assert top == ("fee-waiver-authority", "Loan charges")


@needs_db
def test_partial_load_rolls_back(conn):
    load(conn, CHUNKS, fake_embed, model="fake", schema="policy_test")

    def broken(texts):
        raise RuntimeError("model died")
    with pytest.raises(RuntimeError):
        load(conn, [*CHUNKS, Chunk("x", "y", "X", "1", "z")], broken, model="fake", schema="policy_test")
    assert conn.execute("SELECT count(*) FROM policy_test.chunks").fetchone()[0] == len(CHUNKS)
