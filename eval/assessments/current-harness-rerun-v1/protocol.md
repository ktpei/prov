# Current harness rerun: frozen deterministic quality component

User requested a fresh run with current implemented behavior. Baseline code
`eeb21b9`, clean acceptance `d5886cf`: 510 tests plus lint and validation pass.
The shared checkout has 523 passing tests, including thirteen unrelated tests.

Run the existing six-case FinanceBench retrieval/context driver afresh, with
unchanged cases, source files, question-only queries, five-read budget, annotation
packets and both retention policies. All are previously exposed development
cases; no reserved issuer/task selection or new source research. Rebind only
the complete runtime digest to the clean current code in context-protocol.json.
Keep all original input/annotation/driver hashes; mismatch aborts rather than
silently updating them. New directory: `runs/current-harness-rerun-v1-context`;
new grade file: `runs/current-harness-rerun-v1-context-grade.json`.

Use clean checkout and existing read-only source corpus. Execute actual searches,
reads and projections, not old output rescoring. Grade only after fresh replay
matches the new run. Compare annotated packet coverage at one/three/five reads,
blocked projections, completion, and paired outcomes against the historical run.
Keep exact annotation-location coverage distinct from semantic answer correctness.
No promotion is expected solely from unchanged-path reproducibility.

This is one component of the requested current-state benchmark rerun, not the
entire end-to-end evaluation. H2 arithmetic and H3 read authorization are tested
offline but remain disconnected from model-facing tools and cannot receive
end-to-end quality credit. New live CFA/FinQA/TAT-QA/conversation/model-quality
scores are unavailable: the separately frozen follow-up returned HTTP 404 and
stopped paid calls. Do not substitute models/providers or erase those failures.
No new inference spending is authorized by this deterministic protocol.
