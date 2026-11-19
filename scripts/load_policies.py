"""Chunk, embed and load policies/ into the policy store (P2's own Postgres, decisions D3, D4). Safe to re-run.

Usage: python scripts/load_policies.py   (uses $STATE_DATABASE_URL, default the compose state-db)
"""
import os
from pathlib import Path

import psycopg

from secure_agent_delegation.policy_store import MODEL, chunk_corpus, embed_with_model, load

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    url = os.environ.get("STATE_DATABASE_URL", "postgresql://p2:p2-local@localhost:5433/p2")
    chunks = chunk_corpus(ROOT / "policies")
    with psycopg.connect(url) as conn:
        n = load(conn, chunks, embed_with_model)
    print(f"loaded {n} chunks from {len({c.page for c in chunks})} pages with {MODEL}")
