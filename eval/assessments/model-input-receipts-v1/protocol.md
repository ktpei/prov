# Model input receipt acceptance protocol

Frozen implementation plan · 2026-11-16 · H1

Baseline: `7c61374`. This is an offline infrastructure acceptance cycle, not a
financial accuracy experiment. No paid requests, source selection, heldout content,
or changes to the other chat's unfinished XBRL assessment are authorized by it.

Hypothesis: a receipt created from the exact projected/mapped application request
can expose model-visible evidence and policy drift without changing legacy model
inputs, tool behavior, generation settings, or accounting.

Implement the `trace-receipts-v1` opt-in profile for the LangGraph/OpenRouter path.
Other adapters and the scripted demo reject this profile before execution; default
legacy paths remain unchanged. This support boundary is deliberate and explicit.
Use an injected offline chat client to exercise real adapter mapping and graph
behavior without live inference. No broad framework or tool registry is needed.

Acceptance requirements:

1. Record canonical history, projected messages, normalized application request,
   their digests, effective instruction/schema/config identities, projection
   inventory, and successful legacy read fragments before provider dispatch.
2. The provider receives the same mapped message objects represented by the
   receipt; no second projection or added model-visible IDs. Record final-only
   mode. Failed requests retain receipts. Distinguish preflight rejection from a
   submitted provider attempt; no claim of SDK wire-byte/provider attestation.
3. Verify receipts by rebuilding projection, message mapping, inventory and hashes
   from their canonical input. Reject omission, changed content, wrong IDs, altered
   mapping, and digest-only forgery. Read evidence excludes search and error output.
4. Checkpoint v3 binds actual model instructions/tools, projection and adapter
   versions, generation controls, and full pinned source metadata. Reject legacy
   checkpoint resumes into v3 and any identity drift before a provider request.
   Legacy resumes and cached completed reports stay unchanged.
5. Cover pause/resume, final synthesis, answer repair, provider error, spending
   rejection, context omission, multi-call grouping, and explicit logging. Receipts
   must survive failed calls; no key/Authorization value enters generated metadata.
6. Paired fake-client runs must have identical actual messages, options, tool
   bindings, calls, output and accounted cost with the profile on versus off,
   apart from observational traces/profile identities.
7. Run targeted adversarial tests, `yarn lint`, and `yarn test`. Record dirty-tree
   scope separately from committed-code acceptance; preserve five unrelated
   untracked assessment files. Lead inspects implementation and independent review.

Decision: accept only if all requirements pass; otherwise fix or retain incomplete.
This can establish receipt integrity and compatibility, not improved research
accuracy, provider attention, semantic support, or reduced token cost.

Ownership: lead edits receipt module, OpenRouter adapter, graph/CLI integration,
focused tests, and documentation. Read-only Astra reviewer audits independently.
The closely coupled request/checkpoint changes are serialized in one checkout.
