# Stage-3 attribution — post-hoc development diagnostic

The adjudication was locked at `78b5735` before attribution. Preserve all initial
and adjudicated judgments. This is a separately versioned wording-and-evidence
rubric, not an alternative-location patch to the original benchmark rubric.
Proposed rubric revisions remain proposals and do not earn credit.

Before generating results, commit this plan, the attribution implementation,
synthetic tests and a protocol binding their bytes plus the frozen inputs.
Use only the saved, previously replay-verified page-ranking run. Verify its full
inventory against its grade and the masked preparation receipt; no new retrieval,
source reads, ranking, provider calls or validation-content access.

For each of six cases, each of 16 interpretations, each control/challenger branch,
each production-newest-first/earlier-optional-results-first-v1 context policy and prefixes 1/3/5:

- Delivered evidence is the union of actual returned read lines through the prefix.
- Retained evidence is the union of saved retained read hits for that condition.
- Key every line by source identity. Do not fill gaps or credit requested tails.
- Every cited span of every requirement in a complete set is jointly necessary.
  Complete sets within one interpretation are alternatives; do not mix sets or
  interpretations. Preserve assumptions and unresolved issues by reference.
- Review-only pages are never added to either union. A review-only citation can
  earn credit only if its exact lines independently occur in the saved union.
- No accepted complete set means `no_adjudicated_complete_set`, not proof of
  unanswerability or retrieval failure. Record unsupported/partial/conditional
  requirements explicitly. Keep all six cases, never shrink the denominator.

Report full per-set missing line identities, per-interpretation dispositions and
case-level counts of any accepted set covered, explicitly existential coverage,
not answer accuracy. Also report the count of cases with any adjudicated set and
all interpretations with sets. Search snippets and other message context are not
included: these are read-evidence-only measures matching historical read coverage.
Historical scores remain unchanged and are shown alongside with their different
rubric label. No new aggregate is a promotion or generalization test.

Capture/hash/parse the same input bytes, reject changed inputs before writing, and
never overwrite output. Exact citation validation and lock verification precede
attribution. Independently inspect the implementation and generated result.
