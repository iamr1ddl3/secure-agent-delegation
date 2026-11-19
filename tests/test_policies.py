"""Shape of the synthetic policy corpus: front matter, notice, sections, and references that resolve."""
import re
from pathlib import Path

import pytest
import yaml

DIR = Path(__file__).resolve().parents[1] / "policies"
DOCS = sorted(p for p in DIR.glob("*.md") if p.name != "README.md")
IDS = {p.stem for p in DOCS}
REF = re.compile(r"\b[a-z]+(?:-[a-z]+){1,5}\b")


def split(path: Path) -> tuple[dict, str]:
    _, front, body = path.read_text().split("---\n", 2)
    return yaml.safe_load(front), body


def test_corpus_size():
    assert len(DOCS) >= 25


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.stem)
def test_document(path):
    meta, body = split(path)
    assert set(meta) == {"id", "title", "owner", "version", "effective", "applies_to"}
    assert meta["id"] == path.stem and body.startswith(f"\n# {meta['title']}\n")
    assert "Synthetic document" in body and "novus" not in body.lower()
    assert body.count("\n## ") >= 2, "needs sections for heading-aware chunking"
    # References to other policies: "(some-policy-id)" and the "## Related" list must all resolve.
    refs = set(re.findall(r"\(([a-z]+(?:-[a-z]+)+)\)", body))
    related = body.split("## Related", 1)[1] if "## Related" in body else ""
    refs |= set(REF.findall(related))
    assert refs <= IDS, f"unknown policy ids: {refs - IDS}"
