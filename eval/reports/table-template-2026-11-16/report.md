# Inert-template extraction repair — 2026-11-16

Synthetic inspection found that `native-html-tables-v2` treats ordinary HTML
`template` contents as visible table evidence. A cell containing visible `42`
and template text `999` becomes `42999`; template captions can fabricate units,
and a template table consumes a table ID. Template row/cell fragments can also
modify an outer table's geometry. These are extraction defects, not measured
financial-question failures in the frozen corpora.

The [HTML Standard](https://html.spec.whatwg.org/multipage/scripting.html#the-template-element)
places ordinary template contents in a separate inert document fragment. Simply
adding `template` to the old suppressed-tag set does not isolate geometry: the
old blocked-row/cell path can still mutate the parent table.

The opt-in `native-html-tables-v3` isolates template subtrees before any table,
row, cell, caption or hidden-scope handling. Nested template contents cannot
create table IDs or occupy columns. Unfinished, unmatched and self-closing
templates are rejected. Declarative shadow DOM templates are rejected explicitly,
since their rendering requires different handling. Independent review also found
that literal template-like markup inside `textarea` could escape the depth counter.
V3 now rejects RCDATA/raw-text contexts inside templates and outside already
suppressed content, except `script`/`style`, which the underlying parser tokenizes
correctly. This also prevents the inverse failure: interpreting literal template
markup in visible textarea content and dropping its digits. Eight contexts in
both directions and supported script/style/head-title controls have regressions. External CSS, scripting,
browser tree repair and semantic header association remain unresolved.

```sh
uv run python -m provenance.table_structure input.html output.json --version native-html-tables-v3
```

Seven new tests cover whole-table suppression, nested fragments and parent geometry,
caption/number preservation, hidden-scope isolation, malformed/shadow templates,
and CLI selection. Lint and all 254 tests pass. [Compatibility evidence](compatibility.json)
compares four default-v2 sidecars against committed baseline `72d1fba`: both existing
Cloudflare HTML sources and both acquired Old Dominion copies replay exactly.
No financial questions, model calls or new retrieval evaluations were run.

The initial repair was standalone. A subsequent integration adds explicit sidecar
selection to `TableSources` and assessment run-protocol v4, including exact replay
and annotation-geometry checks in the grader. Earlier protocols and default tools
still use v2. Five integration tests pass, bringing the full suite to 259; lint
passes. [Runtime compatibility](runtime-compatibility.json) replays all 36 recorded
search/read responses across the three prior search policies exactly.

No new real assessment or default promotion has occurred. Using v3 for the
six-filing assessment requires a new committed runtime/protocol amendment and
version-matching annotations. Existing gates and receipts remain historical
snapshots; current code cannot run under the earlier frozen runtime digest.
