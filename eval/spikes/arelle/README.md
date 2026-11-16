# Arelle typed-context investigation — 2026-11-16

Candidate: `arelle-release==2.47.2`, an inspected version rather than a latest-release
claim. Its [tagged metadata](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/pyproject.toml)
declares Python >=3.11 and lists 3.13. The [core license](https://arelle.readthedocs.io/en/2.47.2/license.html)
is Apache-2.0; bundled libraries have separate notices. No project dependency,
default tool, source corpus or benchmark artifact has changed.

## Verified preflight

Installed in a clean temporary virtual environment on Python 3.13.2. The
[record](preflight-result.json) lists all 22 installed distributions, binds the
driver and synthetic fixture, and reproduces byte-for-byte in a fresh process.
The initial uv overlay inherited workspace packages; its separately retained
[overlay record](preflight-overlay-result.json) is not evidence of clean isolation.

An [independent audit](preflight-audit.json) reproduced the clean result exactly,
verified all clean distributions reside inside the virtual environment with system
packages disabled, and confirmed the overlay instead contains 71 distributions.

The fixture deliberately references a missing local schema. With full DTS loading,
validation enabled, formula execution disabled and the OS network-denial profile:

- `Session.run()` returns `true` and the model contains one fact occurrence.
- Diagnostics include `IOerror` and `ix11.12.1.2:missingReferences`.
- The spike rejects the document as dependency-incomplete and accepts zero facts.

This proves an important negative case: API success and parsed fact count do not
establish validated extraction. It does **not** yet test a valid taxonomy, scale/
sign normalization, dimensions, duplicates, continuations or source-to-cell links.
No issuer file was loaded and no taxonomy was downloaded during loading.

On this macOS host, create a separate environment and install the pinned package
before the denied-network phase. Invoke that environment's Python directly:

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/isolated/bin/python eval/spikes/arelle/preflight.py NEW_OUTPUT.json
```

The driver requires an `EPERM` result from a loopback connection probe. This checks
one observable path; the OS profile supplies the broader network restriction.
The profile is host-specific, not a portable isolation implementation. Package
versions are recorded, but loaded package/cache/taxonomy bytes are not yet fully
hashed. This is a spike, not a production acceptance gate.

## Research-backed implementation route

Use the supported [Session API](https://arelle.readthedocs.io/en/2.47.2/python_api/python_api.html)
and [RuntimeOptions](https://arelle.readthedocs.io/en/2.47.2/apidocs/arelle/arelle.RuntimeOptions.html)
in one fresh process per session. Retain `skipDTS=False`, `validate=True`,
`formulaAction="none"`, `validateDuplicateFacts="all"`, isolated cache/config,
and structured diagnostics. An explicit plugin allowlist is required; SEC
[transforms](https://arelle.readthedocs.io/en/2.47.2/plugins/popular/transforms_sec.html)
and [document-set support](https://arelle.readthedocs.io/en/2.47.2/plugins/popular/inline_xbrl_document_set.html)
are separate capabilities, not assumed enabled. Core validation is not EFM review.

The [WebCache implementation](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/arelle/WebCache.py)
uses local/bundled caches offline, while the
[socket helper](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/arelle/SocketUtils.py)
only warns when creating a socket in offline mode. Consequently the setting alone
does not enforce isolation. Bind every loaded dependency and report missing local
schemas/imports/linkbases rather than retrying online. Package installation is a
separate network-enabled setup action, never disguised as offline source loading.

The [fact/context API](https://arelle.readthedocs.io/en/2.47.2/apidocs/arelle/arelle.ModelInstanceObject.html)
provides resolved concepts, contexts, units and typed values. Preserve expanded
namespace names, entity, explicit/typed dimensions, raw period strings, normalized
boundaries, compound units, nil, decimals/precision, sign/scale and transformation.
Do not rescale `xValue`; do not call assembled `rawValue` untouched source bytes.
Retain every [duplicate occurrence](https://arelle.readthedocs.io/en/2.47.2/user_guides/fact_deduplication.html),
including inconsistent groups, with source provenance. Nil is not zero.

[ModelObject identity](https://raw.githubusercontent.com/Arelle/Arelle/2.47.2/arelle/ModelObject.py)
uses runtime indexes, so `objectId()` is not a durable locator. Preserve original
document hashes, unique element identity/structural paths, containing cell/table,
and continuation fragment chains. Parser recovery and visibility remain separate
acceptance concerns; a returned tree is not proof of faithful original structure.

## Positive fixture milestone

The [schema-resolved fixture](typed-values-report.md) now verifies five numeric
occurrences, exact Decimal values, nil versus zero, divided units, lexical and
normalized periods, and original source-cell ancestry. Six model-document hashes
are declared before loading and rechecked afterward. Eight optional acceptance
tests pass under OS network denial, alongside the 399-test core suite and lint.
This does not establish rendered visibility or general issuer extraction.

## Expanded guards

[The versioned guarded adapter](guarded-values-report.md) adds negative-scale and
explicit-timezone cases plus duplicate classifications. It rejects a verified
negative fractional-offset normalization defect in Arelle 2.47.2, retains warning
codes and quarantines inconsistent duplicate occurrences without dropping their
source records. Fifteen optional tests pass. The prior five-fact artifacts remain
unchanged; no issuer extraction or general timezone support is claimed.

## Candidate runtime comparison

The [controlled 2.47.5 comparison](candidate-comparison-report.md) holds Python and
all non-Arelle distribution versions at the baseline values. It uses two explicit
temporary version-gate amendments, verifies import origins and compares complete
case records except independently checked adapter hashes. Independent and retained runs
pass the same 15 tests and 10 scenarios; 2.47.5 still needs the timezone guard.
No frozen file or default tool is changed.

## Dimensional scope observation

The [separate dimensional fixture](dimensions/README.md) observes 13 occurrences
in 10 contexts and verifies explicit/typed members, residual scenario content and
namespace-alias equality. Six optional tests pass under denied-network execution.
It has no hypercubes or default relationships, so this is context identity coverage,
not taxonomy applicability or general extraction.
A [separate applicability matrix](applicability/README.md) now checks default and
closed-cube relationships with 14 cases, including nine expected validation
rejections despite schema-valid facts. Seven optional tests pass. These fixtures
remain separate from the guarded extraction path.

## First real-filing package load

The [dependency acquisition experiment](../../reports/xbrl-dependencies-2026-11-16/report.md)
now loads the existing ODFL June original and 24 declared dependencies under OS
network denial. The initial run rejects 12 missing SEC transforms among 504 facts.
The [subsequent pinned-plugin comparison](sec-transforms-report.md) resolves those
twelve values against independent expectations and preserves the other 492 records.
All 504 facts pass schema validation; full occurrence/source-cell evidence acceptance
remains the next integration step.

## Remaining acceptance work

1. Add separately versioned fixtures beyond the frozen five-fact
   positive path; retain the same denied-network execution and dependency checks.
2. Cover sign/scale/accuracy, nil/zero, divided units, namespace aliases, periods,
   explicit/typed dimensions, unknown concepts/transforms, duplicates and broken
   continuations. Every occurrence must be exported or explicitly rejected.
3. Hash loaded dependencies and preserve diagnostics; quarantine parser recovery
   or unresolved references instead of silently accepting partial models.
4. Round-trip accepted source locators and verify visible-cell associations with
   local rendering. Hidden/detached/ambiguous facts get explicit dispositions.
5. Integrate the verified ODFL package/plugin smoke into a full occurrence sidecar,
   preserving the initial rejected run and paired comparison. Acquisition stays
   separate from denied-network loading. The other two tagged filings remain
   unbundled; preserve them and the untagged release disposition. This remains
   development smoke testing, not prospective benchmark improvement.

The independent research agent checked primary documentation and tagged code;
root executed the negative preflight. Financial correctness, benchmark-role
equivalence, evidence delivery and answer accuracy remain separate questions.
