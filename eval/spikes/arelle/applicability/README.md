# Default members and dimensional applicability — 2026-11-16

This synthetic matrix tests a financial-context acceptance boundary that schema
validation alone misses. All 14 cases produce API success and one schema-valid
Assets fact worth 100, but full dimensional validation rejects nine. A pipeline
must check validation diagnostics and model errors before accepting the occurrence.
The matrix is an optional investigation, not a general extraction adapter or a
claim of financial correctness.

## Taxonomy and independent expectations

One standard link-role network connects Assets to a closed RegionCube scoped to
`segment`, then to RegionAxis and RegionDomain. AllRegions and North are usable
domain members; South's sole incoming membership relationship is unusable.
AllRegions is the default. East is declared but outside the domain; ExtraAxis is
declared but outside the cube. Each case loads a fresh model/process so taxonomy
changes cannot reuse cached default or usability decisions.

| Case | Expected disposition |
| --- | --- |
| Omitted RegionAxis | Accept using the usable default |
| North in segment | Accept |
| Explicit AllRegions default | Reject: `DefaultValueUsedInInstanceError` |
| Unusable South | Reject: `PrimaryItemDimensionallyInvalidError` |
| Undeclared member | Reject: `ExplicitMemberUndefinedQNameError` (also primary-item error observed) |
| North in scenario | Accept: the segment-scoped cube uses its default |
| ExtraAxis in segment | Reject: closed cube excludes the additional axis |
| Omitted axis, default relationship removed | Reject: required dimension has no value |
| Default still declared but removed from domain | Reject: default-map presence does not establish usability |
| North in scenario, default removed | Reject: no segment value/default |
| Declared East outside domain | Reject: member is not usable in the applicable domain |
| ExtraAxis only in scenario | Accept: outside this segment-scoped cube's check |
| Residual budget content in segment | Reject: closed cube excludes residual content |
| Residual budget content in scenario | Accept: outside this cube's check |

All rejections other than explicit-default and undefined-member errors require
`PrimaryItemDimensionallyInvalidError`. Tests require the named error and its Assets occurrence
reference, allowing additional diagnostics. Reported dimensions and their container
remain separate from the taxonomy default map. In particular, scenario's North
must not be mislabeled as this segment cube's effective member. The matrix does not
export an effective-member interpretation.

## Evidence and reproduction

Full DTS loading, formula execution disabled, isolated cache and actual OS network
denial apply to each case. The pre-load baseline manifest binds three authored
files and six bundled schemas. Deterministic, named mutations produce separately
hashed candidate documents; exactly nine loaded model documents must match those
hashes. All loaded bytes, baseline files, manifest and driver are rechecked. The parent
snapshots all baseline documents, manifest and driver across the full matrix and
requires every child to report identical baseline/revision hashes.
Structured errors retain references and source lines; paths are normalized only
before the URI fragment so XPointer fragments remain intact. Invalid cases remain
in the result instead of disappearing from the denominator.

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/applicability/test_matrix.py
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/applicability/matrix.py NEW_OUTPUT.json
```

Use the [controlled 2.47.5 environment](../candidate-comparison-report.md).
The driver enforces Arelle's version but does not independently pin the complete
runtime inventory. It requires an EPERM loopback result; the OS profile supplies
broader network denial. Infrastructure failures/timeouts abort the matrix instead
of producing an ordinary validation disposition; they must not be counted as
expected invalid cases. Outputs refuse overwriting.

Seven optional tests cover all fourteen cases, required errors/fact attribution,
reported/default separation, context placement, fact inventory and loaded document
counts, plus rejection of a mismatched child revision and between-child input change. The matrix does not combine source-cell round-tripping, timezone guards,
transformations or duplicate quarantine. Those remain separate existing fixtures.
Multiple ELRs, targetRole transitions, alternate domain paths, `notAll`, complex
typed domains and actual issuer documents remain untested. Existing benchmark
results, reserved validation sources and default tools are unchanged.

## Research basis

[Dimensions 1.0 §§2.7, 3.1.3–3.1.4](https://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18%2Bcorrected-errata-2012-01-25-clean.html)
separates default relationships from domain membership, requires inferred defaults
to remain unreported and makes the selected context container significant.
Closed-cube restrictions apply to that container, not indiscriminately to the
whole context. A default is not inherently an economic consolidated total.

[Arelle 2.47.5 `checkFactElrHcs`](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/ValidateXbrlDimensions.py#L491-L557)
selects the relationship's container, consults defaults for missing axes, checks
member usability and rejects additional dimensions/content for a closed cube.
[`checkContext`](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/ValidateXbrlDimensions.py#L302)
separately rejects explicit defaults and undefined members. An independent research
agent verified the installed module matches the tagged source and supplied these
expectations before the matrix was finalized. Neither a flat dimension map nor
`context.dimValue(axis)` is a hypercube-specific effective-scope API.

## Retained verification and next integration step

The [retained result](result.json) matches independent reproduction exactly;
[verification metadata](verification.json) binds the seven-test suite. All 399
core tests and lint pass. Review identified and resolved a whole-matrix binding
gap before retention; the parent now checks snapshots and each child revision.
No earlier frozen fixture or result changed.

A separate read-only readiness review found missing relative issuer schemas in
all three already-exposed tagged filings: Cloudflare's `cloud-20240930.xsd` and
Old Dominion's `odfl-20250630.xsd` / `odfl-20250930.xsd`. Root verified the original
hashes and strict XML parsing independently. No issuer file has been loaded by
Arelle. The next integration step is an explicit dependency-readiness record and
one bounded dependency bundle, followed by a denied-network source smoke. Namespace
URIs alone do not establish dependency download URLs or closure. Acquisition must
remain separate from extraction, preserving failures and canonical/delivery bases.
