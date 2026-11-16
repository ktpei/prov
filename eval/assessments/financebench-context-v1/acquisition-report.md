# Six pinned source bodies acquired and byte-verified

All six fixed slots succeeded on their first request: **6/6 verified repository
blobs**, 10,443,871 bytes total, zero failed or partial bodies. The sample was not
changed. Implementation `51ae81f` and protocol freeze `c59d45e` preceded requests.
The [plan](acquisition-plan.md), [protocol](acquisition-protocol.json),
[inventory](inventory.json) and [full result](acquisition-result.json) record the
policy, expected identities, responses, timings and independent SHA-256 values.
Original bodies remain under `runs/financebench-context-v1-acquisition/`.

Each body passed exact pinned Git-tree byte length, SHA-1 of the Git blob header
plus bytes, PDF magic, matching declared Content-Length, identity encoding and
HTTP status/URL/media-type checks. All six saved bodies and frozen inputs were
rechecked before completion. There were six requests, no redirects, retries,
fallback sources or issuer/SEC requests. No download failure was replaced.

| Stage | Count |
| --- | ---: |
| Selected task/source slots | 6 |
| Requested bodies | 6 |
| Verified pinned blobs with PDF prefix | 6 |
| Failed/partial bodies | 0 |
| Extracted or rendered documents | 0 |
| Inspected questions/evidence | 0 |
| Evaluated retrieval/context cases | 0 |

Verification establishes identity to the selected repository blobs. It does not
prove PDF structural usability, current issuer-byte equivalence, publication time,
financial correctness, native extraction completeness or annotation validity.
Only bytes, signatures and hashes were inspected; no financial text or pages were
opened. The next gate must freeze preparation/extraction/annotation rules and
reserve these groups for development before content inspection.

Acquisition uses 20-second socket-operation timeouts and a 120-second elapsed
check between reads; this is not a hard wall-clock guarantee. The overflow probe
can retain expected size plus one byte, up to 32 MiB + 1, solely as a failed partial
artifact. Actual selected objects were all below 2.4 MB and passed exact size.

Five synthetic tests cover exact success, wrong bytes, overflow, HTTP failure,
unsafe route preflight, interruption, input mutation and changed saved bodies.
Independent implementation review found no blockers. All 315 repository tests and
lint pass. No paid model calls occurred; cumulative spending stays $0.4814193.
The separate native-HTML acquisition cohort and original holdout remain unchanged.

Independent byte-only review rehashed all six bodies and verified the complete
commit/tree/blob/input chain. The tracked result matches the local receipt exactly
(SHA-256 `5d82f7e143b89f6984acd3d69686717bf601f25b1f7a00b36293cdc20de5b7e9`);
the output directory contains only six PDFs and that receipt. No financial parsing
or additional requests occurred during review.
