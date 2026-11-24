# Daloopa quick benchmark results — 2026-11-20

**The 25-question live retrieval pilot is complete.** With one confirmed reference
parser defect corrected diagnostically, numerical exact match is **4/25 (16%)**
and within 1% is **7/25 (28%)**. The original frozen scorer reports **3/25 (12%)**
and **6/25 (24%)**, respectively. Both results are preserved; no model question
was rerun to obtain the adjustment.

| Measure | Result |
|---|---:|
| Selected / attempted | 25 / 25 |
| Returned numerical answers | 8 |
| Returned abstentions | 12 |
| Stopped / failed | 4 / 1 |
| Frozen exact numerical matches | 3/25 — 12% |
| Frozen within 1% / within 5% | 6/25 — 24% / 6/25 — 24% |
| Diagnostic exact matches after sign correction | 4/25 — 16% |
| Diagnostic within 1% / within 5% after correction | 7/25 — 28% / 7/25 — 28% |
| Estimated model + Exa cost | $1.2211698 |
| Model calls | 134 |
| Sum of task runtime | About 7 minutes |
| Uncertain billing | None |
| Human-validated supported accuracy | Not established |

The denominator includes every selected question, including refusals and stopped
runs. This is a small, exposed, category-balanced development sample and an
adapted API-agent condition. It is not the full 500-question Daloopa benchmark,
not a secret holdout, and not directly comparable with Daloopa's historical
web-app/MCP leaderboard percentages.

## What failed

The primary issue is **retrieving and reading the exact evidence**, not simply
formatting an answer. Twelve cases ended in abstention. Trace review found cases
that searched repeatedly without reading, opened only the first part of a long
filing, or could not reach the target table within the lean limits. Two stops hit
the tool-context-size boundary; two hit the model-call limit. One attempt failed
at the output-length boundary.

The eight numerical answers received independent coding-agent inspection:

| Case | Diagnosis |
|---|---|
| Eurofins | Exact EUR 626m match; issuer table supports requested FY2023 metric. |
| Northern Trust | Exact USD 13,349.2bn match; correct December 31, 2024 custody measure. |
| Blackstone | Exact USD 734,541,603 thousand match; correct Q3 2023 fee-earning AUM. |
| Discover | Model −365m USD is correct against publisher wording and captured SEC table. Preparation lost the minus outside a Markdown currency link. |
| iRhythm | Model 13.677m USD comes from the detailed filing; reference is rounded to 13.7m. Tolerance match, exact mismatch. |
| GMS | Model uses source presentation's rounded 665.7m USD; reference is 665.696m. Tolerance match, exact mismatch. |
| YDUQS | Model uses rounded 1,459m BRL versus reference 1,458.7m. Tolerance match; flattened chart order limits independent period-column verification. |
| SBI | Model substituted nine-month cumulative EPS of JPY 217.90 for standalone-quarter EPS; reference is 46.16. |

This review is not independent human finance validation. In particular, numerical
matching and matching citation quotes alone do not establish semantic support.
The machine score therefore keeps supported accuracy null.

## Scoring defect and preservation

The Discover correction is recorded in [diagnostic-adjustment.json](diagnostic-adjustment.json),
bound to the original score hash. [score.json](score.json) remains the frozen
machine score. The parser was fixed **after** all 25 questions finished, with a
regression test for minus signs outside Markdown/currency formatting. No runtime
or reference changes were mixed into the live batch.

Original preparation was archived byte-for-byte at
`runs/benchmark-prepared/daloopa-2026-11-20-frozen`. Current default preparation
was regenerated after the fix; quick selection remains the same 25 IDs. Full
inventory remains 500: 426 parseable references, 73 requiring reference review,
and one reserved AMD case. Full mode executes the 499 nonreserved questions and
retains unresolved references as unscored cases.

## Execution and verification

Model: `deepseek/deepseek-v4.1-flash-1017`, original research loop plus the Exa
skill's objective-aware search schema and system-prompt guidance. Each question
had at most six model calls, eight tool calls, 90 seconds, and 1,800 output tokens.
Search used auto mode, five results and highlights; citations required separate
numbered reads. The existing within-task answer repair/finalization behavior
remained active. No batch retries or best-of selection occurred.

The batch had a $2 aggregate ceiling and $0.12 per-task ceiling. Estimates combine
Exa's returned costs and conservative $0.60/$2.40 per-million model token rates;
these are not invoice charges. The separate Exa connection check cost $0.008.
No reserved FinanceBench issuer contents or original heldout tasks were evaluated.

All source-code hashes matched the pre-dispatch run policy at completion. Frozen
scores reproduced exactly before and after the post-run parser fix, using the
archived preparation. Lint and 616 tests passed after the fix. Raw questions,
answers, receipts, evidence snapshots and cost ledgers remain under
`runs/daloopa-quick-2026-11-20/`; third-party source content is not redistributed in
this report. [Protocol](protocol.json) and [summary](summary.json) record identities,
paths, metrics and hashes.

The next useful experiment is targeted document navigation under the same frozen
questions, with scoring corrections versioned separately. Simply increasing the
number of questions would measure the same retrieval bottleneck more expensively.
