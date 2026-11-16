# Blinded evidence audit — fixed scope and staged review

This is a post-hoc development audit of the same six exposed FinanceBench cases.
It cannot make them untouched again. Preserve original packets, results and ranking
parameters. The separate validation reservation remains closed. Reviews are by
coding agents, not human financial experts, and cannot establish exhaustive support.

## Stage 1: interpretation before evidence

Commit this plan, the packet builder and review instructions before generating
question packets. Project only each prepared input's literal question into neutral
case IDs. Use deterministic ordering by SHA-256 canonical JSON
`[17, "evidence-audit-interpretation-v1", task_id]`, then task ID. Assign Q01–Q06.
Keep task/document identity mapping and original prepared order in a separate
custodian file. No reference answers, original rubric, evidence spans, outcomes,
retrieval ranks or condition names appear in the reviewer packet.

Bind input bytes, builder, plan, instructions and output hashes in a stage-1 receipt;
commit the receipt and reviewer questions before dispatching reviewers. Verify
all receipt input/output hashes again immediately before dispatch. Capture,
hash and parse the same bytes, and reject changed inputs before publishing outputs.
Two fresh-context independent reviewers receive identical questions and instructions,
with no access to other files or the previous conversation. Their exclusive outputs
are separate JSON files. Preserve both initial interpretations verbatim. Each records
literal meaning, requested output, necessary facts/context/relationships, acceptable
interpretations, material ambiguities and whether the question is well-defined.
Do not infer an answer, inspect documents, browse benchmarks or resolve an ambiguity
by guessing what a reference expects.

Lock both reviews before proceeding. A third fresh, outcome-blind reviewer
reconciles all six cases using only questions and the two initial interpretations.
The outcome-aware custodian does not decide which disagreements merit review. Record
unresolved interpretations separately; do not force agreement or choose the one
that later improves a score. Freeze interpretation/rubric versions before evidence
is shown. A later change to required roles is a rubric revision, not a new location.

## Stage 2: fixed evidence pool and masked review

After stage 1 is locked, pool the first five saved reads from each of the control
and page-ranking branches in `financebench-page-ranking-v1` for every case. These
also cover the earlier compact-control read set. Include original frozen annotated
spans as controls. Do not add unused pool-25 candidates, oracle witnesses or new
retrieval. Include all six cases equally; failures remain explicit. Deduplicate
identical source spans and retain original/text/location identities in custody.

Give evidence opaque IDs and order by canonical hash of
`[17, "evidence-audit-evidence-v1", case_id, source_id, start_line, end_line]`.
Do not reveal ranks, policies, retention, old correctness flags, control status,
original rubric or reference answers. Preserve issuer, period, units, source/line
identity and literal text needed to interpret each excerpt. Supply every distinct full native-text
page containing any pooled span exactly once to both reviewers as explicitly
review-only context; no selective supplementation, adjacent-page expansion or new
page search. This source-page supplement
never earns delivered-evidence credit unless present in a saved response.

Prepare the same evidence packet for both independent reviewers and hash-lock it
before review. Reviewers assess each declared interpretation separately, supporting
roles, missing facts, conflicts, and complete evidence sets with exact source spans.
A useful individual passage is not automatically a complete alternative. Keep both
judgments before third-reviewer adjudication. Record any changed interpretation as
a separately versioned rubric revision with rationale; do not silently retrofit it.

## Stage 3: lock judgments, then attribute results

Freeze adjudicated judgments and disagreements before revealing policy attribution.
Only afterward may the custodian map accepted complete alternatives onto actual
saved delivered/retained spans for every condition and prefix. Apply the same
judgments to all conditions and retain all-six denominators. Do not credit a policy
for evidence merely available elsewhere in the pooled material or page supplement.

Compare the frozen original roles with new interpretations and evidence judgments.
Report alternative-location additions separately from role/metric/rubric changes.
Reference-answer agreement is a separate later observation, not the interpretation
criterion. Publish original scores unchanged alongside any separately versioned
new diagnostic, unresolved cases, assessor disagreement and annotation scope.

## Blinding limits and access record

The root custodian knows earlier outcomes and cannot act as a blinded judge.
Fresh reviewers are instructed to access only their assigned stage packet and own
output; this is workflow isolation, not a filesystem security guarantee. Record
reviewer role, stage, packet hash, dispatch/completion and any disclosed outside
access. Source names/literal public questions may be recognizable, so do not claim
perfect anonymity or model-training non-exposure. Reviewers must disclose recognition
or prior knowledge and avoid using remembered benchmark answers.

No paid provider calls, new source acquisition, retrieval-policy tuning or validation
content access is part of this audit. Existing repository lint/tests remain required.
