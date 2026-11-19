"""Policy store: heading-aware chunks of the policy corpus in P2's own Postgres + pgvector (decisions D3, D4).

One chunk per `##` section, so a retrieved chunk is exactly what an answer cites (page + section). The embedded text
is "title — section" plus the body. A generated `tsvector` column serves keyword search; the vector column serves
dense search. This database holds policy text only, never bank data.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from psycopg import Connection, sql

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
MAX_CHARS = 2000  # ponytail: no section splitter; largest section is ~700 chars. Split paragraphs if this trips.
SKIP_SECTIONS = {"Related"}  # bare lists of page ids: noise for retrieval

Embed = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class Chunk:
    page: str
    section: str
    title: str
    version: str
    body: str

    @property
    def text(self) -> str:
        return f"{self.title} — {self.section}\n\n{self.body}"


def chunk_page(md: str) -> list[Chunk]:
    _, front, body = md.split("---\n", 2)
    meta = yaml.safe_load(front)
    out = []
    for part in re.split(r"^## ", body, flags=re.MULTILINE)[1:]:
        heading, _, text = part.partition("\n")
        heading, text = heading.strip(), text.strip()
        if heading not in SKIP_SECTIONS:
            out.append(Chunk(meta["id"], heading, meta["title"], str(meta["version"]), text))
    return out


def chunk_corpus(folder: Path) -> list[Chunk]:
    return [c for p in sorted(folder.glob("*.md")) if p.name != "README.md" for c in chunk_page(p.read_text())]


def embed_with_model(texts: list[str]) -> list[list[float]]:
    from fastembed import TextEmbedding  # imported here so tests and CI never load the model

    return [v.tolist() for v in TextEmbedding(MODEL).passage_embed(texts)]


_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS {schema};
CREATE TABLE IF NOT EXISTS {schema}.chunks (
    page            text NOT NULL,
    section         text NOT NULL,
    title           text NOT NULL,
    version         text NOT NULL,
    body            text NOT NULL,
    embedding       vector({dim}) NOT NULL,
    embedding_model text NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || section || ' ' || body)) STORED,
    PRIMARY KEY (page, section)
);
CREATE INDEX IF NOT EXISTS chunks_tsv ON {schema}.chunks USING gin (tsv);
"""  # ponytail: no vector index; ~100 rows scan exactly. Add HNSW if the corpus reaches thousands of chunks.


def load(conn: Connection, chunks: list[Chunk], embed: Embed, *, model: str = MODEL, schema: str = "policy") -> int:
    """Replace the whole store with `chunks` in one transaction. Embeds first, so a model failure changes nothing."""
    vectors = embed([c.text for c in chunks])
    s = sql.Identifier(schema)
    with conn.transaction():
        conn.execute(sql.SQL(_DDL).format(schema=s, dim=sql.Literal(DIM)))
        conn.execute(sql.SQL("DELETE FROM {}.chunks").format(s))
        with conn.cursor() as cur:
            cur.executemany(
                sql.SQL("INSERT INTO {}.chunks (page, section, title, version, body, embedding, embedding_model) "
                        "VALUES (%s, %s, %s, %s, %s, %s::vector, %s)").format(s),
                [(c.page, c.section, c.title, c.version, c.body, str(v), model) for c, v in zip(chunks, vectors,
                                                                                             strict=True)])
    return len(chunks)
