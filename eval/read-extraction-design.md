# Read-response extraction metadata

The six-case FinanceBench comparison exposed a distinction between the 18,000
literal-text-character read cap and the 32,000 serialized-output-character context
budget. Full-document page diagnostics were repeated in every response; they
contributed 77.83% of saved read output characters and made required results too
large before optional retention ordering mattered. See the
[saved-response diagnosis](assessments/financebench-context-v1/response-size-report.md).

## Opt-in returned-page projection

`Sources(..., read_extraction_version="full-v1")` remains the default and returns
full extraction metadata. `read_extraction_version="pdf-returned-pages-v1"` opts
into a projection for `pdf-extraction-diagnostics-v2` metadata only. Legacy PDF,
HTML, unknown and missing metadata retain their prior response representation.
This is a Python source-tool option, not a new CLI flag or a production-default
change.

The projection changes only the response's `extraction` object. Its `pages` array
contains complete diagnostic entries for physical pages represented by the
**actually returned lines**, after the existing text cap. These entries describe
the full original pages, not only the excerpt. Source text, line numbers, page
locations, locators, continuation pointers, original/text hashes, search ranking,
read limits and context-retention policies remain unchanged.

Every other original extraction field remains intact: document page count,
global warning counts/samples and sample-truncation flags, empty-native-text page
list, package versions, OCR status, completeness uncertainty and warning text.
Warnings about omitted pages are not removed. Full diagnostics remain unchanged
in `sources.json`. A new `read_projection` descriptor records the selected mode,
scope, retained/omitted page counts and a reference to that source's full
`extraction` object. Its SHA-256 uses UTF-8 JSON with sorted keys,
`ensure_ascii=False`, `allow_nan=False`, and Python's default separators, matching
the repository's `canonical_hash` convention.

Recognized v2 metadata must have unique complete integer page identities. Each
returned line needs a valid original-page mapping and must fall within that
page's integer emitted-line interval. Malformed, missing or contradictory mappings
fail through the normal read-error path before lines become citation-visible.
Projection and subsequent response mutation cannot change the source metadata.

## Verification and boundaries

Five synthetic tests cover default/explicit-full serialized equality, unchanged
search/evidence fields, one/multiple returned pages, character-cap truncation,
omitted-page warning preservation, independent full-object hashing, copy isolation,
legacy/unknown metadata, malformed records and direct/tool error handling. Independent
review identified contradictory-page and null-mapping cases; both were fixed and
verified before acceptance.

No compact-mode cohort result is claimed yet. A separately frozen comparison must
bind this option and the new runtime, verify default-response compatibility against
saved responses, and keep the six-case denominator, existing annotations, questions,
read windows and context policies fixed. Historical experiment protocols remain
bound to their original runtime; do not rewrite them to accept the new code.

This projection is not a universal serialized-response size bound: global warning
metadata remains complete, and evidence text/escaping can still be large. It does
not repair retrieval gaps or validate financial answers. Default promotion and
full-agent benchmark inference remain gated on further evidence.
