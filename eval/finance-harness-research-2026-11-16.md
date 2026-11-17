# Finance agent harness research and integration plan

Research date: 2026-11-16. Scope: company research, evidence-backed financial
analysis, and evaluation. Recommendations below are proposals, not implemented
features or measured improvements. No new inference or benchmark run was made.

Keep the current LangGraph runtime. Prioritize evidence-linked computation,
model-visible evidence receipts, and prospective end-to-end evaluation before
adding autonomous analyst teams or valuation products.

## External references

The most directly relevant architectural reference is
[FinanceHarness](https://github.com/Yijia-Xiao/FinanceHarness), with
[a July 2026 paper revised in August](https://arxiv.org/abs/2607.27853).
Its tool-output references, deferred schemas, and workflow skills are useful
design patterns. The [Google Research distribution](https://github.com/google-research/google-research/blob/master/finance_harness/README.md)
declares CC BY-NC 4.0; do not assume commercial copying is permitted or that
different repository distributions have identical terms.

[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) is a reference for
separating financial computation from narration. Its framework generations and
product surface are broader than this project's current milestone.
[Dexter's scratchpad implementation](https://github.com/virattt/dexter/blob/main/src/agent/scratchpad.ts)
illustrates durable raw results alongside a separately managed model context.
[Anthropic's financial-services repository](https://github.com/anthropics/financial-services)
offers workflow and handoff templates. These are potential design inputs, not
dependencies selected by this research.

Evaluation references:

- [Vals Finance Agent v2.1](https://www.vals.ai/benchmarks/fabv2-1): critical-check
  gating and separate partial-credit/all-pass reporting.
- [FinanceGym](https://financegym.github.io/): point-in-time retrieval and separate
  evidence-at-cutoff and subsequent-outcome criteria.
- [FORCE-Bench](https://arxiv.org/abs/2607.19409): multiple quality dimensions
  under common tool access and latency constraints.
- [FinToolBench](https://github.com/Double-wk/FinToolBench): tool execution and
  temporal/intent/domain mismatches measured separately. Its questions derive in
  part from FinanceBench, so cross-suite overlap must be audited before import.
- [FinMCP-Bench](https://arxiv.org/abs/2603.24943): single-tool, multi-tool, and
  multi-turn tool-use assessment.
- [FinSearchComp](https://arxiv.org/abs/2509.13160): separate live fetching,
  historical lookup, and complex investigation.
- [FinNextAssist](https://arxiv.org/abs/2610.03174): October 2026 proposal with
  specialized table and heterogeneous-data agents. Treat as a research candidate;
  implementation reproducibility and local benefit are not established here.

## Integration sequence and acceptance criteria

1. **Record what the model actually receives.** `project_messages` in
   `provenance/context.py` keeps the latest search/read and fits older reads by
   recency. `OpenRouterModel._step` reports character totals, while the graph logs
   canonical messages before projection. Add a versioned receipt of retained and
   omitted call IDs and a canonical request digest. Bind prompt, schema, and
   projection identities to checkpoint compatibility. Verify exact reconstruction
   and rejection of incompatible resumes. Never label a digest as provider-side
   attestation.
2. **Introduce a small calculation contract.** Default `TOOL_SCHEMAS` exposes
   search/read only. `validate_answer` has no derivation checks. Add bounded
   decimal arithmetic with immutable operand references, explicit units, period,
   entity, scope, formula, and rounding. Start with differences, ratios, growth,
   and sums. Verify wrong-unit, wrong-period, percentage-versus-percentage-point,
   zero-denominator, and unresolved-scope cases. Recomputable arithmetic does not
   prove that the selected financial operands are appropriate.
3. **Connect evidence types coherently.** `TableSources` and `FactReader` remain
   experimental and separate from the default loop. Before exposing them, agree
   on discovery, read authorization, context projection, citation/claim schemas,
   checkpoint identity, and replay grading. Preserve reported facts separately
   from assumptions and derived outputs. Exact-ID delivery is not autonomous
   question-to-fact discovery.
4. **Test evidence retention by active requirement.** Preserve the operand,
   header, period, scale, and footnote groups needed for pending claims. Compare
   against the existing projection with equal budgets and frozen inputs. Keep
   both replayable; historical negative retrieval/retention experiments remain
   negative results. Promote only on fresh preregistered evaluation, including
   semantic answer checks and cost/completion metrics.
5. **Add narrow workflow instructions.** First candidates are statement
   comparison, ratio calculation, and earnings reconciliation. Each should
   declare required inputs, permitted tools, output claims, and abstention rules.
   Add deferred schema loading only when tool-catalog size creates a measured
   cost. Maintain the single model-directed agent as the baseline.
6. **Freeze a full-agent experiment.** `run_prepared` currently rejects the
   `full_agent` condition. First complete source acceptance and an independent
   protocol. Measure discovery, delivery, model-visible retention, financial
   operand selection, computation, final support, and completion separately.
   Compare one change at a time with fixed model, sources, and budget; include
   zero-credit failures and repeated-run variability. Critical checks must be
   chosen before seeing outputs, and judge agreement needs expert calibration.

The existing `source_availability.availability` and `FactReader.read(as_of=...)`
are useful temporal building blocks. Extend exact-artifact availability to each
new connector; a current API response or a historical period label is not proof
that the returned data was available at the requested cutoff.

Do not replace current deterministic spending controls with soft repetition
warnings. Add progress feedback only as an additional aid. Preserve final-answer
time and cost headroom, not merely a remaining model turn. Keep workbook writes,
trading, large connector catalogs, and multi-agent debate outside this milestone.

## Research exposure addendum

Before research, reservation.json, exposure-audit.json, and the two source
manifests were consulted. No local reserved question, gold answer, or original
filing was opened for this research. All six selections and their frozen
dispositions remain unchanged. Amazon and Microsoft retain known prior issuer
exposure; none of these issuers is authorized for development tuning.

External browsing nevertheless displayed incidental examples. Record these as
research exposure for future cohort audits, not as a modification of frozen
metadata or as selected development cases:

- A `find` for “skill” in the FinanceHarness paper unexpectedly returned an
  appendix excerpt about a Microsoft FY2025 valuation workflow and tool-produced
  fundamentals. This is additional Microsoft issuer exposure. The figures were
  not used in recommendations or tests. No reserved 2016 filing was opened.
- Vals v2.1 displayed a Centene FY2025/FY2020 worked answer and rubric outcome.
  Treat those issuer-period contexts as exposed in future selection.
- The FinanceGym landing page displayed an Air France-KLM/SAS/TAP question and
  an Apple Q1 2025 rubric excerpt. Dexter documentation also displayed an Apple
  historical revenue example. These are research exposures, not validated facts.
- Broad search returned an unattributed numerical filing example from a
  secondary benchmark catalogue. No issuer identity was established; do not use
  that example or claim comprehensive cross-suite non-exposure from this audit.

Future research should retrieve bounded methodology sections and avoid global
paper searches that can surface worked examples. This addendum supplements the
existing exposure registry and manifests; it does not claim an exhaustive audit.
