# Project scope

Informal, unpaid, part-time proof of concept for ProvenanceXL. The selected brief
is a single model-directed finance agent with a small tool set and an honest
evaluation. Current authorization covers roadmap steps 1 and 2 only.

## Step 1: evaluation foundation

- Fix three useful task types: financial extraction, management guidance, and
  cross-company comparison; include evidence-limited abstention cases.
- Use five public companies, explicitly dated documents, and original source
  URLs. Keep local excerpts small and distinguish them from full filings.
- Create 25 questions, each with an expected answer, source locators, units,
  periods, tolerances, and rubric: 10 dev and 15 heldout.
- Validate source hashes, split counts, references, and locator bounds.
- Keep expected answers out of model context and retrieval.

These artifacts are implemented. The initial holdout shares companies and
documents with development tasks, so it is not an independent generalization
benchmark. Numerical gold facts were researched against official releases;
derived answers were checked arithmetically. No model-quality result is claimed.

## Step 2: minimal agent loop

- One model selects tools, sees their results/errors, and chooses its next step.
- Start with `search` and `read_source`; no financial workflow routing.
- Enforce model/tool call limits, a wall-clock deadline, bounded HTTP, and
  conservative cost reservations; record stops and failures explicitly.
- Return structured claims with evidence locators and matching quotes.
- Produce complete model/tool event logs plus cost and elapsed time.
- Verify the loop offline and provide an opt-in live OpenAI adapter.

Implemented with a labeled offline replay and fake-HTTP contract tests. Live
acceptance remains deferred at the user's request. Quote presence proves
retrievability, not that the evidence logically supports a claim.

## Explicitly later

Full filing/XBRL extraction, financial-calculation tools, market data, workbook
reading/writing and approval UI, full benchmark execution, model/prompt tuning,
deployment, a production UI, and a production financial research service.

## Decisions

- Python 3.11+ standard-library CLI; no framework required for two tools.
- OpenAI Responses API for future inference; no paid model chosen implicitly.
- Frozen-corpus retrieval works without Exa. Optional Exa search/contents is
  implemented but not live-verified.
- Runtime has no model-controlled file writes. Human-supplied `--log-dir`
  explicitly enables deterministic diagnostic logging.
- One model loop at runtime. Development research/review delegation is separate
  from the product architecture.
- No remote repository was configured in this initially empty workspace.
