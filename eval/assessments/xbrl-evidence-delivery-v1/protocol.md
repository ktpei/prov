# Typed-fact evidence delivery — development protocol v1

Status: baseline diagnostic completed; typed-reader implementation and question
assessment pending. This is the already exposed ODFL June 2025 issuer copy. It is
not an unseen test set. The six reserved FinanceBench documents remain closed.

## Baseline diagnostic

`eval/scripts/audit_xbrl_table_delivery.py` gives the existing `TableSources` reader
the exact nearest-cell row for each mapped fact. It does not search or infer rows.
It deduplicates identical table/row requests, retains every full response, and
checks whether the mapped cell identity appears. Before execution, the complete
regenerated table sidecar must equal the table artifact bound to the typed export.
All source/runtime inputs are hashed and rechecked after execution.

[table-audit.json](table-audit.json) covers all 504 facts. All 420 mapped fact occurrences, across 412 distinct cells, are
represented in 139 unique reads; 84 facts have no mapped cell (77 outside-table,
seven explicitly hidden). Both nil facts are hidden, rather than empty visible
cells lost by the reader. No mapped-cell omission or read error occurred. The
responses range from 1,431 to 7,989 serialized Unicode characters, totaling 654,292
across unique reads. These are character counts, not token costs.

This tests a location-assisted delivery ceiling, not retrieval or answer accuracy.
A returned cell does not prove delivery of its typed value, full period, unit,
entity, dimensions or footnotes. Conversely, an unmapped fact is not a retrieval
failure: narrative reading may supply equivalent financial evidence. Table and
fact representations may complement each other; no ranking promotion follows.

Independent review reproduced the audit byte-for-byte (SHA-256
`b68ec275a824af7bbd8672f9298bbb80180bdb341a442b7573f8eaa7b3ab2639`).
All 504 cases and response hashes/source identities were verified. Multiplicity
matters: `table-9-r23-c0` contains six occurrences spanning two contexts and
multiple concepts/units. Returning that one cell is not six independently complete
financial evidence packets.

Source review also found a concrete context gap: the row-34 read in `table-10`
returns rows 0–4, 33 and 34, including “Basic” and “Diluted,” but omits row 32,
“Earnings per share:”. The recorded response verifies this omission. Consequently,
occurrence presence and parent-label completeness need separate checks. No score
is retroactively changed; question-specific sufficiency has not yet been graded.

## Required reader contract before question assessment

The experimental reader must be opt-in and consume authenticated, validated
artifacts. Preserve source provenance: these bytes were acquired from the issuer;
the canonical SEC URI identifies the filing but does not establish SEC byte
equivalence or a historical availability timestamp. Availability metadata must
remain attached and respect existing temporal access policy.

Read explicit occurrence identities with bounded, atomic responses. Preserve
exact tagged values, nil versus zero, resolved concept/type, context entity,
reported and normalized periods, units, reported dimensions, source locators,
source disposition and duplicate membership. No automatic numeric rescaling,
deduplication, hidden-to-visible conversion or inferred consolidation. Keep
source-bound schema validation distinct from financial correctness. Taxonomy
defaults are not reported dimensions or per-fact scope. Any omitted long lexical
or XML field needs an explicit disposition and a separately bounded retrieval
route; silently truncated evidence cannot receive complete-delivery credit.

Search/discovery and reads must have separate traces and measures. A successful
exact-ID read is not successful natural-language retrieval. If a selected fact
has an inconsistent duplicate group, retain the group/conflict indication and
quarantine; do not choose a convenient representative.

## Evaluation boundaries

Before running a candidate on question cases, freeze questions, source-derived
requirements, acceptable alternatives, implementation hashes and response budget.
Score mechanically replayable evidence delivery separately from human-reviewed
financial sufficiency and answer quality. Include absent/unsupported requirements,
period/dimension near misses, nil/zero, duplicate and availability controls.
Report all cases and all failures. Do not use this exposed filing to claim
unseen-source improvement. No model calls are needed for the first delivery gate.

[Eight proposed cases and failure controls](case-plan.md) make the next gate
concrete. Their role alternatives are not yet frozen grading labels.
