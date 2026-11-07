# Finance evaluation corpus v1

This development benchmark contains 25 grounded questions: 10 development tasks and 15 heldout tasks, covering Apple, Microsoft, NVIDIA, Amazon, and Meta. There are 13 extraction, 5 management-guidance, 4 cross-company comparison, and 3 explicitly unanswerable tasks. It tests answers within a fixed, small public-document corpus, not investment recommendations.

## Source and date boundaries

`tasks.json` has an information cutoff (`as_of`) of November 20, 2024, the newest release date. The official documents were inspected on October 24, 2026. Historical reporting periods are deliberately explicit: Apple's FY2024 Q4 ends September 28, Microsoft's FY2025 Q1 and Amazon/Meta's Q3 2024 end September 30, and NVIDIA's FY2025 Q3 ends October 27. Forecast periods can extend beyond the information cutoff. They must remain forecasts, not be silently replaced with subsequently reported actuals.

The source manifest at `../data/corpus/sources.json` records the original official URL, publication date, retrieval date, and SHA256 of each local UTF-8 text file. Each file is a curated factual extract: selected financial facts with normalized labels, units, dates, and original section names. It is not a verbatim or complete copy of the release. Apple uses page 1 of the release's financial-statement PDF; the other four use the named earnings-release sections. Hashes identify these local extracts, not the full upstream documents or proof of their authenticity. Upstream pages may change.

Locations such as `L4-L6` refer to inclusive, one-based lines of the local text file. Files have no embedded line-number prefixes. The runtime adds line numbers. Source headings identify the original section; the local line numbers do not purport to be original webpage line numbers. A quote must reproduce text within the cited local span. Never cite an evaluation answer key as evidence.

## Split discipline

Use only the 10 `dev` tasks when selecting prompts, retrieval settings, models, or tool budgets. The 15 `heldout` tasks are reserved for a later, explicitly authorized final evaluation. No heldout model evaluation was run during corpus creation. Static validation of task counts, references, expected arithmetic, and source hashes is data QA, not an agent evaluation.

The split is by question, not by company or document: both splits intentionally share sources and some underlying facts. The answer keys are visible in this repository and were written in the same development workflow. This is a development holdout, not a secret, independently authored or contamination-resistant benchmark. Do not report it as evidence of broad generalization. Record any inspection or tuning against heldout outcomes; a tuned-on holdout needs replacement before a credible final assessment.

## Answer contract and rubric

Each task names its allowed `source_ids`. A supported answer needs the requested claims, correct accounting basis, measurement period, units, and citations. The expected claim has a stable `key`, numeric `value`, `unit`, `period`, absolute numeric `tolerance`, source/locator, and optional `derivation`. `supporting_sources` lists additional required evidence for a derived comparison. A guidance range is represented by separate lower and upper claims; a stated guidance tolerance is distinct from the evaluator's numeric tolerance.

1. **Numeric correctness.** Match the expected value within the specified absolute tolerance after interpreting the requested unit. Most direct table facts have zero tolerance; formatting such as trailing decimal zeros is immaterial. Accept an equivalent unit conversion only if the evaluator normalizes it explicitly and the answer preserves the requested precision. Do not equate USD millions with billions, percent with percentage points, or basis points with percent. Report multi-claim completeness rather than hiding an incorrect claim behind an average.
2. **Basis and period.** Match GAAP/non-GAAP, segment/consolidated, quarter/year, actual/forecast, and reported/constant-currency distinctions. Correct numbers under the wrong labels fail. Fiscal labels differ across companies even when calendar quarter ends coincide. The Apple/Microsoft comparison has nearby, unequal period ends and is an arithmetic comparison, not a claim of identical reporting windows.
3. **Derivations.** Show the arithmetic and cite every input. `derivation` is explanatory data, not executable code for an agent. Compute from the specified exact table values and round only where the question requests it. A derived answer is not expected to appear verbatim in a source. All required source spans must jointly support the calculation.
4. **Citation validity and entailment.** A valid source ID, an in-bounds line span, and a matching quote are necessary but insufficient. Check that the cited passage actually supports the claimed metric, basis, period, and number. A citation to a nearby unrelated number fails. Equivalent local spans are acceptable if they include the value and enough header context; an exact match to the gold locator is not required.
5. **Abstention.** For unanswerable tasks, return `answerable: false`, no factual answer claims, and a brief explanation of what is missing from the supplied excerpt. Do not guess or substitute a consolidated/segment amount for an undisclosed product amount. Absence is scoped to the supplied excerpt, never a claim that the company has not disclosed the fact anywhere. For answerable tasks, unsupported refusal is a failure.
6. **Unsupported additions.** Review the prose as well as structured claims. Correct requested values do not excuse additional ungrounded causal explanations, forecasts, or facts. External knowledge is outside the benchmark evidence boundary.

Report numeric/period correctness, citation validity, citation entailment, abstention, and overall task success separately. Overall strict success requires every requested claim and all necessary evidence, with no material unsupported addition. Automated structural or string checks cannot establish semantic entailment; a human reviewer must inspect the answer, quotes, source context, and task-specific `rubric` before treating a score as trustworthy. No numeric promotion threshold is established by these artifacts alone.

## Verified status and limitations

The expected factual values were checked against the five official documents; derived values use explicit arithmetic. Static checks verify 25 unique task IDs, the 10/15 split, five referenced companies, three abstentions, hashes, line ranges, direct numeric presence in cited spans, and independently recomputed derived values. This records corpus QA only. It does not claim a live agent run, heldout score, or human-reviewed model performance.

The corpus is tiny, manually curated, concentrated in large US technology companies, English-only, and mostly simple earnings tables. Excerpts are short and selected around answer-bearing facts, so retrieval is easier than searching full filings. It omits OCR, long-document navigation, table extraction noise, source conflict resolution, restatements, external browsing, private data, and realistic financial due diligence. Model pretraining may already contain these public facts. A high result here would justify broader evaluation, not deployment or financial reliance.

## Full-document company packet benchmark

`company_tasks.json` is a separate, entirely development-only benchmark over the
full Cloudflare packet in `../data/cloudflare-2024-q3`. It preserves the original
25-task excerpt benchmark and its holdout boundary. Its nine tasks cover direct
numerical extraction, GAAP/non-GAAP distinctions, guidance across two documents,
qualitative explanations, filing/call synthesis, free-cash-flow definitions,
packet-scoped abstention, and the date boundary between a May investor deck and
November earnings results. All four extracted-source hashes are pinned. Changing
extraction requires reviewing the anchors and versioning the benchmark.

Run the fixed-query diagnostic from the repository root:

```sh
uv run python -m provenance.evaluation \
  --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json \
  --output eval/reports/retrieval-baseline.json
```

For each task, fixed queries use concepts from the question; they never include
expected numerical answers or dates that the question asks the system to find.
Only those queries reach search. Reference claims, evidence anchors, and rubrics
stay in the evaluator. Up to five search hits per query receive bounded reads of
up to 40 lines. The report records source hashes, settings, actual evidence
windows, returned characters, and latency. It separately checks whether expected
lexical anchors survived extraction and whether they occur in retrieved evidence.
Anchor coverage across windows does not guarantee correct reading order, table
columns, chart interpretation, or semantic entailment.

The initial construction used some expected numeric values and answer-specific
terms in probes. Review removed them and reran the diagnostic under
`cloudflare-full-docs-v2`. This correction and earlier inspection mean it remains
a development benchmark. It has no heldout or independent model-quality status.
Live acceptance receives only each `question`, never the fixed probes or keys.

The committed v2 baseline finds all required anchors in extraction for **8/8**
answer-bearing tasks, and in bounded retrieved evidence for **5/8**. It misses
the price-increase-anniversary clause in the two net-retention explanation tasks,
and the cover date in the deck/date task. These are actionable context-selection
misses despite the required text existing in the corpus. The ninth task's absent
future result has no positive evidence anchors and is excluded from both ratios;
no retrieval-only abstention success is claimed. No model or paid API was called.
Timing varies by machine and is not a model-latency result.

To pre-grade an actual model report separately:

```sh
uv run python -m provenance.evaluation \
  --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json \
  --result /path/to/result.json --task packet-01
```

This replays local search/read events against the selected frozen corpus, checks
trace consistency and exact quoted evidence, checks answerability and required
numerical value/unit/period triples, and reports whether cited spans contain the
expected anchors. It deliberately does not assign semantic quality from lexical
matches or score qualitative claims using exact answer strings. A human must
review the task rubric, metric identity, source support, causal attribution,
missing claims, unsupported additions, and abstention rationale. A mechanical
pass alone is never an overall task-success score. The existing v1 `grade`
function also accepts an explicit `directory` for replaying a different corpus.

Known coverage gaps remain: native extraction's chart series and table-header
alignment are not verified by anchor presence; there is no measured OCR
comparison, broad domain holdout, or automatic qualitative entailment judge.
Actual live acceptance and spending, when run, are recorded separately from this
offline retrieval diagnostic.

## Recorded live development

[Live acceptance report](reports/live-acceptance.md) records all five development
iterations, 28 paid runs, conservative cost accounting, and initial/final coding-agent
reviews. Source hashes and full public event traces are included. Final synthesis
was checked on four previously stopped tasks after the nine-task BM25 batch;
these are tuned development results, not a combined final nine-task pass rate.
No heldout model evaluation or independent human financial review is claimed.

## Frozen post-development evaluation — 2026-11-07

`company_fresh_tasks.json` contains six additional public development questions
authored and independently checked before live inference, then committed with the
protocol at `ce1a2f2`. They cover three numerical questions with table context,
two single-source qualitative questions, and packet-scoped missing evidence.
The runtime was frozen at `d9057ed`. The original benchmarks and holdout remain
unchanged. Task-author independence is not human finance validation or a secret
holdout; the source company was already inspected during development.

All six ran once: **5 completed**, **2 unchanged mechanical passes**, **4/6
evidence-supported task passes under coding-agent review**. The saved mechanical
failures remain unchanged: two numerical responses are correct but differ from
the expected period string; one correct abstention never reads evidence; one
rejected-quote repair stops for spending-reservation headroom. A supported extra
2023 comparison in fresh-03 violates structured-number output instructions and is
reported separately from the preregistered unsupported-claim criterion.

The [full report](reports/frozen-evaluation-2026-11-07/report.md) links the frozen
protocol, task/source hashes, 6 complete traces, unchanged per-task grades, semantic
reviews, and offline reproduction. Fresh estimates total $0.0863112 at conservative
$0.60/$2.40 input/output per million; combined with prior cloud estimates,
$0.4362039. Neither token estimates nor six single-company tasks establish invoice
charges or production accuracy. No runtime fixes were mixed into the scored batch.
