# Context markup in exposed HTML sources — 2026-11-16

The [reproducible inventory](inventory.json) inspects the four already-exposed
HTML snapshots from the table-template compatibility check. Original hashes match
that historical record. All four dispositions are retained; no new source was
fetched. This is descriptive development research, not representative coverage or
a prospective evaluation.

| Source | V2 tables / cells | Explicit `th`, `headers`, `scope` | Lexical `ix:nonfraction` tags | V3 disposition |
|---|---:|---|---:|---|
| Cloudflare Q3 2024 filing | 55 / 8,247 | 0 / 0 / 0 | 1,016 | Extracted |
| Cloudflare Q3 2024 release | 16 / 2,682 | 0 / 0 / 0 | 0 | Rejected: unsupported raw-text context |
| Old Dominion June 2025 filing copy | 24 / 4,084 | 0 / 0 / 0 | 452 | Extracted |
| Old Dominion September 2025 filing copy | 24 / 4,067 | 0 / 0 / 0 | 452 | Extracted |

Successful v3 counts equal v2 counts in these three documents; this does not
establish semantic equality or extraction completeness. The release rejection
is an explicit v3 limitation, not a new v2 regression or financial failure.
Absent semantic HTML attributes do not mean absent visual headers. Colon-tag
counts are lexical HTMLParser observations, not namespace validation, visible
fact counts, valid facts or usable evidence. Hidden facts and repeated facts may
be present; counts cannot be translated into benchmark coverage.

This evidence changes implementation priority: resolving explicit HTML header
links alone would not help any extracted cell in this small cohort. The three
filings instead contain tagged units, contexts and numeric facts. Evaluate a
mature Inline XBRL processor before writing a custom numeric/context parser.
The release still needs a visual/table-context path; tagged facts are not a
universal replacement for source reading or OCR.

## Prospective context contract

The [HTML table relationship algorithm](https://html.spec.whatwg.org/multipage/tables.html#header-and-data-cell-semantics)
distinguishes explicit header references and table-model associations. Preserve
the relationship and its source cells; a matching year elsewhere is insufficient.
Automatic visual associations must be labeled inferred, not explicit markup.

[XBRL 2.1 unit references and units](https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31%2Bcorrected-errata-2013-02-20.html#_4.8)
require resolved measures, including compound units. Retain namespace-qualified
concepts, entity, dimensions and contexts rather than interpreting an ID's name.
Its `decimals` describes accuracy, distinct from display scale.
[Inline XBRL nonFraction](https://www.xbrl.org/Specification/inlineXBRL-part1/REC-2013-11-18%2Berrata-2026-07-14/inlineXBRL-part1-REC-2013-11-18%2Bcorrected-errata-2026-07-14.html#sec-nonFractions)
provides transformation, sign and scale semantics; applying these twice would
change the financial value. Preserve raw markup and the normalized value separately.

[XBRL date guidance](https://www.xbrl.org/dates-in-xbrl/#periods-in-xbrl-xml-and-inline-xbrl)
explains that date-only instant/end dates represent the end of the day, whereas
start dates denote its beginning. Preserve both reported dates and normalized
boundaries, with period kind. A normalized next-day instant must not rewrite the
source's displayed fiscal endpoint.

The [SEC Frames API description](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes calendar-window aggregation. Its frame label is not proof of an issuer's
exact fiscal period or of availability at a historical decision time. Retain
actual fact dates and filing identity; do not invent availability timestamps.

Minimum future record: original bytes/hash, extraction version, fact/cell identity
and original locator, raw value, normalized decimal, unit, scale, sign, reported
accuracy, entity/concept/dimensions, period, and evidence references by role.
Distinguish explicit markup, inferred geometry and unresolved associations.
Retain nils, conflicts, unresolved references and validation diagnostics.

Acceptance must test wrong-duration headers, repeated headers across tables,
per-share scale exceptions, double scaling/sign, unresolved units, duplicate facts,
continuations and nils. Numeric equality alone cannot join a tagged fact to a
visible cell. Ingestion availability does not imply delivery or retention in an
agent context; frozen line-only runs receive no retroactive credit.

## Reproduction

Run `PYTHONPATH=. uv run python -P eval/scripts/inspect_context_markup.py OUTPUT.json`
with a new output path. The result binds script, extractor, baseline inventory
and original source bytes, and rechecks captured inputs before returning.
This diagnostic does not change extraction defaults, dependencies or tool results.
