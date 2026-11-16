# Locked evidence adjudication and read attribution — 2026-11-16

This is a post-hoc development audit, not a replacement benchmark score. The
question-only stage produced 16 interpretations before evidence was shown. Two
fresh independent evidence reviewers and a third fresh adjudicator then assessed
all 60 requirements. Original interpretations and judgments remain verbatim.

The [stage-2 lock](reviews/stage-2-lock.json), committed at `78b5735`, precedes
retrieval attribution. The adjudicator marked 38 requirements supported, 17
partial, four conditional and one unsupported. Its five complete sets belong to
five interpretations across two cases. These counts are coding-agent judgments,
not human financial validation or an exhaustive inventory of support.

All 223 citation occurrences (177 in requirement judgments, plus complete-set
repetitions) match exact supplied source lines. All 60 ordered adjudication notes
match the initial and final statuses: 180 status comparisons. No technical repair
of a submitted review was requested. An independent audit reproduced these checks.

| Case | Locked interpretations | Complete sets | Remaining limitations |
|---|---:|---:|---|
| Q01 American Water Works | 1 | 0 | Named currency remains conditional under the locked requirement. |
| Q02 Coca-Cola | 2 | 2 | Consolidated versus parent-attributable income remain distinct interpretations; display scale must be stated. |
| Q03 Costco | 1 | 0 | Dollar scale is supported; explicit USD identity remains conditional within the balance-sheet-only boundary. |
| Q04 3M | 5 | 3 | I01/I03/I05 have sets; I02/I04 lack the required exact organic-growth definition. Some set evidence is review-only page context. |
| Q05 Johnson & Johnson | 5 | 0 | Cost/inventory scope, valuation comparability and interpretation-specific reasoning remain partial or unsupported. |
| Q06 Verizon | 2 | 0 | Classification criterion remains conditional; the flow interpretation has additional partial measurement/association requirements. |

## Separately frozen attribution

[Plan](attribution-plan.md), implementation, eight synthetic tests and the
[21-file protocol](attribution-protocol.json) were committed at `a84580a` before
generating [the result](attribution-result.json). Exact saved read-line unions
are keyed by source. Retention uses saved retained ranks and verifies actual
response text/locator against hit snippets, excluding omitted/failed reads and
unreturned request tails. This corrected a defect caught during independent
pre-run review; no real result was generated with the defective implementation.

Every interpretation is reported independently for both retrieval branches,
both context policies, prefixes 1/3/5, and delivered/retained read measures.
The run is bound to the previously replay-verified inventory. No new retrieval,
source read, source acquisition or paid provider inference occurred.

| Rubric and measure | Control @1 / @3 / @5 | Page-ranking @1 / @3 / @5 |
|---|---|---|
| Original frozen complete-location packets, delivered/retained reads | 0/6 · 0/6 · 1/6 | 0/6 · 0/6 · 0/6 |
| New wording-based adjudicated sets, any set covered by delivered/retained reads | 0/6 · 0/6 · 0/6 | 0/6 · 0/6 · 0/6 |

Both rows have these values under both context policies. The second row is
existential evidence-set coverage, **not six retrieval failures**: four cases
have no adjudicated complete set. In the other two cases, saved reads lack lines
required by every accepted set. Search snippets and other message context are
outside these read-only measures. Full-page review material never receives
delivery credit merely because it was supplied to reviewers.

The two rows use different rubrics and cannot establish improvement or regression
against one another. The original page-ranking regression remains unchanged and
the challenger remains unpromoted. No original packet, reference answer or score
has been edited. Currency defaults and other proposed revisions are not applied.

Result SHA-256:
`411c22b976635d90a5dab00165627850f767f5e25391a468723767a4745ec7c9`.

## Limits and next work

Independent contexts use the same model family; workflow restrictions are not
filesystem security isolation. Reviewers self-report access and recognition.
The root is an outcome-aware custodian. Native-text quote correctness does not
prove table geometry, financial sufficiency or exhaustive annotation. Public
questions may be recognizable; no model-training non-exposure claim is made.

The [financial-convention research](../../financial-conventions-research-2026-11-16.md)
proposes prospective evidence boundaries and versioned accounting conventions.
This can distinguish strict textual support from analyst usefulness without
silently fitting a rubric to observed results. Separate role-comparison review
must distinguish location additions from role/metric/assumption revisions before
any future annotation update. Reserved validation documents remain closed.

All 399 tests and lint pass. The original 25 tasks and 15-task holdout remain
unchanged; schema validation is not a held-out model evaluation.
