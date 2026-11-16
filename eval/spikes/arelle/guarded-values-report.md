# Timezone and duplicate safeguards — synthetic v2

Expanded acceptance probes found two failures outside the original five-fact
fixture. Its source, driver, manifest and retained result remain unchanged.
The separate `typed_values_guarded.py` version keeps those historical artifacts
reproducible. This is still a synthetic spike, not a production ingestion tool.

## Confirmed findings

On Arelle 2.47.2, fully timezone-explicit source periods using `-05:30` normalize
to `-04:30`; `-00:30` becomes `+00:30`. Both instant and duration boundaries are
affected, without validation errors. Independent review traced this to the
installed `XmlUtil.tzinfo` construction, which signs hours but not minutes.
See the [inspected release source](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/arelle/XmlUtil.py).
The original date-only fixture is unaffected. Mixed aware/naive durations can
instead raise a context-date validation error and are not used to demonstrate
the silent offset defect.

The previous adapter filtered diagnostics to ERROR/CRITICAL, discarding Arelle's
`arelle:duplicateFacts` warnings. It retained occurrences but omitted their
complete/consistent/inconsistent classification. The
[duplicate classifier](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/arelle/ValidateDuplicateFacts.py)
already supplies these distinctions; the new adapter uses it rather than
inventing numeric tolerances or dropping duplicate records.

## Guarded behavior

V2 independently checks each reported period against a deliberately restricted
ISO lexical form: four-digit dates, optional explicit time with up to six
fractional-second digits, and optional `Z` or numeric offset. A date-only end or
instant advances to the next boundary; explicit date-times do not. Unsupported
forms or disagreement with Arelle cause whole-fixture rejection with expected
and observed boundaries. The adapter does **not** repair the library result:
other internal comparisons could already have used the wrong dates.

WARNING codes remain visible. Every duplicate occurrence retains its source path;
groups carry Arelle's complete, consistent and inconsistent flags. Every member
of an inconsistent group is marked `quarantined_inconsistent_duplicate` and
excluded from schema-valid occurrence counts. Other records are labeled only
`schema_valid_occurrence`, not financially correct or benchmark-eligible.
Full diagnostic messages and arbitrary plugin resources are not serialized.

Both adapter source files and all six model documents are bound and rechecked.
The companion matrix binds its scenario builder, tests, original fixtures and
manifest; its four bundled standard-schema hashes must match the frozen baseline.
Candidate synthetic source/schema mutations are individually recorded, never
silently substituted for the original fixture.

| Scenario | Expected guarded disposition |
|---|---|
| Original fixture | Five schema-valid occurrences |
| Negative scale -2 | Assets becomes exactly -0.12 |
| Explicit UTC or +05:30 periods | Offset preserved; no extra day |
| Explicit -05:30 or -00:30 periods | Reject known library mismatch |
| Nil on a non-nillable concept | Reject validation errors |
| Equal assets duplicate | Six occurrences; complete and consistent group |
| EPS 2.50 at decimals 2 / 2.5 at decimals 1 | Six occurrences; incomplete but consistent group |
| Assets -12000 / -13000 at the same decimals | Six retained occurrences; both conflicting members quarantined, four remaining schema-valid |

Fifteen optional tests include the original eight cases plus these expanded
boundaries. Each Arelle session runs in a fresh child process under inherited
OS network denial. The core suite remains 399 tests; optional tests require the
separate pinned environment. No issuer documents, reserved validation, model
inference or financial-answer scoring are part of this work.

Under the OS profile documented in [setup](README.md), run:

```sh
/path/to/isolated/bin/python eval/spikes/arelle/test_guarded_values.py
/path/to/isolated/bin/python eval/spikes/arelle/record_guarded_matrix.py NEW_OUTPUT.json
```

Dimensions, continuations, broader number transformations, equivalent contexts
with different IDs, arbitrary dependency graphs and rendered-cell relationships
remain unverified. The negative fractional offsets are a rejection boundary,
not a claim of supported timezone normalization. A later library version must
pass the same fixtures before adoption; this report concerns the inspected pin.

A [current-release review](release-review-2026-11-16.md) identifies 2.47.5 as the
next candidate but finds the same affected helper in its published wheel and
tagged source. This is static evidence, not a runtime regression result; an
upgrade alone cannot be claimed as the fix.
