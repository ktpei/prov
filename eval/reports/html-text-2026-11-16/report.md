# Versioned HTML text ingestion diagnostics

The opt-in text extractor was exercised under clean commit `1424916` on two
previously inspected Cloudflare development originals. The
[initial diagnostics](diagnostics.json) record original/text identities, parser
metadata and a new local corpus manifest. All original-corpus files remained
byte-identical, and both legacy extracted-text hashes replayed exactly. No model
calls, new assessment questions, or holdout inference occurred.

The release produced 402 lines (legacy 403): navigation labels gained boundaries
and a hidden email-confirmation heading was omitted. The filing initially produced
1,721 lines (legacy 1,719), with 41 changed line groups. Differences include block
and date boundaries; this does not establish complete or financially correct
extraction. Review found extra separator-only lines caused by empty block cells.
The original diagnostic corpus is retained; a targeted regression fix prevents
whitespace-only cell content from creating separators before the first real text.

Synthetic coverage includes hidden attributes/styles/templates, inherited hiding,
optional cell/row closures, nested tables, self-closing syntax, malformed hidden
wrappers, block-separated numbers, full heading unit context, visible XBRL, zero,
parentheses, explicit version metadata, legacy replay, and corpus reuse rejection.
External CSS, conflicting styles, descendant visibility overrides and browser-level
rendered completeness remain unresolved. The new six-document assessment is not
acquired, annotated or run by this diagnostic.

Independent coding-agent review found no numeric or unit omission in these two
initial outputs: after removing whitespace and separators, all content-bearing
filing lines matched legacy order. Original markup supports the release's hidden
heading omission. These particular documents do not demonstrate removal of hidden
numeric content; that protection is supported by synthetic regressions. This is
bounded compatibility review, not human adjudication or rendered-page verification.

The [final clean rebuild](final-check.json), under `8aa5cec`, yields 380 release
lines and 1,718 filing lines, with zero separator-only lines. This removes empty
layout rows as well as the newly noticed separator artifacts. Content-bearing
lines match the initial v2 output in order after removing whitespace/separators;
this comparison does not assert that whitespace is semantically irrelevant.
The old corpus remains byte-identical. Local initial and final corpora are kept
separately at `runs/cloudflare-html-text-v2` and `runs/cloudflare-html-text-v2-final`.
