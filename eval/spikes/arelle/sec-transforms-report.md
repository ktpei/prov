# Pinned SEC transforms on the exposed ODFL filing — 2026-11-16

A paired offline load now resolves all twelve missing SEC transformations in the
existing Old Dominion June 2025 filing. All 504 facts reach schema validation
state 4, with no model errors. Independent source-derived expectations verify the
twelve changed values; the other 492 occurrence records are identical between
conditions. This establishes the targeted transformation behavior, not general
financial accuracy, rendered evidence visibility or an accepted retrieval sidecar.

## Controlled change

The prior [dependency package](../../reports/xbrl-dependencies-2026-11-16/report.md)
remains byte-identical. Both fresh processes use controlled Arelle 2.47.5, the same
canonical entrypoint, all 25 declared document hashes, full DTS/validation,
formula execution disabled, isolated cache/config and OS network denial. Python
and installed distribution versions are recorded and compared. This is not a
complete hash inventory of every loaded runtime byte.

The candidate adds one explicitly allowlisted local plugin directory. The
[acquisition receipt](sec-transform-acquisition.json) binds unchanged official
files at EDGAR commit `4891c4c9889c77af247428ceff4fa7cc52d534ea` (release 26.3).
The plugin declares name `SEC Inline Transforms`, version **19.2**. These are
separate version identifiers. Before execution, the observer checks the pinned
module/helper/license hashes; afterward it verifies actual loaded hook/helper
origins, plugin inventories, registered SEC formats and unchanged bytes. The
control has no added plugin. EDGAR validation, rendering and XULE are not loaded.
The module registers 18 SEC formats; this filing exercises only five.

The parent snapshots all observation inputs, expectation bytes and its driver,
requires identical child input revisions, and rechecks them after both processes.
All original/parsed fact occurrences match canonical XML representations. Every
loaded document URI, archive member and hash matches the frozen package manifest.
Canonical XML is a parsed-tree representation, not original byte slices.

## Independent value expectations

A read-only reviewer derived the [twelve expectations](sec-transform-expectations.json)
from original HTML and pinned official function source before inspecting runtime
outputs. They cover:

| Format | Occurrences | Expected values |
| --- | ---: | --- |
| `boolballotbox` | 4 | One true quarterly-report flag; three false flags |
| `stateprovnameen` | 2 | Virginia → VA; North Carolina → NC |
| `exchnameen` | 1 | The Nasdaq Stock Market LLC → NASDAQ |
| `entityfilercategoryen` | 1 | Large accelerated filer → Large Accelerated Filer |
| `numwordsen` | 4 | “one” → numeric 1 |

All twelve have no continuation or excluded-content dependency. The four numeric
occurrences comprise two outer operating-segment facts and two nested
reportable-segment facts. Their descendant text is “one”; using direct text alone
would miss the outer values. The observer retains all four separate occurrences.
The runtime represents these numbers as Python integers, booleans as booleans and
codes/categories as strings. The independent expectations specified semantic kinds
rather than inferring the numeric Python class from runtime output.

## Duplicate groups and diagnostic qualification

The controlled pair preserves 78 existing duplicate groups and adds two complete,
consistent numeric groups for the now-valid segment counts. The candidate has
80 groups: 74 complete/consistent and six incomplete/consistent, with none marked
inconsistent by this Arelle API. These classifications do not establish economic
correctness or authorize collapsing source occurrences.

The controlled observer records 78 duplicate warnings in control and 80 in the
candidate, stable immediately after loading, after value inspection and after
grouping. The earlier exploratory candidate recorded 78 warnings. That separate-run
discrepancy remains unexplained; it is **not** established evidence of lazy
finalization. Installed source emits these warnings during validation; ordinary
post-load grouping does not emit them. Both historical and current records remain
available, and neither warning counts nor API success alone establishes acceptance.

## Reproduction and limits

Use the controlled runtime and the locally retained original package and plugin:

```sh
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/test_sec_transforms.py
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  /path/to/controlled/bin/python eval/spikes/arelle/compare_sec_transforms.py NEW_OUTPUT.json
```

Seven optional tests cover paired expectations, actual plugin registration,
within-run diagnostics, and rejection of changed unaffected values, context hashes,
transformed-value detail and duplicate occurrence loss. The comparison refuses to
overwrite output. Missing local assets or infrastructure failures abort rather than
becoming expected financial-validation outcomes. The source/plugin directories are
explicit development inputs; no project dependency or default tool was changed.

The next integration step is a full occurrence sidecar with original context/unit,
dimension/default provenance, continuation membership, duplicate classifications,
and explicit hidden/outside-table/unmapped dispositions. Existing timezone guards
and source-cell verification still need integration. No benchmark answers, reserved
validation documents or paid inference were accessed in this experiment.

## Primary sources and notices

[Arelle's 2.47.5 documentation](https://github.com/Arelle/Arelle/blob/2.47.5/docs/source/plugins/popular/edgar.md)
explains that pip/source distributions omit EDGAR plugins. The pinned
[official transform module](https://github.com/Arelle/EDGAR/blob/4891c4c9889c77af247428ceff4fa7cc52d534ea/transform/__init__.py)
uses the singular `transform/` directory; older activation instructions use a stale
plural path. The [helper](https://github.com/Arelle/EDGAR/blob/4891c4c9889c77af247428ceff4fa7cc52d534ea/transform/text2num.py)
retains its MIT notice. Repository CC0 licensing, plugin Apache-2 metadata and SEC
employee-authorship notice are preserved separately in the downloaded files; they
are not summarized as one blanket license.

The [retained paired result](sec-transform-result.json) matches independent
reproduction byte-for-byte; [verification metadata](sec-transform-verification.json)
binds the test source. All seven optional tests, 412 core tests and lint pass.
The independent reviewers are coding agents, not human financial validators.
