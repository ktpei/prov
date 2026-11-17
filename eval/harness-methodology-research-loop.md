# Harness methodology research loop

Started 2026-11-16. Research chat: `01a1e698-b708-7490-a303-2fc6ec1506f7`.
Implementation destination: **Research finance agent harnesses**, chat
`01a1e620-dc5f-7d40-911b-27122e523249`. The user authorized continuous online
comparison and actionable findings sent to that implementation loop. An hourly
follow-up is active (`research-harness-methods-for-prov`); this does not authorize
paid experiments. The implementation loop owns runtime changes and integration.

## Research contract

Compare mechanisms, not framework popularity. Each finding needs primary sources,
access date, local fit, benefit hypothesis, integration cost, failure modes, a
decision, and a falsifiable check. Distinguish source claims, inspected code,
proposed experiments, and measured results. Preserve negative findings. Recheck
implementation state before recommending already-completed work.

The user's project-fit gate additionally requires demonstrated local need, the
smallest sufficient integration, build/maintenance effort, dependencies/deployment
burden, latency/cost, and comparison with no change and a simpler local solution.
Unknown production workload, staffing and user counts stay unknown. Preserve
financial correctness while simplifying; revisit deferred mechanisms only when
observable workload or failure evidence warrants them.

Consult the validation reservation and exposure audit before browsing. Preserve
all six selected issuers and their dispositions, including Amazon/Microsoft prior
issuer exposure. Audit metadata using both source manifests and cross-suite
aliases; never open held-out content to resolve identities. Log incidental
examples. No reserved issuer is available for development tuning.

## Cycle 1 — evaluation adapter boundary

Primary source, accessed 2026-11-16:
[Inspect Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html).
The documented bridge supports existing agents but routes their model calls
through Inspect's model provider. It is not passive trace collection.

**Decision: defer adoption; prototype parity after H1 if external evaluation
orchestration is needed.** Benefit hypothesis: reuse evaluation infrastructure
while keeping prov's agent. Cost: adapter maintenance and a second configuration
surface. Risk: changing provider routing, generation settings, retries, or tools
changes the evaluated system.

Acceptance proposal: with an offline deterministic provider, compare direct and
bridged runs for projected messages, tool schemas, effective generation settings,
attempt counts, cost reservations, stops, and outputs. Account for deliberate
differences explicitly. Do not claim application receipts attest provider wire
bytes. Delivered to the implementation chat; no adapter installed or tested.

## Cycle 2 — recovery boundaries versus finance reference chaining

Sources accessed 2026-11-16; live documentation, not pinned release evidence:

- [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance):
  a retry reruns a node; external side effects are outside checkpoint atomicity.
  A durable key helps only when the external service honors deduplication.
- [Temporal activities](https://docs.temporal.io/activity-definition): completed
  activities can be replayed from history, but failure to report completion can
  cause re-execution. Smaller activities reduce repeated work, with more history.
- [Temporal workflow execution](https://docs.temporal.io/workflow-execution):
  recovery reconstructs workflow progress against event history.
- [FinanceHarness README](https://github.com/Yijia-Xiao/FinanceHarness): describes
  tool-output reference chaining and on-demand tool/skill loading. These are
  documented design claims, not a local reproduction or a recovery guarantee.

| Method | Fit and benefit hypothesis | Cost / limitation | Decision |
| --- | --- | --- | --- |
| LangGraph checkpointing plus prov's attempt marker | Preserve existing graph and prevent blind replay of uncertain paid calls | Requires application-level reconciliation; checkpoints alone cannot establish provider outcome | Keep current protection |
| Temporal workflow/activity separation | Potentially useful for long-running distributed ingestion or research jobs | Service/worker operations and migration; still needs external deduplication or reconciliation | Defer dependency; borrow failure-boundary tests |
| FinanceHarness reference chaining | Reduces retyping between evidence tools and calculations; fits H2/H3 | Reference identity does not prove correct financial scope or safe paid-call retry | Prototype bounded references under existing spec |

Local inspection: base HEAD `179d176`, with active uncommitted H1 edits owned by
the implementation chat. `provenance/graph.py` commits an attempt marker before
external work and rejects resume when that marker is ahead of the checkpoint.
`provenance/transport.py` does not retry network failures automatically;
`provenance/langchain_model.py` sets `max_retries=0`. `tests/test_graph.py` has
marker-tampering and process-death tests. The inspected process-death test exits
inside the model before simulating an externally completed response. These
observations are a moving-checkout review, not clean-release acceptance.

**Actionable delta: test the acknowledgement gap, rather than add generic retry.**
Use a synthetic provider with a separately persisted accepted-call counter. Kill
the worker after that counter increments but before the graph commits completion.
Resume must issue zero additional provider calls and retain the uncertain attempt
for reconciliation. Also test death after durable completion: reopening a finished
run must return its stored result without another call. Existing pause/resume and
completed-result tests remain necessary. No live provider or held-out issuer is
needed. These tests are proposed, not run by this research cycle.

Reference-chained computations should distinguish immutable evidence/result IDs
from provider-operation IDs. Replaying deterministic arithmetic can be safe even
when retrying the upstream paid fetch is not. This is our integration inference,
not a guarantee established by the FinanceHarness README.

## Exposure and handoff status

No reserved task, gold answer, or source filing was opened. FinanceHarness's
README displayed generic NVIDIA valuation and Apple research/P-E prompts, without
worked financial answers in the inspected excerpt; record this visibility for
future exposure audits. No cohort or frozen disposition changed.

Cycle 1 was sent to implementation. Cycle 2 and this document are handed to the
implementation owner for review and a focused documentation commit, serializing
Git mutations with its active H1 work. No runtime files were changed here.

Cycle 3: [reference transport and financial acceptance](harness-reference-contract-research-2026-11-16.md)
pins the upstream resolver/dispatcher/calculator, reinforces H2's Decimal contract,
and proposes explicit preservation of resource-stop exceptions in H3. Its isolated
evaluator checks are not end-to-end benchmark results.

## Reviewed research backlog

- [Context boundaries](harness-context-boundary-research-2026-11-16.md): H4 may
  compare deterministic candidate filtering plus complete support reads; do not
  replace claim support with private aggregation or summaries.
- [Tool catalog fit](tool-catalog-fit-2026-11-16.md): two current schemas total
  711 compact JSON characters/bytes, not tokens. Keep fixed tools; require
  measured burden before dynamic discovery.
- [Evaluation fit](harness-evaluation-fit-2026-11-16.md): retain local evaluation.
  A future external adapter must preserve failures/unscored cases, scoring
  coverage and the declared strict-success denominator.
- [Narrow workflows](finance-workflow-fit-2026-11-16.md): after H2/H3, isolate a
  short two-period instruction comparison from retention changes at equal budgets.

These are reviewed design inputs, not implemented features or benchmark gains.
H2 evidence admission and calculation replay take precedence; the acknowledgement
gap test remains a discrete offline recovery check. Framework migration stays
deferred.
