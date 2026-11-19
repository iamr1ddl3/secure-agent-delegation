"""Copy the index of P1's human-reviewed golden items (id, role, question, expected status) into P2.

Usage: python scripts/vendor_p1_golden.py <path to a secure-sql-agent checkout at the pinned tag>
No database and no credentials: this reads P1's public YAML only. Truth rows come later (tracker task 21).
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

p1 = Path(sys.argv[1])
tag = subprocess.run(["git", "-C", p1, "describe", "--tags", "--exact-match"], check=False, capture_output=True,
                     text=True).stdout.strip()
items = {}
for f in sorted((p1 / "evals/golden").glob("*.yaml")):
    for it in yaml.safe_load(f.read_text()):
        assert it.get("reviewed") is True, f"{it['id']} is not human-reviewed in P1"
        items[it["id"]] = {"asked_by": it["asked_by"], "question": it["question"], "expect": it["expect"]}
out = Path(__file__).resolve().parents[1] / "evals/p1_golden_index.json"
out.write_text(json.dumps({"source": f"iamr1ddl3/secure-sql-agent {tag or 'untagged checkout'}", "items": items},
                          indent=1, ensure_ascii=False) + "\n")
print(f"{len(items)} items from {tag or 'untagged checkout'} -> {out.name}")
