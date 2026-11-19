"""Policy mini-eval: every answerable item is provably answerable from the cited section of the corpus."""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ITEMS = yaml.safe_load((ROOT / "evals/policy/questions.yaml").read_text())
PAGES = {p.stem: p.read_text() for p in (ROOT / "policies").glob("*.md") if p.name != "README.md"}


def section(page: str, heading: str) -> str:
    """Text of one ## section, without markdown bold and with whitespace collapsed."""
    parts = re.split(r"^## ", PAGES[page], flags=re.MULTILINE)
    body = next((p for p in parts[1:] if p.split("\n", 1)[0].strip() == heading), None)
    assert body is not None, f"{page} has no section '{heading}'"
    return " ".join(body.replace("**", "").split())


def test_ids_and_mix():
    ids = [i["id"] for i in ITEMS]
    assert len(ids) == len(set(ids)) == 20
    assert sum(i["expect"] == "refused" for i in ITEMS) >= 3


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i["id"])
def test_item(item):
    assert set(item) <= {"id", "question", "cites", "section", "must_include", "expect", "notes"}
    assert item["expect"] in ("answered", "refused") and item["question"].strip()
    if item["expect"] == "refused":
        assert item["cites"] == [] and "section" not in item and "must_include" not in item
        return
    assert item["cites"] and set(item["cites"]) <= set(PAGES)
    text = section(item["cites"][0], item["section"])
    for fact in item["must_include"]:
        assert fact in text, f"{item['id']}: '{fact}' not in {item['cites'][0]} / {item['section']}"
