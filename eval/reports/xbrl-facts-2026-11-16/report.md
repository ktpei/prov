# Experimental typed fact export — 2026-11-16

The existing exposed ODFL June 2025 filing now has one integrated typed record:
504 facts, 71 contexts, five units, 21 taxonomy defaults and 80 duplicate groups.
All facts remain bound to original bytes and validated runtime identities. This
is development ingestion evidence, not measured financial answer improvement.

## Representation and binding

[facts.json](facts.json) preserves Decimal strings (including signed zero), integer
strings, booleans, nil, strings, namespace-qualified enumeration members, partial
dates and complete parsed temporal components. Numeric values already incorporate
transform, sign and scale; they are never rescaled. Date-only context end/instant
boundaries advance one day; date-only fact values do not. Original source bytes
remain authoritative when runtime precision or assembly differs from lexical text.

Reported dimensions remain separate from taxonomy defaults. Each default carries
its relationship arc, dependency URI/hash and location. This does not infer a
fact's effective default or consolidated scope. All original context/unit XML
identities round-trip. Source geometry is rebuilt from original bytes and the
hash-bound table sidecar before serialization; altered spans, hashes, identifiers,
paths and cell joins reject. Runtime annotations from the prior occurrence report
are discarded in favor of rebuilt geometry.

There are 446 Decimal, 38 string, ten boolean, four integer, two nil, one enumeration
set, one gMonthDay, one gYear and one date-time parsed values. The 420 cell-mapped,
77 outside-table and seven hidden dispositions remain distinct. All 80 actual
duplicate groups are consistent; an injected inconsistent group checks quarantine
without dropping facts. That synthetic injection is not an observed issuer error.

## Independent expectations and verification

The optional tests assert source-derived values before using the export as an
oracle: cash 24,057 with scale 3 becomes 24,057,000; repurchase settlement 200.0
with scale 6 becomes 200,000,000; nonoperating expense 1,357 with sign minus and
scale 3 becomes -1,357,000. An em dash becomes zero only through its declared
fixed-zero transform. Two empty nil facts stay nil. Tests also independently bind
the fiscal-year-end month/day, year, document date and executive enumeration.

The fixed driver pins Arelle 2.47.5, Python and all 22 distributions, the sole SEC
transform plugin and helper origins, every loaded dependency, original bytes,
prior runtime fingerprints and source occurrence artifact. Inputs are rechecked
after export. Acquisition is separate; execution uses OS-denied networking.

Run the optional driver with the controlled local environment:

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /tmp/prov-finance-loop/arelle-2.47.5-controlled/bin/python \
  -m eval.scripts.build_xbrl_fact_report /tmp/typed-facts-new.json
```

Independent review reproduced the export byte-for-byte: SHA-256
`11462530f838361ad867201079ea6252f9c02703f9d4e20ec37a080220ee7986`. All 14 input hashes were verified.
Seven optional integration/type tests pass, as do 431 core tests and lint.
Arelle emits a Python ResourceWarning concerning its local ZIP handle during test
cleanup; this remains disclosed. The filing has zero validation errors and 80
retained duplicate warnings. Financial correctness, rendered visibility, evidence
delivery and prospective benchmark gains remain unverified. No default tool or
retrieval policy is changed; reserved evaluation documents remain closed.
