# Schema-resolved synthetic values and source ancestry

This extends the missing-schema negative preflight with five deliberately authored
numeric occurrences and a local synthetic taxonomy. It is not a general extractor
or an issuer accuracy evaluation. No default tool or project dependency changed.

## Acceptance contract

Before validation, [the manifest](typed-manifest.json) binds the original XHTML,
synthetic taxonomy and four bundled standard XBRL schemas. The process must have
OS network denial; a loopback probe requires EPERM. Arelle runs with full DTS
loading, validation enabled, formula execution disabled and an isolated cache.
The loaded model-document inventory must equal the six declared documents, and
their bytes are rechecked after extraction. This binds model documents, not every
runtime library, plugin or cache resource; complete runtime hashing remains open.

The independent source parse rejects malformed XML, DTDs, duplicate source IDs,
unsupported inline fact types and nested numeric content. Each parsed fact must
match the original occurrence's path, expanded element name, attributes and text.
The path is resolved against the original tree with recorded namespace bindings.
Nearest containing cell, context and unit paths are retained with the original
source hash. This proves **source ancestry**, not rendered visibility, table-header
meaning, literal byte-range quotation or financial correctness.

Acceptance requires API success, one model, no model errors or ERROR/CRITICAL
diagnostics, resolved concepts, valid typed facts and exact Decimal values.
Every source nonFraction occurrence must appear exactly once in the parsed
inventory. Source IDs are occurrence identities only after global uniqueness
checks; no deduplication or value-based cell joining occurs.

## Independently declared synthetic expectations

| Occurrence | Source representation | Expected typed value | Period / unit |
|---|---|---|---|
| Assets | `12`, scale 3, sign minus | `-12000` | Instant; USD |
| Revenue | `1.25`, scale 6, namespace alias | `1250000` | Duration; USD |
| Earnings per share | `2.50`, no scale | `2.50` | Duration; USD / shares |
| Missing amount | Explicit nil | null | Instant; USD |
| Zero amount | `0`, not nil | `0` | Instant; USD |

The source reports instant/end date `2025-12-31`; normalized boundaries are
`2026-01-01T00:00:00`. Duration start remains `2025-01-01T00:00:00`. Both lexical
and normalized forms are preserved, without inventing a timezone. Concepts,
entity identity, unit measures and expected cell IDs are checked independently
of the values. Precision/sign/scale attributes remain source attributes; the
adapter neither rescales typed values nor rounds according to decimals.

An early authored taxonomy used a nonexistent standard per-share type. Arelle
rejected it; the fixture was corrected to a decimal item with a divided unit
before freezing. A unit-mutation test initially expected an adapter error, but
Arelle correctly rejected the invalid USD/USD unit earlier. The final mutation
uses valid-but-wrong USD/EUR to exercise the adapter's independent unit check.
These are fixture-development findings, not benchmark outcome changes.

## Verification and limits

Eight optional tests run Arelle in fresh child processes inheriting OS network
denial. They cover reproducible success, changed source/schema hashes, unknown
concept/context/unit/format, invalid sign/scale/numeric text, empty non-nil values,
period-type/date failures, valid-but-wrong values/units/concepts, duplicate IDs,
changed source-cell ancestry, malformed XML and unsupported fact content.
The existing 399 repository tests and lint also pass. Optional acceptance tests
are separate from the default suite and require the isolated Arelle environment.

Run under the documented OS profile:

```sh
/path/to/isolated/bin/python eval/spikes/arelle/test_typed_values.py
/path/to/isolated/bin/python eval/spikes/arelle/typed_values.py NEW_OUTPUT.json
```

These commands must be wrapped with `sandbox-exec` as shown in [the setup](README.md).
Outputs are never overwritten. The fixture is intentionally fixed: dimensions,
continuations, explicit date-times/timezones, negative scale, duplicate-fact
classification, transformed/localized numbers, parser recovery, rendering,
arbitrary issuer extensions and unknown dependency graphs remain acceptance work.
No issuer document has been loaded. The next iteration must expand these cases
before treating this spike as a usable knowledge-ingestion path.

The implementation was committed at `b06b476` before writing the retained
[result](typed-values-result.json). Root reproduced it byte-for-byte in a fresh
denied-network process. [Verification](typed-values-verification.json) records
independent implementation/test review separately from root result reproduction.
Result SHA-256: `4308ed64e294d474c3298feb24692bc8914408e9e5ee0f5a2bc9b0fcd3476e34`.
