# Frozen acquisition policy: six pinned PDF blobs

This stage downloads the six already selected mirror artifacts in inventory order.
Selection `aaeb24e` and inventory `5fdcf20` remain unchanged. No source substitution,
availability-based replacement, retries, fallback routes or financial-content
inspection. No issuer/SEC URLs are requested. The exact raw.githubusercontent.com
URLs contain the pinned FinanceBench revision and validated PDF paths.

Before any request, verify protocol/script/runtime hashes, selection/inventory,
the saved commit-to-tree chain, all six unique selected identities, each regular
blob entry and size, and the original-versus-mirror URL mapping. Require the raw
metadata response hashes already recorded in inventory.json. Freeze this plan,
script and input protocol before executing.

Issue one request per source with identity encoding and no redirects. Accept HTTP
200, the exact requested URL and PDF/octet-stream content types. The socket-operation
timeout is 20 seconds; a 120-second elapsed check runs between bounded reads and
after EOF. This is not a hard total wall-clock limit: urllib may perform multiple
socket operations while parsing headers/chunks. No process-wide duration guarantee
is claimed.

Read no more than the expected Git-tree size plus one byte, with a 32-MiB maximum
per declared object. A successful body must begin with `%PDF-`, exactly match the
expected byte length and match SHA-1 of `blob <length>\0` plus the bytes. Also record
an independent SHA-256. Declared Content-Length, if supplied, must agree. Preserve
partial/error bytes with separate names and hashes; do not classify them as PDFs
or resolve LFS/error bodies through another route.

Persist all six pending slots before dispatch, each request start, and each result.
Ordinary network/identity failures consume the slot and leave the other selected
slots eligible for their one attempt. Interruption preserves partial bytes and
pending slots. Recheck frozen inputs before each request and after all requests;
recheck every verified saved body at the end. Any input/artifact mutation invalidates
the run. Existing output directories are rejected. Completion means the acquisition
attempt has recorded dispositions for all slots, not that all downloads succeeded.

`verified_blob` establishes repository-byte identity and PDF magic only. It does
not establish PDF structural usability, issuer-byte equivalence, publication timing,
financial correctness or extraction completeness. Store original metadata URLs
separately. Request/finish timestamps are observations, not publication dates.
No PDF text extraction, page rendering, question/answer/evidence inspection or model
calls occur in this stage. Retain all six selected/acquired/verified denominators.

The script lives outside production runtime modules and is independently hashed.
After acquisition, freeze a separate preparation/extraction/annotation gate before
opening financial content or evaluating retrieval/context policies.
