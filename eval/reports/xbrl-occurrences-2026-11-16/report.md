# Original-source occurrence bridge — 2026-11-16

The existing ODFL June filing now has one explicit original-source record for each
of its 504 Inline XBRL facts. All match the frozen validated runtime observation by
ID, canonical source representation, expanded concept, context and unit. This is a
source-location sidecar, not a financial-value export or browser visibility test.

| Original source disposition | Numeric | Nonnumeric | Total |
| --- | ---: | ---: | ---: |
| Exact nearest-cell join, not explicitly hidden | 406 | 14 | 420 |
| Outside tables, not explicitly hidden | 44 | 33 | 77 |
| Inside `ix:hidden`, outside tables | 2 | 5 | 7 |
| Table ancestor without cell / unmapped cell | 0 | 0 | 0 |
| Total | 452 | 52 | 504 |

The 420 joins cover 412 distinct cells across 15 tables. Many-to-one joins are
preserved. No-cell occurrences are not failures: six facts contain descendant
tables while having no containing cell themselves. They are not assigned to an
arbitrary descendant cell. Hidden facts remain in the denominator and retain
explicit hiding evidence; “not explicitly hidden” does not mean rendered visible.

## Location and identity contract

`provenance.xbrl_occurrences` uses strict namespace-aware XML parsing to obtain
actual original byte positions and ancestry. A separate HTML start-event stream
from the same UTF-8/ASCII bytes supplies the exact line/column convention used by
the existing table extractor. All 14,413 element starts must agree on byte position,
expanded name and ID. Line numbers start at one; columns start at zero and count
Unicode characters. LF-only line counting preserves BOM, CRLF and bare-CR behavior
rather than incorrectly substituting Expat's normalized line/column coordinates.

Every fact and continuation has a numeric structural element path and an exact
half-open `[byte_start, byte_end)` range with SHA-256 of those original bytes.
The range includes nested source elements and excludes following sibling/tail
content. These are neither normalized values nor continuation-expanded text.
Ordinary and self-closing end positions are handled separately; a quoted `>` in
a start tag cannot truncate the range.

The table join uses exact nearest-cell and nearest-table positions, with table
identity agreement, unique sidecar IDs/positions and the same original hash. It
never matches numbers, normalized text or guessed headers. The sidecar artifact's
own bytes/hash/version are retained. The saved table sidecar is **v2**, with 24
tables and 4,084 cells; it is not relabeled v3. Independent inspection found v3's
`tables` array identical for this original, but version/limitations remain distinct.

Start-event agreement alone cannot establish HTML ancestry. The implementation
rejects nested/implicitly closed cells and rows, unsupported row-group nesting,
foreign or prefixed XHTML geometry, template semantics, markup inside raw-text
contexts and unsupported Inline XBRL namespaces/tuples. Strict XML failure, DTDs,
duplicate IDs and ambiguous continuation links also reject the inventory. An
otherwise supported source whose cell is absent from the supplied sidecar gets
`cell_unmapped`; no text-matching fallback repairs it.

## Nesting and continuation relations

All 136 facts with fact ancestors retain those ancestor IDs. Twenty fact elements
contain other facts; the records remain independent occurrences. Six continuation
elements are retained separately from facts, each directly referenced once in this
filing. No continuation has its own `continuedAt`; no `ix:exclude` occurs here.

Ninety-five distinct facts occur inside continuation subtrees. Physical containment
is separate from assembly links: one continuation is physically inside another,
but their reference chains do not link them. Ordered fragment locators preserve
`continuedAt` chains without assigning the fragment to the originating fact's cell.
Missing/wrong-type/cyclic/shared targets and ancestor/descendant members of the
same chain reject. Supported link sources are `ix:nonNumeric` and
`ix:continuation`; numeric and footnote continuation sources are explicitly
unsupported, and ordinary HTML attributes cannot create continuation links. Orphan or `ix:hidden` continuation elements receive explicit
issue flags instead of being confused with legitimate hidden facts.

## Runtime association and reproduction

The fixed [report builder](../../scripts/build_xbrl_occurrence_report.py) binds the
original, saved v2 table sidecar, implementation files and frozen SEC-transform
observation (`6e68cad69b919b0f700f27d8f6fc7a2a416018ef900e55c0f0b01a7747ab2230`).
For all 504 facts, an independent strict XML parse reproduces the runtime source
fingerprint and verifies concept/context/unit references and schema state. The
raw-byte hash and runtime canonical-tree hash use different representations and
are not equated. Inputs are rechecked after report generation.

Generic source-only output uses the project's normal environment:

```sh
uv run python -m provenance.xbrl_occurrences ORIGINAL.html TABLES.json NEW_OUTPUT.json
```

The fixed runtime-binding report also needs lxml from the controlled Arelle
candidate environment, but does not itself load Arelle, execute plugins or access
the network:

```sh
/path/to/controlled/bin/python -m eval.scripts.build_xbrl_occurrence_report NEW_OUTPUT.json
```

Both commands refuse output overwrites. Twelve new core tests cover exact and
many-to-one joins, nesting, hidden/orphan dispositions, BOM/multibyte/CRLF/bare-CR
positions, quoted delimiters, self-closing spans, continuation errors, geometry
mismatches, missing cells, sidecar hash/position ambiguity and duplicate IDs/DTDs.

The next integration step is to combine these source records with complete typed
values, raw/normalized periods, dimensions, units and duplicate dispositions in a
single optional fact sidecar. The current artifact does not expose a retrieval
API, infer headers, establish financial correctness, or prove computed visibility.
Historical benchmark scores, frozen sidecars and default tools remain unchanged.

The [retained occurrence record](occurrences.json) reproduces byte-for-byte in
independent review. [Verification metadata](verification.json) binds the tests;
all 424 core tests and lint pass. Reviewers independently checked every fact and
continuation byte span and all 420 joins. They are coding agents, not financial
validators. No paid inference or closed validation-source access occurred.
