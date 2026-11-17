# Reference transport and financial acceptance

Research cycle 3, 2026-11-16. Proposal for H2/H3; no runtime changes or paid calls.
Complements [the research ledger](harness-methodology-research-loop.md) and
[the implementation specification](../harness-improvement-spec.md).

## Pinned source and method

Inspected FinanceHarness revision
`1163c5e7a8f35ff6217c3a480f7b04562355e0cc`, resolved through GitHub's commits API.
Read only runtime registry, reference resolver, dispatcher, event helper, and
arithmetic source files. No benchmark data or source filings were retrieved.

- [Resolver](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/runtime/chaining.py)
- [Dispatcher](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/runtime/dispatch.py)
- [Registry](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/runtime/tool_registry.py)
- [Calculator](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/tools/compute/arithmetic.py)

## What the code establishes

Reference strings resolve against successful tool payloads in per-run session
state, before consumer schema validation. The resolver supports dictionary paths,
list indices and wildcard selection. This avoids transporting large values through
model-generated arguments. Resolution establishes where a value came from; these
modules do not establish its currency, period, accounting basis, or suitability
for a requested financial calculation.

The dispatcher records original arguments and returned structured results.
It catches generic handler exceptions and converts them to repairable tool errors.
Successful payloads are assigned by call ID. These local behaviors do not prove
that the whole upstream agent lacks additional controls or call-ID safeguards.

The calculator is an AST evaluator using Python integer/float operators and math
functions, with an exponent bound. Its request is an expression string, not an
evidence-operand contract. The model-facing result uses six significant digits;
the structured result retains the underlying value.

## Bounded verification

Downloaded calculator bytes had SHA-256
`f9cc3001b204788bf902e2e53a95fcd0907838a097ea0b63cba7ccd277764bbc`.
Executed only the inspected `_eval` and `safe_eval` definitions and their operator
constants, extracted with Python AST into an isolated namespace containing
`ast`, `math`, `operator`, and a local `ToolError` exception. No package install,
handler, dispatcher, serialization, or provider execution was performed.

| Synthetic expression | Observed evaluator result |
| --- | --- |
| `0.1+0.2` | float `0.30000000000000004` |
| `True+1` | integer `2` |
| `1e309` | float infinity |
| `2**1001` | `ToolError` |
| `1/0` | `ToolError` |

These results concern the evaluator boundary only. In particular, downstream
serialization may reject nonfinite results; that path was not tested. Do not
report these examples as end-to-end finance benchmark failures.

## Integration decisions

| Decision | Expected benefit and cost | Acceptance condition |
| --- | --- | --- |
| Borrow reference transport, retain prov's typed evidence contract | Less transcription; modest registry/validation work | Resolve only accepted same-run evidence, then check financial compatibility before arithmetic |
| Keep H2's bounded Decimal operations instead of importing the expression calculator | Explicit units, precision and finite-value behavior; narrower operation vocabulary | Existing H2 Boolean/nonfinite/precision/scale cases must pass independently of display formatting |
| Explicitly preserve control exceptions in H3 | Prevent model repair loops after resource exhaustion; small dispatcher change | Budget/deadline stop escapes dispatch immediately, no follow-up model call or accepted calculation record |
| Record original references and validated operand identities | Reviewable derivations; small trace size increase | Replay detects changed target content, duplicate/rebound IDs and incompatible resolved metadata |

The first two decisions reinforce existing specification requirements; they are
not newly discovered missing features. The concrete clarification for H3 is that
`LimitReached` (including `DeadlineReached`) must propagate before any generic
exception-to-tool-error handler. `provenance/sources.py` already follows this
pattern. Maintain it when introducing the new dispatcher; the upstream generic
catch is not directly compatible with prov's control exception hierarchy.

Treat malformed references as bounded repairable errors, but keep resource stops
as controller outcomes. Test with a synthetic handler raising each class and
assert exact provider/tool counts, preserved reservations, and no success record.
Do not add retries or a broad plugin framework merely to adopt reference chaining.

## Scope and handoff

Local comparison used HEAD `179d176` and the active implementation checkout;
H1 edits remain owned by the implementation chat. Reservation metadata and the
exposure audit were rechecked; all six dispositions remain unchanged. The upstream
calculator contained an unattributed numerical growth example in documentation;
no issuer was identified and that example was not used in tests or recommendations.

This file is handed to the implementation owner for review and a focused research
documentation commit, together with a link from the research ledger. No claim of
adoption or measured end-to-end improvement is made. Next research should examine
evidence visibility when tools consume structured data the model has not seen.
