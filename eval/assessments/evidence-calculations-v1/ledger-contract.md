# Calculation ledger v1 contract freeze

2026-11-16 · baseline `220e8c0` · supplement to [H2 protocol](protocol.md)

Implement a small in-process ledger, with no provider calls or new dependency.
The internal constructor takes a trusted admission snapshot, not model arguments.
It structurally validates and copies that snapshot; it cannot independently prove
financial semantics from arbitrary caller metadata. H2 uses synthetic admission;
H3 must supply real reader authorization, semantic admission and model visibility.

## Admission snapshot

Exact outer fields: `run_id`, `admission_policy`, `evidence` (list). Evidence records
contain exactly `run_id`, `evidence_id`, `kind`, `source`, `reader`, `read_receipt`,
`delivery`, `quarantined`, `support`, and `attributes`. No accepted flag is an
authority. Require same run, unique IDs, complete delivery, no quarantine, a
text_span/table_cell_group/xbrl_occurrence kind, nonempty IDs/versions/locators,
and lowercase SHA-256 strings for original/extracted/receipt bytes.

Source fields: `id`, `original_sha256`, `extracted_sha256`; reader: `name`, `version`;
read receipt: `id`, `sha256`. Support is a nonempty map of local support IDs to
`{role, locator, content}` with exact nonempty returned text. This is the small
H2 boundary; H3 may construct it from larger immutable reader records only after
validating complete support delivery. Receipt/source hashes here bind identities,
not cryptographic authenticity or financial truth.

Each attribute has exactly `state`, `value`, `origin`, `support_refs`. State is known
or unknown; unknown value is null. Origin is parser_produced or model_proposed;
nonempty support references must resolve within this evidence's support inventory.
Required attributes: `value`, `scale`, `unit`, `entity`, `metric`, `period`, `basis`,
`status`, `scope`, `measurement_precision`. Measurement precision can stay unknown;
all other attributes must be known before use in calculation. Keep all attribution
and unknowns in the trusted snapshot; do not silently infer completeness.

- Value is a bounded decimal string; scale is the explicit remaining power-of-ten
  conversion. Already normalized XBRL values require scale zero. The caller remains
  responsible for admitting the correct representation from source support.
- Unit: `{kind, code, rate_representation}`. Currency/count kinds require nonempty
  codes and representation none. Dimensionless uses null code and fraction/percent;
  percentage_points uses null code and none. No currency conversion.
- Entity: `{scheme, identifier}`. Metric: `{namespace, name, role}`, where role is
  profit, revenue, rate, or other. Display-label equality is insufficient.
- Scope: `{identity, dimensions, qualifiers, complete}`. Identity is nonempty,
  dimensions a string-to-string map, qualifiers a list of distinct nonempty strings,
  and complete must be true. An empty dimension map alone is not scope admission.
- Basis is a nonempty declared accounting-basis identifier; status actual/guidance.
- Period: `{kind: instant, date}` or `{kind: duration, start, end}`. ISO dates,
  duration start inclusive/end exclusive, start strictly before end.
- Measurement precision, when known, is `{kind: decimal_places, value: integer}`;
  it is preserved source metadata, never an arithmetic rounding instruction.

## Compatibility and result metadata

All operations require identical entity, complete scope including residual
qualifiers, accounting basis and actual/guidance status. Like units compare kind
and code; fraction/percent rates normalize exactly into percent before arithmetic.
Output unit is the exact derived unit assertion, not a requested conversion.

Add requires equal metric identity and exact single period; repeated identical
references reject. This does not establish nonoverlap of distinct admitted facts.
Subtract, growth and percentage-point difference require equal metric identity and
equal/comparable single periods. Comparable instants allow different dates;
durations require equal day counts OR both endpoints on calendar-month boundaries
with equal month counts. This admits leap-year calendar spans without silently
equating arbitrary 52/53-week years. No single-period/comparison-period mixing.

Ratio/margin require exact single period and compatible units. Margin additionally
requires currency operands and admitted ordered profit/revenue roles. Metrics may
differ for ratios. Percentage-point difference requires two dimensionless rates.
Growth baseline positivity remains the numerical policy. Temporal operations
preserve ordered current/comparison periods; even same-period growth retains a
comparison pair. Comparison-valued results cannot be new operands in v1.

Add/subtract preserve the common unit, with rates represented as percent. Ratio
returns dimensionless/fraction; margin/growth dimensionless/percent; rate difference
returns percentage_points/none. Derived metric identity hashes operation and ordered
child metric hashes, excluding evidence IDs and dates. Ratio and margin remain
distinct metric identities. Derived roles are rate for ratio/margin/growth, other
otherwise; do not automatically infer that an arbitrary sum is admitted profit.

## Ledger and replay

`calculate(operation, operand_refs, output_unit, rounding_policy)` accepts exact
reference objects `{kind: evidence|calculation, id}`. Resolve only the immutable
snapshot or an earlier calculation in this ledger; never raw factual numbers.
Store all upstream evidence IDs, operand content hashes, derived metric/period/unit,
scope checks, admission/policy identity, and numerical kernel output. Chains consume
precision_result, not display_value; normalize derived units once with scale zero.
Evidence depth is zero; calculation depth max(parent depth)+1, maximum 16.

Calculation IDs hash run/admission/policy/request plus the rebuilt record. Equal
requests may return an existing identical immutable result. Unknown, future,
cross-run, rebound or cyclic references reject. Copies returned to callers cannot
mutate registry state. Validate output unit, compute/rebuild all fields, serialize
the entire prospective response under 12,000 characters, then commit atomically.

Replay starts from an independently trusted snapshot, reexecutes records in order,
and compares entire canonical records; do not trust stored checks or reuse saved
display values. Altered source/receipt hashes, periods, scope, references, arithmetic
order, precision policy, or lineage fail even if a displayed number remains equal.
This is integrity relative to trusted input, not signed attestation.

Acceptance requires synthetic positive current/prior margin chaining and negatives
for unknown/incompatible attributes, dates/durations, wrong units/roles, nil, duplicate
refs, depth, future/cross-run refs, mutation, tampering, non-reassociation, and full
response overflow without state mutation. Independent review plus full/clean checks
are required. H3's actual source admission, claim visibility and tool budget remain
separate gates; no financial-answer accuracy gain follows from this infrastructure.
