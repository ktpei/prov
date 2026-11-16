# Model-input receipt acceptance report

2026-11-16 · H1 · offline infrastructure acceptance

Implementation commit: `3dcd09b`. Frozen protocol: `179d176`, against baseline
`7c61374`. [Protocol](protocol.md); [implementation specification](../../../harness-improvement-spec.md).

## Delivered behavior

The optional `trace-receipts-v1` profile supports the LangGraph/OpenRouter adapter.
Every fully constructed request receives an immutable receipt before spend/size
rejection or external dispatch. It records canonical history, actual projection,
mapped LangChain application messages, tools, invocation options, configuration,
policy hashes, retained/omitted outputs, and successful legacy read fragments.
Search results and error outputs are not evidence fragments. The provider path
uses the same mapped message objects; no model-visible receipt text is added.

Replay rebuilds projection, message mapping, inventories and hashes, then checks
the receipt against run policy, complete canonical event history, attempt IDs,
dispatch/completion markers and reported counts. These checks reject inconsistent
or selectively edited traces; unsigned local traces are not cryptographic proof
against wholesale coherent fabrication.

Checkpoint v3 binds actual instructions, schemas, adapter/projection versions,
generation settings, dependency versions, and full pinned source metadata as
well as the existing text identities. Resume rejects incompatible profiles and
identity drift before dispatch. Completed-result replay makes no provider call.
Legacy is still the default; no existing checkpoint is silently upgraded.

Real ChatOpenAI settings must match the adapter's declared OpenRouter settings.
Injected offline clients are labeled `injected-test-client`; their tests establish
adapter parity rather than real-provider behavior. Receipt reconstruction uses the
locked dependency environment. Credentials are excluded from generated metadata.
Explicit log/checkpoint settings continue to control local persistence.

## Verification

- Seventeen new synthetic tests cover request parity, immutable snapshots,
  projection inventories, malformed grouped calls, unanswered calls, failed requests,
  spending rejection, synthesis/repair, trace tampering, policy drift, metadata drift,
  pause/resume, cached results, explicit logs and unsupported CLI combinations.
- Independent read-only Astra review reproduced four gaps: profile downgrade,
  dropped canonical history, policy/client mismatch, and malformed trace handling.
  All were corrected with regression tests. Follow-up review passed all 17 receipt
  tests and 19 graph tests, plus separate tool-cap, finalization and oversized-input
  probes; it found no remaining material blocker against the protocol.
- Shared checkout: `yarn lint` and `yarn test` passed, **470 tests**. This includes
  13 pre-existing untracked tests owned by the paused XBRL assessment chat; those
  files were not edited or committed in this cycle.
- Clean detached checkout at `3dcd09b`: Ruff check/format, corpus validation and
  **457 tests passed**, using the existing locked dependency environment. Git
  status was clean after verification. These execute the same checks as the Yarn
  scripts without including the paused chat's 13 untracked tests.
- An initial archive-only snapshot produced 13 test errors because existing
  benchmark runners require `git rev-parse HEAD`. Repeating in a clean Git checkout
  resolved that verification-environment issue without code changes.

## Decision and limits

Accepted as opt-in infrastructure after clean committed-code checks passed. No paid
calls, new source selection, reserved validation inspection, or original holdout
evaluation occurred. No financial accuracy, semantic-support, token-saving or
provider-attention improvement is claimed. Application messages are not SDK wire
bytes. Existing SQLite ResourceWarnings remain; this cycle does not fix them.

H2 next introduces bounded evidence-linked arithmetic with independently replayed
Decimal and financial-scope checks. Separately queue the research chat's synthetic
external-success/local-acknowledgement crash test; retain current conservative
no-blind-retry protection. No framework migration is required by H1.
