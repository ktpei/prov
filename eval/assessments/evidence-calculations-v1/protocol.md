# Evidence-linked calculation acceptance protocol

Frozen before implementation · 2026-11-16 · H2

Baseline: `82aa34b`. This is an offline infrastructure cycle using synthetic
records only. No paid calls, new source selection, reserved content, or changes
to the paused XBRL assessment are included. H1 remains opt-in and unchanged.

Hypothesis: a bounded deterministic calculator with independently replayed
evidence references removes transcription/arithmetic ambiguity while rejecting
incompatible financial operands. Arithmetic correctness alone does not establish
financial meaning. Do not expose a model-facing calculator until its reference
and admission boundary exists; a numerical kernel is only an internal component.

## Project fit

Keep this in process with Python's standard Decimal library. No new service,
agent team, expression interpreter, arbitrary code execution, or dynamic tool
discovery. Compare implementation cost and maintenance with the existing model-only
calculation path; actual accuracy/cost comparison belongs to a later frozen
development experiment. Current production workload and staffing are unknown.

## Numerical policy freeze

Use six operations from spec section 4.4: add, subtract, ratio, margin percent,
relative growth percent, and percentage-point difference. Follow the ordered
formulas there literally. Initialize addition with operand zero (the first input),
not a synthetic numeric zero; never pre-round operands. Arithmetic uses precision
34 and ROUND_HALF_EVEN. Preserve intermediate arithmetic rounding flags separately
from display quantization flags. Relative growth requires a strictly positive
baseline; all division rejects zero denominators.

Only ASCII decimal strings are accepted, including decimal/scientific notation.
Bound lexical coefficient digits to 128 before constructing Decimal. Parsed
exponent and adjusted exponent must independently be in [-100,100]. Exponent
digits are checked before integer conversion, ignoring leading exponent zeros;
bound the entire lexical input to 512 characters to reject oversized encodings.
Reject booleans, floats, nil, malformed and nonfinite values. Accepted inputs,
normalized operands, final arithmetic and display results must meet the same
coefficient/exponent bounds; rejection is atomic. Pure internal intermediates
use a wider bounded context and need not meet persisted-value bounds: for example,
margin(9e100,9e100) must return 100 despite a temporary numerator exponent of 102.

Normalize an explicit integer power-of-ten scale in [-100,100] by exact Decimal
tuple exponent shifting, not context-rounded multiplication. Preserve lexical
input and transformation. Rates explicitly use fraction or percent; normalize
fractions into percent by an exact +2 exponent shift before arithmetic. Other
numeric values declare rate representation `none`. Percentage-point differences
require two rate operands. The future ledger checks physical units and financial
compatibility; this kernel cannot accept or certify evidence.
The formula constant 100 uses an exact +2 exponent shift, also without rounding.
Growth subtracts at precision 34, shifts that difference, then divides. Arithmetic
uses context Emin=-1000/Emax=1000, clamp=0; persisted bounds are checked explicitly.

Rounding requests have exactly `{decimal_places: integer 0..12}`. Display uses
half-even quantization with sufficient precision (128) for permitted large values,
not arithmetic precision 34. Preserve the pre-display result and both sets of
inexact/rounded flags. Display cannot be reused as a calculation operand.
No caller-selected rounding mode or arbitrary expression is supported.

At most 32 inputs for add, exactly two for other operations. Bound the complete
serialized calculation response to 12,000 characters. The kernel checks its own
response; the ledger must recheck after provenance/lineage is included. Errors
have stable codes; budget/deadline exceptions are never converted to repair errors.

## Evidence and chaining acceptance

The full H2 ledger is a separate required component, not waived by kernel tests.
Admission is a trusted controller boundary, never a caller-supplied accepted flag.
H3 supplies actual reader reconstruction/semantic admission and final visibility.
H2 tests use a clearly identified synthetic admission authority. Records snapshot
run identity, source/read/content identities, normalized values, supporting
attribute evidence and attribution, metric, entity, scope, accounting basis,
actual/guidance, and period. Unknown required attributes reject calculations.
Existing typed XBRL values already include sign/scale; never scale them twice or
infer consolidated scope from absent dimensions.

Derived metrics use operation plus ordered child metric identities, excluding
occurrence IDs and dates; lineage separately binds operand IDs/content hashes.
Single instant/duration periods and comparison-period pairs remain distinct.
Temporal subtraction/growth retain both current and comparison periods. Same-period
ratios require identical periods; temporal changes require comparable metrics and
period types/durations. Freeze exact cadence semantics before ledger implementation;
do not silently equate 52/53-week periods or unknown fiscal calendars.

References resolve only to immutable same-run admitted evidence or earlier
calculation records. Reject rebound IDs, raw factual operands, cycles, future or
cross-run references, unknown scale, nil, incompatible currency/scope/basis/status,
and depth over 16. Replay reconstructs every record, including ancestry and hashes.
Output unit is an assertion, not a conversion instruction. Controller budget
integration and model-facing dispatch remain H3 acceptance requirements.

## Verification and decision

1. Numerical fixtures independently cover cancellation of >34-digit inputs,
   order-dependent rounding, scale conversion, mixed fraction/percent rates,
   half-even ties, positive growth baseline, input/output/exponent bounds,
   large display quantization, and typed failures with no partial mutation.
2. Ledger fixtures cover financial scope/period mismatches, unknown attributes,
   precision preservation through chains, changed/rebound references, depth/cycle
   rejection, and reconstruction from trusted inputs.
3. Independent Astra numerical and financial-contract reviews; lead inspects code.
   Run targeted adversarial checks, `yarn lint`, `yarn test`, and clean committed
   verification excluding other chats' untracked work.
4. Record each implemented component and remaining requirements separately. Accept
   H2 only when both numerical and evidence/ledger requirements pass. Do not claim
   end-to-end financial improvement or expose raw-number calculations to the agent.

Lead owns tightly coupled implementation and integration. Reviewers are read-only.
Keep frozen benchmark results, legacy defaults, spending and all six reservation
dispositions unchanged. Record negative findings and choose subsequent work from
the remaining acceptance requirements rather than calling a partial H2 complete.
