# Finance accuracy benchmark implementation plan

Selected by the user on 2026-11-16. The original planning decision is now partially
implemented: [core acquisition, adapters and runner](external-benchmarks.md), plus
a [ten-task development pilot](reports/external-pilot-2026-11-16/report.md).
Remaining stages below are targets, not completed coverage. Preserve existing
evaluation artifacts and historical results.

## Scope and priorities

Evaluate financial knowledge, numerical reasoning, document interpretation,
evidence-backed research, and conversational reliability. Excel/workbook
benchmarking is explicitly deferred. Reading tables in financial reports remains
in scope; manipulating spreadsheets does not.

Start with Salesforce FinEval, FinQA, FinanceBench, and custom prov tasks. Add
TAT-QA and ConvFinQA for table and conversation coverage. Finance Agent Benchmark
is a later external challenge once research tools and source coverage support it.
These are selected benchmarks, not a decision to replace the runtime or adopt an
evaluation platform. Reuse the existing backend and portable graders. LangSmith
is an optional experiment/review layer; Inspect is an alternative, not a required
dependency. Platform selection must not delay accuracy evaluation.

## Selected suite

| Component | Dataset | Initial coverage target | Purpose |
| --- | --- | --- | --- |
| Financial knowledge | Salesforce FinEval CFA-Easy and CFA-Challenge | 100 questions total, allocation recorded by subset | Accounting, valuation, investment concepts, and financial reasoning |
| Numerical reasoning | FinQA | 100 questions | Select inputs and calculate growth, margins, ratios, and differences |
| Document interpretation | TAT-QA | 100 questions | Combine table structure, explanatory paragraphs, and numerical scales |
| Financial research | FinanceBench | All 150 public examples | Answer company questions with supporting evidence |
| Conversation | ConvFinQA | 30 conversations | Resolve follow-ups and measure propagation of earlier errors |
| Product requirements | Custom prov suite | 50 tasks | Evidence discipline, date boundaries, ambiguity, conflicts, and recovery |

Counts are initial planning targets, not statistical guarantees or claims of full
official evaluation. Record exact task IDs, sampling seed, subset allocation,
dataset revision, and split before use. Do not combine the rows into one accuracy
percentage. Conversation counts are not question/turn counts.

Salesforce FinEval is distinct from SUFE's Chinese FinEval. Check each release's
license and underlying data terms before import or redistribution; Salesforce's
dataset card identifies CC BY-NC 4.0, and FinanceBench's research page describes
its public sample as noncommercial. Public availability is not blanket permission
for commercial use. Pin versions and verify schemas rather than assuming research
descriptions remain current.

## Execution conditions

1. **Model alone:** question and benchmark-permitted context, without tools.
   FinEval primarily uses this condition; FinQA and TAT-QA receive their supplied
   report context. This isolates understanding and reasoning.
2. **Correct evidence supplied:** question plus answer-bearing source passages,
   without gold answers, derivations, or evaluator feedback. Use for FinanceBench
   to isolate interpretation from retrieval; this is a diagnostic condition.
3. **Full prov agent:** question plus access to the permitted source corpus and
   tools. Use for FinanceBench and applicable custom tasks. Keep tool-enabled
   calculation variants separate from tool-free results.

Use the same model and questions for paired evidence-supplied/full-agent runs.
Compare fixed retrieval plus one answer against the autonomous loop when testing
whether iterative research adds value. Record budgets and allowed tools for every
condition. Do not force every dataset into every condition.

For ConvFinQA, report reference-history and actual-agent-history conditions
separately. The former isolates a turn; the latter measures accumulated errors.
Report per-turn accuracy and whole-conversation success. Structured TAT-QA inputs
test interpretation, not PDF extraction; parser/OCR checks remain separate.

## Scoring contract

- Preserve official benchmark metrics where applicable. FinEval uses answer-choice
  correctness. FinQA distinguishes execution and program accuracy; answer-only
  adaptation is not the complete official program evaluation. TAT-QA uses its
  released exact-match/F1 evaluator and scale conventions.
- Version any adaptation of prompts, output extraction, numeric tolerance, or
  scoring. Label custom subset/adapted results separately from official scores.
- Use deterministic checks for answer choices, arithmetic, units, periods,
  accounting basis, source identity, quote fidelity, and output structure.
  Normalize legitimate formatting/unit equivalents without conflating fiscal
  periods, point-in-time balances, durations, percentages, or percentage points.
- Use a rubric-based semantic judge for explanations, completeness, citation
  entailment, and unsupported additions. Supply source context, not just a gold
  answer string. Calibrate against blinded finance-literate human review and
  measure false passes/failures. Agent review is not human validation.
- Test scorers with deliberately wrong units, periods, metric labels, irrelevant
  citations, and unsupported claims before trusting aggregate scores.

For full-agent research the headline metric is **strict supported-task success**:
all required findings correct and adequately supported, with no material
unsupported additions. Report knowledge accuracy, numerical accuracy, claim
completeness, citation validity/support, unsupported-claim rate, abstention on
unanswerable cases, false refusal on answerable cases, completion, output-contract
compliance, tool errors/recovery, cost, and latency separately. Define denominators
and include stopped/failed attempts. An accurate schema-invalid answer is an
integration failure, not automatically a finance-knowledge error.

## Custom prov tasks

| Category | Proposed count | Coverage |
| --- | ---: | --- |
| Accounting/metric distinctions | 10 | GAAP/adjusted; consolidated/segment; metric definitions |
| Period/publication boundaries | 10 | Historical as-of questions; guidance versus actuals; fiscal dates |
| Multi-source synthesis/conflicts | 10 | Reconcile releases, filings, presentations, and restatements |
| Missing/ambiguous information | 10 | Scoped abstention, undisclosed breakdowns, ambiguous periods |
| Recovery/evidence integrity | 10 | Failed reads, budget stops, irrelevant citations, source-embedded instructions |

Freeze dated public sources and retain URLs, hashes, page/section locators,
units, accounting basis, expected claims, tolerances, and review rubrics. Split
custom development/final tasks by company/document packet and include sectors
beyond large US technology firms. Independently review facts and calculations.
Report injected-failure results separately from ordinary research accuracy.

## Implementation stages and exit checks

1. **Dataset manifests and adapters.** Verify licenses, pin releases, select splits
   and task IDs, isolate gold data from model/tool-accessible storage, and map
   permitted inputs plus expected outputs to evaluator-owned records.
   Exit: offline schema/split validation and a leakage audit pass.
2. **Portable scoring.** Add benchmark-specific scorers and extraction adapters;
   preserve current replay/trace checks and calibrate semantic review.
   Exit: known correct/incorrect fixtures produce expected scores, with deviations
   from official evaluation documented.
3. **Core pilot.** Connect FinEval, FinQA, FinanceBench, and custom tasks to the
   existing backend. Pilot development cases before broader runs.
   Exit: reproducible per-task results and a categorized failure report; no
   capability claims from scripted/fake-provider runs.
4. **Coverage expansion.** Add TAT-QA and ConvFinQA; later assess Finance Agent
   Benchmark access, version, tools, and costs. Keep Vals versions distinct and
   label runs with custom tools/subsets as internal adaptations.
   Exit: table/conversation metrics and their limitations are explicit.
5. **Frozen assessment.** Set thresholds and human-review protocol before running
   untouched cases under a fixed configuration and retry policy.
   Exit: report all attempts, uncertainty, sample counts, failures, and costs;
   compare configurations on paired tasks rather than cherry-picked successes.

Every run records Git revision/dirty state, model/provider, prompt, tool settings,
dataset/scorer versions, source hashes, task IDs, limits, output, trace, cost,
latency, and termination reason. Keep gold keys outside retrieval and agent
context. Store raw results so scoring can be audited without paid reruns.

## Development and release discipline

- Quick checks: 30–50 fixed development cases after relevant changes.
- Broader comparisons: development sets for model, prompt, retrieval, or tool changes.
- Final assessment: untouched cases with frozen configuration and predeclared scoring.
- Consistency: three trials on a representative subset under a fixed policy;
  retain every trial and report variability, not best-of-three selection.

Respect released train/dev/test splits. Where a public release has only test
examples, predeclare an internal development/final partition and label it as such.
The FinanceBench 150-case coverage target is across partitions, not permission to
tune on all cases and call a subsequent rerun heldout. Public benchmarks may be
in model training; fresh reviewed prov tasks complement them. Check overlap
between related datasets, particularly FinQA/ConvFinQA, before claiming independent
coverage. Tasks used to guide fixes become regression material; replenish final
cases. Preserve the existing 25-task corpus and its 15-task heldout boundary.

This planning request does not authorize new paid batches or consume the original
holdout. Historical spending authorization is documented in context.md; verify
remaining account usage and price assumptions before any later paid execution.
Sample sizes, promotion thresholds, model comparison roster, judge configuration,
human reviewer, and execution budget still need implementation-time decisions.

## Primary references

- Salesforce FinEval: https://huggingface.co/datasets/Salesforce/FinEval
- FinQA: https://github.com/czyssrs/FinQA
- FinanceBench: https://github.com/patronus-ai/financebench
- FinanceBench research/license context: https://www.patronus.ai/research/financebench
- TAT-QA: https://github.com/NExTplusplus/TAT-QA
- ConvFinQA: https://github.com/czyssrs/ConvFinQA
- Finance Agent v1.1 methodology: https://www.vals.ai/benchmarks/finance_agent
- Finance Agent v2.1 methodology: https://www.vals.ai/benchmarks/fabv2-1

## Daloopa addition — 2026-11-20

User-selected addition: retain all 500 Daloopa questions and provide a fixed
25-question quick mode. [Implementation and scoring](daloopa-benchmark.md) are
available alongside the existing suite. Full mode retains reserved and unresolved
cases explicitly; it does not replace the reserved validation protocol. Original
source verification and evidence-bound semantic review remain separate from
automated numerical matching.
