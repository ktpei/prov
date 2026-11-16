# Broader FinanceBench context validation: selection and acquisition gates

Select six tasks from six previously uninspected FinanceBench 10-K source groups,
with at most one group per known company. This follows development on Walmart,
NIKE and Ulta; it is broader development validation, not a secret holdout or an
unbiased estimate of generalization. Do not inspect selected questions, answers,
evidence or PDF content before the selection is committed.

## Metadata-only selection

Use the existing immutable release150-task file and361-row document metadata at
commit cc39aeb4afdf33909ee1412188bf89035950c2eb. Verify their pinned SHA-256 values.
Parse only metadata for selection: task ID, document name, company and document
metadata. Full JSON records necessarily contain question/reference fields, but
those fields must not be displayed, inspected or used by selection.

Preserve seed17 and the existing group partition: a document is internal-final
when int(canonical_hash([17, doc_name])[:8],16) %5 equals zero. Never recruit those
groups via exposure overrides. Join exact document names; require a unique
metadata record with doc_type exactly `10k`. Do not silently collapse conflicting
metadata. Record conflicts and excluded candidates in the ledger.

Exclude every registered exposed group and every mapped exposed company. Known
FinanceBench companies derive from exposed document metadata; cross-suite report
aliases are explicitly recorded by the selector. Four exposed TAT-QA UUID groups
have no known issuer metadata. Keep those unresolved in the ledger: this sample
cannot claim global issuer disjointness from all prior suites. It is disjoint
from known exposed FinanceBench companies and registered source groups.

Rank eligible document groups by canonical_hash([17,"context-validation-v1",
doc_name]), then doc_name as tie-breaker. Greedily choose the first six with
unique case-folded company names. Within each group, choose the task minimizing
(canonical_hash([17, task_id]), task_id). No source-availability, question type,
answer, evidence, metric or observed performance may influence selection.

Save all candidate metadata/dispositions, registry snapshot/hash, alias map and
unresolved mappings, selected order and original task-hash preparation order.
Freeze selector and plan before selection; commit the selected manifest before
source acquisition. Do not change the sample after inspecting selection/results.

## Acquisition and evaluation gates

Research the pinned repository's PDF inventory via tree metadata. Mirror bytes
may be verified against pinned Git blob identity and local SHA-256; that does not
prove byte equivalence to the current issuer URL or publication availability.
Freeze an acquisition policy/inventory before bounded one-shot downloads. Preserve
all six dispositions and partial failures; no replacement tasks, silent fallback,
retry or source substitution. Record original source URL separately from mirror.
Do not extract or inspect PDF contents in the metadata/acquisition stage.

Before question/evidence inspection or retrieval evaluation, record development
exposure reservations and freeze preparation, extraction, annotation and comparison
rules. Keep selected, acquired, extracted and gradable denominators separate.
The later comparison must keep the existing baseline/challenger code fixed, the
same 32K output-character budget and original-question ranked-parent read schedule.
A separate frozen plan must define packets and evaluation before executing it;
this selection gate alone does not authorize result-dependent annotation/tuning.

No paid inference is needed for selection or source acquisition. Existing original
25 tasks/15-task holdout and all frozen benchmark results remain unchanged. The
unresolved six-filing native-HTML cohort is a separate assessment; do not retry its
blocked SEC routes as part of this work.
