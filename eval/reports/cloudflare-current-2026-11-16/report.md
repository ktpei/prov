# Current Cloudflare offline check — 2026-11-16

User-requested rerun of the existing nine-task development suite against the
current shared checkout. Observed HEAD after execution: `d770c15126223f77da4783dc5077b89046ec06dd`.
Other work was active in this checkout; this is not an isolated clean-commit run.
No runtime changes or paid model calls were made by this check.

Command: `uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 --benchmark eval/company_tasks.json --output /tmp/cloudflare-current-check.json`.
Saved output: [retrieval.json](retrieval.json).

Default BM25 v2, five hits per query and bounded 40-line reads reproduce the
recorded 6/8 retrieval baseline. Extraction anchors pass 8/8. Retrieval misses
packet-02 (actual GAAP/non-GAAP gross margins) and packet-09 (deck date and date
boundary). Packet-08 is an abstention question and excluded from positive evidence
ratios; abstention quality is not measured. Source hashes match the frozen suite.

These are fixed-query lexical evidence checks, not model-selected research,
financial answer accuracy, or proof of complete table semantics. The new arithmetic
ledger and typed-read authorization are not exercised by this legacy packet runner.
Full-agent testing remains separate; the recent paid comparison failures and
billing uncertainty are not resolved by this offline run.

Verification: `yarn lint` passed; `yarn test` passed 523 tests in the shared checkout.
No heldout content was opened and no policies were promoted.
