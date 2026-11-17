# Context savings versus evidence visibility

Research cycle 4, 2026-11-16. Status: proposed experiment, not measured improvement.
See [research ledger](harness-methodology-research-loop.md) and
[implementation specification](../harness-improvement-spec.md).

## Primary evidence

[Anthropic programmatic tool calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling),
accessed 2026-11-16, documents executing tool calls in code and processing their
results before returning output to the model. Intermediate results do not enter
model context. This supports batching and filtering, but documentation of the
mechanism does not establish benefit on prov's financial tasks.

[Anthropic context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents),
published 2025-09-29 and accessed 2026-11-16, describes lightweight references,
on-demand retrieval, compaction, and persistent notes. It acknowledges exploration
latency and information loss from aggressive compaction. Its general guidance
does not define a financial evidence acceptance standard.

[FinanceHarness chaining](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/runtime/chaining.py)
uses structured results outside the model's text channel. The
[prior pinned-code analysis](harness-reference-contract-research-2026-11-16.md)
establishes the transport mechanism and its distinction from financial acceptance.

## Local boundary

HEAD `3dcd09b` now contains opt-in H1 receipts; shared documentation was still
being updated when inspected. The implementation chat reports full-suite success;
this research cycle did not independently rerun or accept that suite.
`provenance/context.py` preserves the latest search/read, retains older results
when they fit, and leaves omission notices without altering canonical history.

The specification's sections 4.5 and 5 require complete support groups in the
final synthesis request. A privately computed result or an agent summary cannot
substitute for that evidence. Therefore blindly adopting result-only programmatic
aggregation would change prov's evaluation contract, even if it saves tokens.
This is a local integration inference, not a criticism of the external mechanism.

## Comparison and recommendation

| Approach | Possible benefit | Main cost or failure | Decision |
| --- | --- | --- | --- |
| Current complete-result projection | Simple, replayable baseline | Recency may omit needed evidence | Retain baseline |
| Programmatic prefiltering for discovery | Fewer irrelevant candidates reach the model | Bad filters can hide relevant facts or qualifying notes | Prototype only with reproducible candidate selection |
| Reference-linked calculations | Avoid transcription and large intermediate payloads | Result alone conceals wrong-period or wrong-scope operands | Use H2/H3 evidence and calculation contracts |
| Summary-only final support | Small final request | Removes information needed to inspect financial meaning | Reject under current v2 contract |
| Complete, bounded support groups | Remove irrelevant material while retaining operands and qualifiers | Extra selection/retrieval work; groups may exceed the budget | H4 candidate, not a default promotion |

Do not introduce arbitrary code execution or change providers merely to test the
filtering idea. A deterministic local candidate filter can isolate its value.
The accounting unit must include filter work and rereads, not just the smaller
final model request. Tool-result characters are not interchangeable with billed
tokens; report both with their actual definitions.

## Falsifiable experiment proposal

First freeze synthetic cases containing a financial table, headers, units, periods,
and qualifying notes. Include identical values under different scopes, a footnote
that changes the valid denominator, and a filter returning zero rows despite a
relevant record elsewhere in the declared source. No real issuer is needed.

Compare current projection with deterministic candidate filtering followed by
complete support-group reads. Keep model, corpus, limits and requested outputs
fixed. Both conditions must use the same final support acceptance rule. A
summary-only condition may be a negative control, but cannot earn a successful
v2 score merely by producing the correct number.

Predeclare checks: final support-group completeness, scope/period/operand
correctness, false claims of non-disclosure after empty filters, completed-answer
rate, all attempted calls, latency and total charged/reserved cost. Establish
offline integrity first; any paid comparison remains subject to the existing
budget reconciliation and frozen development protocol. A token reduction with
more missing qualifiers or unsupported conclusions is not a promotion.

For derived claims, require final visibility of the selected operands and their
qualifiers plus the calculation record. Do not infer that every irrelevant row
of an original document must be shown. If a future large aggregation requires
different visibility semantics, freeze a separate policy and evaluate it rather
than silently treating a summary as a complete support group.

## Exposure and handoff

Reservation and exposure-audit metadata were rechecked. No held-out content or
reserved issuer examples were opened. The primary pages displayed generic
employee-expense, regional-sales and software examples; these were not finance
benchmark cases. No cohort dispositions changed.

Handed to the implementation owner for review, a ledger link and a focused
documentation commit. This is an H4 experiment design input; it need not interrupt
H1 acceptance or H2 implementation. No runtime file changed and no experiment ran.
