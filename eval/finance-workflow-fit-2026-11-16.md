# Narrow finance workflow instructions

Research cycle 7, 2026-11-16. Decision: propose one optional H4 instruction
comparison after H2/H3 integration. No runtime prompt changes now.

## Primary-source findings

FinanceHarness revision `1163c5e7a8f35ff6217c3a480f7b04562355e0cc` contains short
workflows with declared tool prerequisites:

- [Consensus check](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/skills/consensus-check/SKILL.md)
  separates estimates from reported facts, combines a consensus snapshot with
  corroborating reads, and retains unverified status where confirmation is absent.
- [Ticker snapshot](https://github.com/Yijia-Xiao/FinanceHarness/blob/1163c5e7a8f35ff6217c3a480f7b04562355e0cc/financeharness/skills/ticker-snapshot/SKILL.md)
  names its reference/price tools and handles unavailable fields without guessing.

These workflows depend on market-data capabilities outside prov's current supplied
document milestone. Adopt the narrow prerequisite/check/report pattern, not their
market-data product scope. The code was inspected as reference material, not
installed or executed as an agent skill. Source byte hashes respectively:
`3272c12bc94cc3f35a235bd037c6301e5d23ad5624146daaf68d1bb57e2aff3f`
and `60f3c173151c04801334d0beb0499586198206e08d41c24587295744cd9c6d21`.

[Anthropic's workflow/agent comparison](https://www.anthropic.com/research/building-effective-agents),
published 2024-12-19 and accessed 2026-11-16, distinguishes predefined paths from
model-directed tool use and recommends increasing complexity only with evidence.
The page explicitly notes that its tooling discussion has aged; use the conceptual
distinction, not its old platform assumptions. A procedural prompt does not require
a multi-agent architecture or a separate model call for every checklist step.

## Local fit and actual novelty

At HEAD `015e7e9`, H2's acceptance protocol is frozen and implementation is active.
The current `provenance/model.py::INSTRUCTIONS` already mentions fiscal periods,
currency, scale, accounting definitions, actuals/guidance, neighboring context and
abstention. Merely adding those cautions again is unlikely to isolate a useful
hypothesis. The candidate difference is ordered evidence acquisition and an
explicit compatibility decision before calculation.

Keep the existing single agent, tools and deterministic controls. No skill loader,
new connector, planner model, market-data fetch or agent team is required. A
versioned optional instruction block is the smallest testable intervention.

## Original candidate text for a later experiment

> For a requested two-period comparison, identify the metric and both requested
> periods. Read each value together with its unit, scale, entity, accounting basis,
> scope, and relevant table headers or notes. Before calculating, determine whether
> the periods and definitions are comparable; preserve unknowns and conflicts.
> Use the supplied calculation tool with accepted evidence references only when
> compatibility is established. If support is missing, read the specific missing
> context within the remaining budget. Report supported results and explicit gaps;
> stop when the requested comparison is supported or further permitted research
> cannot resolve it.

This text is a proposal for the future tool profile; the current two-tool default
must not be instructed to call an unavailable calculator. Do not print a long
checklist in the user's answer or add unrequested financial figures. Normal
evidence/calculation records provide the inspection surface.

## Acceptance and costs

Compare unchanged instructions against the optional block on the same frozen,
source-accepted development tasks and equal total budgets. Keep context policy,
tools, model and output contract fixed. Predeclare scope/period selection errors,
missing-qualifier errors, strict supported success, completion, calls, latency
and cost. Include tasks that need only extraction, tasks with compatible periods,
and tasks that must abstain because definitions differ or support is absent.

Potential benefit is fewer calculations over incompatible operands. Risks are
redundant reads, extra prompt cost, over-abstention and applying a comparison
procedure to a simple lookup. A procedural checklist is not an independent
financial validator. Reject it if the apparent gain comes from unsupported
assumptions, fewer completed tasks, or uncounted extra research.

This is a small prompt-maintenance burden with no deployment dependency, but the
effectiveness test still costs inference and review. Queue it after the required
capabilities exist; freeze and fund the experiment separately. Do not combine it
with H4 retention changes in the first comparison, which would obscure attribution.

## Integrity and handoff

Reservation/exposure metadata was checked before research. Upstream retrieval
withheld any paragraphs matching reserved issuer names/aliases; neither inspected
workflow displayed such a paragraph. No financial source content or benchmark
answer was opened. All dispositions remain unchanged.

Handed to implementation for review, a research-ledger link and an atomic
documentation commit. The existing runtime instructions and H2 protocol were
not edited. No improvement claim or paid experiment follows from this proposal.
