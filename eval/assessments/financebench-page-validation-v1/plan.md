# Prospective page-ranking validation reservation

Reserve six additional FinanceBench 10-K source groups using metadata only, before
any results from the new page-ranking experiment. This is a prospective local
validation subset of the existing development partition, not the original holdout,
a secret test set, or proof that models have never seen these public documents.
No question, reference, evidence text or source content may be opened before the
final retrieval policy and validation protocol are committed.

## Selection fixed before execution

Use the pinned 150-task release and 361-row document metadata from FinanceBench
commit `cc39aeb4afdf33909ee1412188bf89035950c2eb`, with SHA-256 values in
`reserve.py`. Parse task records only to project ID, document name and company;
question/reference fields must never be displayed, inspected or used. Capture, hash
and parse the same raw bytes for every input, including registry, selector and plan;
reject changes detected before returning the reservation. Document
metadata contains no question/answer content. Require exact document joins and
`doc_type == "10k"`; fail ambiguous eligible joins and company mismatches.

Preserve seed 17 membership: groups whose first eight hex digits of
`canonical_hash([17, doc_name])`, interpreted as an integer, are divisible by five
remain internal-final and are excluded. Do not recruit them via exposure overrides.
Exclude every group in the current development exposure registry, every company
mapped from those groups, and the existing FinQA/ConvFinQA aliases recorded in the
selector. Conservatively also exclude Casey's General Stores, Old Dominion Freight
Line and Ameren, reserved for the separate native-HTML assessment. Case-fold names;
do not infer new company mergers/aliases from question content. Four TAT-QA UUID
issuer identities remain unresolved: no universal cross-suite disjointness claim.

Rank groups by `canonical_hash([17, "page-ranking-validation-v1", doc_name])`, then
document name. Greedily reserve the first six distinct companies. Choose one task
per group by `(canonical_hash([17, task_id]), task_id)`. No source availability,
question type, financial metric, answer or performance influences the choice.
Retain the complete candidate ledger, all dispositions, metadata conflicts,
registry snapshot/hash, alias map, selector/plan hashes and preparation order.
If fewer than six eligible companies exist, stop with an explicit selection failure;
do not relax rules or pick replacements. Commit this plan and selector before
running selection, then commit the resulting reservation before development runs.

## Reservation is separate from exposure

`reservation.json` records closed content, not observed development exposure. Do
not add these groups to `development-exposures.json` merely for metadata selection.
They retain original development partition membership. Future development
selection and research must exclude all reserved issuers until validation closes.
Before opening validation content, verify the current exposure registry and any
new research against this frozen reservation. Unexpected exposure invalidates the
local-unseen claim for that slot; retain it and its disposition, never replace it.
This is a workflow gate, not a global filesystem access-control guarantee.

## Required before validation execution

Freeze the final retrieval policy after development comparison, then commit a
validation protocol binding it, this reservation, corpus acquisition/extraction,
parameters, candidate/read/context limits, actual-cost accounting and all-six
failure denominators. Do not tune using validation feedback or substitute
unavailable documents. No acquisition is performed by this reservation script.

Use independent fresh-context annotation with a predeclared scope broader than
reference pages alone. Freeze interpretation, role definitions, allowed page
review and disagreement rules before outcomes. A preregistered blinded pooled
judgment supplement is possible only after all conditions are locked and before
feedback reaches developers. Distinguish frozen-location coverage, adjudicated
semantic support, ambiguity and model answer accuracy. Preserve historical scores.
See [annotation-validity research](../../incomplete-judgments-research-2026-11-16.md).

Original 25 tasks/15-task holdout, prior protocols, annotations and results stay
unchanged. No paid inference, source retrieval or model evaluation is needed for
reservation. This plan does not authorize new SEC retries.
