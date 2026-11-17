# Tool discovery: current project fit

Research cycle 5, 2026-11-16. Decision: keep the fixed tool catalog. Deferred
loading remains a future option, not a current implementation recommendation.

## Measured local scale

At HEAD `82aa34b`, importing `TOOL_SCHEMAS` and serializing with
`json.dumps(TOOL_SCHEMAS, ensure_ascii=False, separators=(',', ':'))` produces
711 characters / UTF-8 bytes for two tools: `search` and `read_source`.
The instruction string contains 2,293 characters. `Limits()` defaults are eight
model calls, ten tool calls and 90 seconds. These are code defaults, not observed
traffic or user-selected limits. Character counts are not tokenizer counts,
provider request size, or billed cost. No model calls or source reads were made.

## Primary-source comparison

[Anthropic tool search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool),
accessed 2026-11-16, documents discovering definitions from large catalogs.
Deferred definitions are still sent to the API; they are selectively introduced
to model context. Thus request transfer size and model-context savings are
different quantities. Its large-catalog examples do not establish a break-even
point for prov.

[FinanceHarness load_tool](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/tools/core/load_tool.py)
at the pinned revision loads requested names into session state, returns schemas
inline, and makes them available in subsequent tool definitions. This provides a
provider-independent pattern but introduces discovery state and an extra step.
The separately inspected registry also retains textual catalog descriptions.

## Cost and decision

For prov's present catalog, an on-demand loader would add a schema, routing
instructions, loaded-tool state, checkpoint/replay handling, and potentially
additional model/tool turns to avoid initially showing two small definitions.
There is no measured local benefit to justify those costs. The simplest viable
choice is no change. Even growth toward the sponsor's five-to-seven-tool target
does not itself establish a need for dynamic discovery.

If optional capabilities grow, first compare explicit static tool profiles chosen
by the caller at run start. Profiles can avoid irrelevant tools without requiring
the model to discover the catalog, but must not hide a capability the task needs
or choose tools using benchmark answers. This is a comparison candidate, not a
new feature request.

Reconsider on-demand loading when real request measurements show material schema
overhead or observed tool-selection errors in a broader catalog. Compare fixed,
static-profile and dynamic conditions using the same tasks, model and budgets.
Count discovery failures, schema bytes, actual token usage, extra calls, latency,
completion and supported-answer correctness. Include loading on resume and tool
identity checks. Set a promotion margin from the real workload before seeing
outcomes; do not borrow a vendor's catalog-size threshold as a local rule.

## Integrity and handoff

Reservation and exposure-audit metadata were checked before source research. No
held-out content, issuer examples or financial documents were opened. No frozen
disposition changed. This is a measured catalog inventory and design comparison,
not a performance experiment. No runtime changes or dependency additions.

Handed to the implementation owner for a focused documentation commit and a
link from the research ledger. This applies the user's explicit requirement that
recommendations fit the use and size of this project.
