# Dimensional context identity observation — 2026-11-16

This optional fixed-fixture observation uses controlled Arelle 2.47.5 under OS
network denial. It is not a general extraction adapter and does not promote any
default tool or claim financial accuracy. Prior typed-value adapters and records
remain unchanged.

The fixture contains 13 numeric occurrences in 10 contexts. Nine Assets occurrences
share the same concept, amount (-12000), unit and period, but include distinct
explicit regions, typed account codes, residual budget/actual scenario content,
and an unqualified context. Six optional acceptance tests require:

- Expanded explicit dimension/member names distinguish North from South; changing
  only namespace prefixes preserves identity.
- Typed scalar account codes A001 and A002 remain distinct; repeated A001 contexts
  form a duplicate group. These domain elements are simple strings with no attributes.
- Non-dimensional scenario content survives alongside reported dimensions.
- All 13 occurrences remain present. Exactly two duplicate groups are detected:
  North/prefix-alias and A001/repeated-A001. Duplicate warnings are retained.
- Each complete context, dimension element, typed domain element and residual
  element resolves back to the strict original XML tree and has equal canonical
  serialization. Canonical XML is a tree representation, not original byte slices
  or a universal semantic identity key. Original document hashes remain authoritative.
- Exactly eight source/schema documents match a declared pre-load manifest and
  remain unchanged afterward; full DTS loading and validation produce no errors.

The taxonomy declares dimensions but deliberately contains no hypercubes, domain
networks or defaults. In Arelle 2.47.5, facts with no applicable hypercube relations
pass `isFactDimensionallyValid`; this fixture therefore proves context observation
and equality behavior, **not member usability or hypercube applicability**.
`taxonomy_dimension_defaults` is explicitly empty. Default lookup, default-domain
membership, closed/open hypercubes and segment/scenario applicability remain future
acceptance work. Complex typed domains, QName-valued typed content, typed attributes,
continuations, source rendering and issuer extraction are also unverified.

The observation preserves source scope but does not independently recheck numeric
normalization, date boundaries or source-cell ancestry. Those checks exist in the
separate frozen guarded fixture; a future integrated adapter must combine them.
The package version is enforced; this driver does not independently enforce the
whole environment inventory. Run it in the previously verified
[controlled candidate environment](../candidate-comparison-report.md).

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/dimensions/test_contexts.py
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/dimensions/probe.py NEW_OUTPUT.json
```

The loopback probe must return EPERM; the OS profile provides the broader network
restriction. Installation is separate from loading. The output records driver and
manifest hashes, loaded document hashes, diagnostics, source representations,
reported dimensions and occurrence/group inventories. The command refuses to
overwrite an existing result.

## Research implications

[Dimensions 1.0 §§2.7 and 3.1](https://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18%2Bcorrected-errata-2012-01-25-clean.html)
separates default relationships from domain membership and permits primary items
without dimensional relationship sets. A default must not be reported explicitly;
it is not automatically an economic total. The next applicability fixture should
connect a primary item, hypercube, explicit axis, domain and default member with
all relevant relationships, then reject explicitly reported defaults and invalid
members. These are prospective checks, not completed coverage.

[Arelle 2.47.5 context APIs](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/ModelInstanceObject.py#L1197-L1259)
separate `qnameDims` from `qnameDimensionDefaults`. In this release,
`dimMemberQname(..., includeDefaults=False)` can nevertheless return a default via
`dimValue`; use reported-map membership instead of that flag. Its dimensional
context comparison ignores explicit dimension placement but retains ordered
residual content per container. Runtime hashes are not durable identifiers.
[Dimensional validation](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/ValidateXbrlDimensions.py#L397-L424)
explains why the declaration-only fixture passes without a hypercube network.

The [xBRL-XML mapping §§2.1.1–2.1.3](https://www.xbrl.org/Specification/xbrl-xml/REC-2021-10-13%2Berrata-2023-04-19/xbrl-xml-REC-2021-10-13%2Bcorrected-errata-2023-04-19.html)
excludes residual context content from the OIM-compatible subset. Preserve it
rather than silently flattening it away; this observation does not claim OIM
conformance. Schema-aware typed equality also needs separate integer/string,
nil/empty, QName-valued and attribute-bearing tests before broader support.

## Verification

Six optional tests and the 399-test core suite pass; lint passes. An independent
read-only reviewer verified all 21 canonical source records, all eight loaded
hashes, occurrence/context counts and the two duplicate groups under OS network
denial. The reviewer also confirmed all 26 prior top-level spike files were
unchanged. No source documents or benchmark answers were accessed for this work.
