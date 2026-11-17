# H3 first increment: controller-owned typed read authorization

Freeze before implementation. Baseline `b067f87`. No paid inference, source
selection or heldout content. Use the existing real FactReader with synthetic
authenticated artifacts. Preserve default agent tools and H2 interfaces.

Implement a run-scoped session owned by the controller, constructed with a trusted
FactReader and fixed availability cutoff. Model arguments can request an occurrence
and chunk range, but cannot register response objects, change the run/cutoff, or
mark evidence accepted. Every successful reader call records a content-bound
receipt containing run, policy, sequence, exact request and copied response.
Blocked availability records remain diagnostics and never authorize payloads.

Full reads must match declared canonical payload hash/length. Chunked delivery
requires a first offset of zero and consecutive nonoverlapping ranges, stable
source/reader/availability/payload identity, individual chunk hashes and a final
canonical JSON payload matching the full declared hash/length. Reject altered,
missing, out-of-order, overlapping or cross-identity pieces atomically. Bound
aggregate reconstruction at 256,000 characters; this is a backend diagnostic
limit, not permission to send oversized context to a model. No automatic reads.

Expose copied read records and completed delivery records with run-scoped IDs
binding their exact receipts and payload. Replays must execute the recorded
requests against a separately trusted reader and compare the full records and
completed inventory; self-consistent attacker hashes alone are insufficient.
Reading already delivered values again may produce a new delivery identity.

Completed delivery is not semantic admission, numeric eligibility, or evidence
that a model saw the payload. Nil, inconsistent duplicate quarantine, unknown
scope and source limitations remain intact. This increment must not construct
an H2 accepted snapshot or expose calculator/answer-v2 tools. The remaining H3
work is deterministic semantic admission, submitted-request visibility, v2
claim/derivation validation, dispatcher budgets and model-facing integration.

Acceptance: actual synthetic FactReader full/Unicode chunk reads, cutoff block,
gap/overlap, incomplete/malformed/hash-mismatched/cross-identity payloads,
aggregate overflow, immutable outputs, cross-run identity and trusted-reader
replay/tampering. Independent review, lint and full tests required. No financial
effectiveness or H3 completion follows from these delivery tests.
