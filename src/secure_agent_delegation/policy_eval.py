"""Scoring for the policy mini-eval (evals/policy/README.md): hit rate @5, MRR, faithfulness, refusal score."""
from __future__ import annotations


def _flat(s: str) -> str:
    return " ".join(s.replace("**", "").split()).casefold()


def score(item: dict, retrieved_pages: list[str], status: str, answer: str, cited_pages: list[str]) -> dict:
    if item["expect"] == "refused":
        return {"id": item["id"], "refused_ok": status == "refused" and not cited_pages}
    rank = next((i + 1 for i, p in enumerate(retrieved_pages[:5]) if p in item["cites"]), 0)
    faithful = (status == "answered" and bool(set(cited_pages) & set(item["cites"]))
                and all(_flat(f) in _flat(answer) for f in item["must_include"]))
    return {"id": item["id"], "rank": rank, "faithful": faithful}


def summarise(scores: list[dict]) -> dict:
    ans = [s for s in scores if "rank" in s]
    ref = [s for s in scores if "refused_ok" in s]
    return {"hit_rate_at_5": sum(s["rank"] > 0 for s in ans) / len(ans),
            "mrr": sum(1 / s["rank"] for s in ans if s["rank"]) / len(ans),
            "faithfulness": sum(s["faithful"] for s in ans) / len(ans),
            "refusal_score": sum(s["refused_ok"] for s in ref) / len(ref),
            "answerable": len(ans), "refusable": len(ref)}
