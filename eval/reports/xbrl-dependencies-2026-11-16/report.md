# Real-filing dependency acquisition and offline load — 2026-11-16

The existing Old Dominion June 2025 filing now loads from a local taxonomy package
under OS network denial with its canonical SEC URI preserved. **It is not accepted
for fact extraction:** 12 of 504 occurrences fail missing SEC transformations.
This is an exposed development-source smoke, not a new benchmark result, cohort
replacement or promotion of a default tool.

## Local readiness and source selection

Read-only inspection found one missing relative schema in each existing tagged
filing: Cloudflare `cloud-20240930.xsd`, Old Dominion `odfl-20250630.xsd`, and Old
Dominion `odfl-20250930.xsd`. Root independently verified original hashes against
the prior context-markup inventory and parsed all three as strict XML. No HTML
base or XML Base changes their declared root schema location. Standard vocabulary
namespace URIs alone do not establish schema acquisition locations.

Old Dominion June was selected for this development smoke because its recorded
issuer delivery route was already successful. One new request to the corresponding
issuer schema returned 601,965 bytes, hash
`36a992b6fea7bc0e1648a0971ed0d7eafdc705edfa0930552086a4d87f77f08e`, with target namespace
`http://odfl.com/20250630`. The [entrypoint receipt](entrypoint-receipt.json) keeps
canonical SEC identity separate from actual issuer delivery. No blocked SEC filing
route was retried. Canonical remapping does not establish byte equality with an
independently downloaded SEC copy. The other two filings remain unbundled.

## Acquired graph and its limits

The [acquisition receipt](acquisition-receipt.json) preserves 24 documents and 2,417
reference occurrences, totaling 6,700,877 stored response bytes. Origins are one
receipted issuer schema, 12 exact bundled-cache files, and 11 network responses.
There are no redirects, retries, unresolved declared edges or import-namespace
mismatches in this run. The issuer schema embeds its linkbases. All original
payloads remain local under `runs/xbrl-dependency-acquisition-v1/closure`; they are
not rewritten or replaced by synthetic concepts.

The new `provenance.xbrl_dependencies` inventory respects expanded XML names,
inherited XML Base, original reference occurrences/fragments, and separate
canonical/delivery bases. It rejects DTDs, unsupported HTML base semantics,
non-HTTP(S) references and credentials. It inventories schema import/include/
redefine and XBRL schema/linkbase/role/arcrole/locator references. It does not infer
URLs from namespaces or claim that this set covers every extension mechanism.
Numeric element paths are positions in the strict parsed tree, not source byte
spans. Namespace matches do not validate schema contents or fragment targets.

The bounded acquisition script records failures and unavailable edges instead of
silently removing them. Its limits are 64 scheduled documents, 10 MiB per body and
100 MiB total observed bodies, with one overflow-detection byte; exhausted budgets
prevent further body reads. These bounds exclude HTTP headers and code/receipt
metadata. No automatic retry or alternative delivery route is attempted.

Review found and fixed malformed-XML queue termination, missing final code binding,
and unbounded cached-body reads. The initial successful acquisition used the
[retained executed driver](acquisition-driver-executed.txt); its hash matches that
receipt. The corrected script was replayed locally under OS network denial against
all saved bodies, preserving the same ordered document identities, hashes and all
2,417 edge records. Original receipts remain unchanged. Seven acquisition tests
cover malformed XML followed by a valid queued dependency, namespace mismatch,
conflicting routes, document/body limits and code mutation; six parser tests cover
reference semantics. Replay evidence is bound by [verification](verification.json).

## Exploratory package smoke

A standard taxonomy-package catalog maps the canonical filing and exact declared
dependency URL prefixes to local ZIP members. The package includes a byte-identical
copy of the original HTML, hash
`7ba28f8a0327378bb816e536b8f7861c233e394f9a041cce8e1d3101374c77b0`.
The [manifest](bundle-manifest.json) declares all 25 documents. Independent review
verified the ZIP hash, every member hash, and equality with the smoke's loaded
URI/path inventory. The package and raw bodies remain local development artifacts.
The retained [builder](package-experiment.txt) and [smoke driver](smoke-experiment.txt)
are exploratory transcripts with host-specific paths, not supported general CLIs.
Catalog rewrite rules are prefixes, not an exact-match security boundary.

Arelle 2.47.5 used the controlled environment, full DTS loading, validation enabled,
formula execution disabled, no added plugins, isolated cache/config and OS network
denial. The [summary](smoke-summary.json) retains all 12 errors and binds the full
local diagnostic record. Observed: 504 facts, 71 contexts, five units; 492 facts
have schema state 4 and 12 state 2. There are 78 duplicate warnings. API success
remains true despite the errors. No occurrence has been exported as accepted
evidence, and no rendered source-cell association or financial accuracy is claimed.

## Specific next dependency: SEC transforms

The errors name five formats in
`http://www.sec.gov/inlineXBRL/transformation/2015-08-31`: `boolballotbox` (4),
`stateprovnameen` (2), `exchnameen` (1), `entityfilercategoryen` (1), and `numwordsen`
(4). Eight errors are nonnumeric and four numeric. Installed wheel inventory and
[Arelle's tagged EDGAR documentation](https://github.com/Arelle/Arelle/blob/2.47.5/docs/source/plugins/popular/edgar.md)
confirm that pip/source installations omit EDGAR plugins.

Independent primary-source research identifies the narrow official
[EDGAR 26.3 transform module](https://github.com/Arelle/EDGAR/blob/4891c4c9889c77af247428ceff4fa7cc52d534ea/transform/__init__.py),
commit `4891c4c9889c77af247428ceff4fa7cc52d534ea`. Its directory is `transform/`
(singular), whereas older instructions show `transforms/`. It registers the needed
formats through `ModelManager.LoadCustomTransforms`, with one local `text2num.py`
helper. No plugin has been installed or executed yet. Next: separately acquire
pinned files/notices, explicitly allowlist that directory, repeat this same package
under network denial, and verify each affected value against original text.
Do not activate EDGAR validation/rendering or infer filing-rule compliance.

Research source hashes: module
`2296586f945ffd95ab37d3d4147c4e45f42ce4e5f397f61143e053208adefbf1`, helper
`6c9b26354320a2fb34fe380cdc71ff7f8d1cc712811e6b10c661e512f0383409`, repository license
`5537d4d10b76b81b6e8dfd8b644480a4b1efa332fbb0cdb61126c5be781ef7b4`.
These are remotely inspected bytes, not installed-plugin verification. Preserve
the repository CC0 notice, plugin Apache-2 metadata/SEC authorship notice and
helper MIT notice separately. Compatibility with Arelle 2.47.5 remains untested.

All 412 core tests and lint pass. Independent review cleared the acquisition
fixes and matched the final replay receipt hash; no paid inference or reserved
validation-document access occurred.
