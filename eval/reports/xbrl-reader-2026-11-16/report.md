# Exact-ID typed-fact reader — 2026-11-16

The opt-in `provenance.xbrl_reader.FactReader` delivers authenticated experimental
fact records without changing the default harness tools. This is an exact-ID
transport, not discovery, financial grading or a claim of benchmark improvement.

## Contract

The constructor receives export bytes, one source metadata record, original
filing bytes and trusted expected hashes for export/metadata. Expected hashes must
come from an authenticated producer receipt; computing a hash from arbitrary
uploaded content does not establish trust. The reader consumes already validated
exports and does not replace taxonomy/schema validation.

Each read preserves the complete selected fact, referenced context/unit, duplicate
membership, linked continuation records and exact original UTF-8 source fragments
for fact/context/unit/continuations. Original fragment byte ranges and hashes
remain attached. The source metadata preserves issuer delivery versus canonical
SEC identity, artifact class and temporal availability. A canonical SEC URL does
not imply SEC byte equivalence or earlier availability of issuer bytes.

`read(occurrence_id, as_of=None)` returns a complete selected-occurrence payload
only if the serialized response fits 12,000 Unicode characters. Otherwise it
returns `deferred`, payload length/hash and a range-read instruction. A subsequent
`read(occurrence_id, start=N, length=M, as_of=...)` returns at most 4,000 payload
characters, with positions and chunk/full-payload hashes. The payload is canonical
JSON, hashed as UTF-8. JSON escaping and identity overhead count toward the same
response budget; an oversized response rejects atomically. Callers can reduce
chunk length. No string or XML evidence is silently clipped. Reconstruct and
verify the whole payload before awarding complete payload delivery credit.

“Complete” means the selected-occurrence bundle. It does not deliver duplicate
peers, ancestor/descendant fact records, table headers or taxonomy defaults unless
separately requested through their appropriate source path. Defaults remain in
the authenticated export; the reader never infers effective default dimensions.
Schema validity, source binding, rendered visibility and financial sufficiency
remain separate. Inconsistent duplicates retain their quarantine disposition.

Temporal eligibility is checked before occurrence lookup. A blocked request does
not reveal whether the requested ID exists. An omitted cutoff follows the existing
explicit `not_requested` policy. Returned metadata is detached from internal state.

## Verified reconstruction

[reconstruction.json](reconstruction.json) records a hash-bound inventory-wide
check over all 504 existing ODFL occurrences, not the eight proposed questions.
There are 484 complete first responses and 20 deferred payloads. All 20 reconstruct
through 419 chunks, giving 923 total responses including initial requests. The
maximum response is 11,615 serialized Unicode characters; these are not tokens.

Every reconstructed fact/context/unit and duplicate group matches the frozen
export. The checker requires the exact ordered original-fragment inventory and
all linked continuation records, then binds each fragment ID to its exact
original node interval before checking bytes and hashes. Empty or wrong-node
substitutions reject even when their own slice hashes are internally consistent. Chunk/full-payload hashes and lengths agree. Historical availability is
blocked; source acquisition bounds are not backdated to the reporting period.

Nine new regression tests cover exact evidence, signed zero/nil, Unicode chunk
reconstruction, caller mutation, receipt mismatch, quarantine, invalid ranges,
oversized metadata, historical access and missing/substituted reference rejection.
These checks do not establish financial sufficiency or correct discovery.

Run the reproducible inventory check with:

```sh
uv run python -m eval.scripts.check_xbrl_reader /tmp/new-reader-check.json
```

The [eight proposed cases](../../assessments/xbrl-evidence-delivery-v1/case-plan.md)
have independent source review. Their final role alternatives, machine manifest
and case budgets remain to be frozen before candidate question execution/scoring.
The reader has not been promoted to default tools. Reserved evaluations stay closed,
and this cycle makes no paid model calls.

Independent review reproduced the retained check byte-for-byte: SHA-256
`5ddad7e76a9290fdf776cef0cc102ec560fabfb0192df4a06efa4f8866e86495`. All eight input hashes
were verified, both source-substitution attacks reject, and lint plus all 440
core tests pass.
