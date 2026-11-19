"""Policy store: heading-aware chunks of the policy corpus in P2's own Postgres + pgvector (decisions D3, D4).

One chunk per `##` section, so a retrieved chunk is exactly what an answer cites (page + section). The embedded text
is "title — section" plus the body. A generated `tsvector` column serves keyword search; the vector column serves
dense search. This database holds policy text only, never bank data.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
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


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding  # imported here so tests and CI never load the model

    return TextEmbedding(MODEL)


def embed_with_model(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _model().passage_embed(texts)]


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


@dataclass(frozen=True)
class Hit:
    page: str
    section: str
    title: str
    body: str
    score: float


RRF_K = 60  # standard reciprocal-rank-fusion constant
_SEARCH = """
WITH q AS (SELECT %(v)s::vector AS v,
                  replace(plainto_tsquery('english', %(q)s)::text, '&', '|')::tsquery AS t),  -- any word, not all
dense AS (SELECT page, section, row_number() OVER (ORDER BY embedding <=> q.v) AS r
          FROM {schema}.chunks, q ORDER BY embedding <=> q.v LIMIT %(n)s),
kw AS (SELECT page, section, row_number() OVER (ORDER BY ts_rank_cd(tsv, q.t) DESC) AS r
       FROM {schema}.chunks, q WHERE tsv @@ q.t ORDER BY ts_rank_cd(tsv, q.t) DESC LIMIT %(n)s)
SELECT c.page, c.section, c.title, c.body,
       coalesce(1.0 / (%(rrf)s + d.r), 0) + coalesce(1.0 / (%(rrf)s + k.r), 0) AS score
FROM dense d FULL JOIN kw k USING (page, section) JOIN {schema}.chunks c USING (page, section)
ORDER BY score DESC, c.page, c.section LIMIT %(k)s
"""


def search(conn: Connection, question: str, query_vector: list[float], *, k: int = 5, pool: int = 20,
           schema: str = "policy") -> list[Hit]:
    """Hybrid search: dense (pgvector cosine) and keyword (tsvector) ranks fused with RRF, in one SQL round trip."""
    rows = conn.execute(sql.SQL(_SEARCH).format(schema=sql.Identifier(schema)),
                        {"v": str(list(query_vector)), "q": question, "n": pool, "k": k, "rrf": RRF_K}).fetchall()
    return [Hit(*r[:4], float(r[4])) for r in rows]


def embed_query_with_model(text: str) -> list[float]:
    return next(iter(_model().query_embed([text]))).tolist()
