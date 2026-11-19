# Policy corpus (synthetic)

25 internal staff policies for the bank in Project 1's data (10 branches, 7 demo roles). They are what the policy
agent searches and cites. **Every document is invented** for this project: the bank, its rules, limits and amounts
are not a real bank's, and nothing here is legal or regulatory advice. Written for decision D3 (internal staff
policies, not customer-facing product pages; no reuse of the Novus Bank RAG corpus).

Each file: YAML front matter (`id` = file name, `title`, `owner`, `version`, `effective`, `applies_to`), the
synthetic-data notice, then `##` sections (the chunker splits on headings). Policies refer to each other by id.

Consistency with P1: the roles and access in `data-access-and-roles` and the bulk-export rule in
`pii-masking-and-bulk-export` (more than 20 rows of raw identifiers needs a second person who never sees the data)
describe what P1's database and review queue actually enforce. Overdue (1-90 days past due) and NPA (over 90)
match P1's ontology.

The compound tasks in `evals/compound/` cite these pages by id; `tests/test_policies.py` checks the corpus shape and
that every cited id exists. Poisoned pages for the stage 3 injection tests will live apart from this folder and be
flagged, so the clean corpus stays clean.
