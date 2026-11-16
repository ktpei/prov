# Header-association design review

Read-only independent audit by `/root/masked_packet_review`, 2026-11-16. Existing
24 structure tests and 16 table-tool tests passed. The reviewer reproduced the
synthetic issues below; no production behavior was changed.

Explicit associations are deferred for the current four-source cohort because
the inventory finds no `th`, `headers` or `scope` on extracted cells. This does not
remove the longer-term need for visual header interpretation.

A resolver over current v2/v3 sidecars alone would lack necessary information:

- Document-wide IDs on non-cell, suppressed and hidden-table elements are lost.
- Rowgroups, colgroups and nested-table ancestry are not retained.
- Duplicate attributes become last-value wins, and `headers.split()` uses a
  broader whitespace set than HTML's ASCII separators.
- Current locations identify start-tag character positions, not exact byte spans.
- Normalized cell text loses child structure; read windows omit hidden/empty cells.
- Visible self-closing cell markup, duplicate ID attributes and group-crossing
  rowspans can be interpreted differently from a browser table tree.

The [HTML relationship algorithm](https://html.spec.whatwg.org/multipage/tables.html#header-and-data-cell-semantics)
requires document-aware identity and table-model semantics. Explicit `headers`
must not silently fall back to inferred associations; scope is not unrestricted
row/column overlap. The [HTML parser rules](https://html.spec.whatwg.org/multipage/parsing.html#attribute-name-state)
also matter for duplicate attributes and malformed markup. A future extractor
must implement or explicitly reject unsupported behavior rather than claiming
browser equivalence.

Use a new opt-in structural version retaining raw attributes, presence-versus-empty,
ID occurrences, table ancestry and groups. Bind a separate association result to
original bytes and extraction/algorithm versions. Record target, header, basis,
source location and unresolved reason. Distinguish no declaration, explicit empty
declaration and unsupported/ambiguous markup. Do not infer financial meaning from
structural association alone.

Tests must cover duplicate IDs outside cells and across nested/hidden tables;
empty, missing and self-referencing targets; NBSP and case-sensitive IDs; spanning
cells and intervening data; groups and early footers; templates and raw-text;
headers outside read windows; response limits; and exact legacy response replay.
Association availability does not deliver header text: a future read policy must
return the actual referenced cells and preserve evidence accounting.
