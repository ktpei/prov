# Evaluation methods at prov's scale

Research cycle 6, 2026-11-16. Decision: retain the local evaluator and borrow
specific measurement practices; no new evaluation platform or paid run proposed.

## Primary evidence and comparison

[Anthropic's agent-evaluation guidance](https://www.anthropic.com/research/demystifying-evals-for-ai-agents),
published 2026-01-09 and accessed 2026-11-16, distinguishes task attempts,
deterministic checks, model judgments and human calibration. It also distinguishes
at-least-one success across repeats from consistent success across repeats.
For prov, an occasional correct financial answer is insufficient evidence of
reliable single-run behavior. Keep every repeat, not the best response.

[Inspect scoring policy](https://inspect.aisi.org.uk/scoring-policy.html), accessed
2026-11-16, excludes scoring errors and `Score.unscored()` values from aggregate
accuracy. `None` can omit a score without increasing its unscored count. These
are explicit measurement choices, not framework defects.

[Inspect metrics](https://inspect.aisi.org.uk/metrics.html), accessed 2026-11-16,
documents epoch reduction and grouped uncertainty. The default epoch reducer is
mean; reduced results do not by themselves preserve the full trial distribution.

Local comparison at HEAD `82aa34b`: `provenance/benchmarks.py::score_run` preserves
selected tasks and gives missing/incomplete predictions unsuccessful outcomes.
The full-agent specification requires every preselected adjudicable case in its
strict-success denominator; unresolved references are counted separately. It also
already requires paired execution, frozen repeats, clustered uncertainty and
fresh confirmation. These are existing requirements, not new research proposals.

## Concrete integration delta

If an external evaluator is later added, keep three distinct layers:

1. Execution status: completed, failed, stopped, or not run under the budget.
2. Measurement status: scored, grader error, or unresolved reference.
3. Verified strict success over the frozen adjudicable inventory, with separate
   scoring and execution coverage.

An unverified result cannot establish strict success. A grader failure is also
not evidence that the financial answer itself is incorrect. Report that unknown
explicitly; unresolved measurement prevents a supported promotion decision.

Synthetic adapter acceptance case: four selected adjudicable tasks, one verified
correct, one verified incorrect, one grader error and one unscored verdict.
Scored-only accuracy is 1/2; verified strict success is 1/4, with 2/4 scoring
coverage. Preserve all four records and reasons. Add a missing prediction and a
not-run-budget case; neither may silently disappear. Reject duplicate/foreign
IDs. This check can run offline and requires no real issuer content.

## Project-size decision

The lowest-cost next step is an aggregator contract test when an adapter is
introduced, not an evaluator migration now. Current benchmark scoring already
has denominator regression tests. Avoid duplicating those unless the new adapter
introduces a new boundary. Keep raw per-trial rows even if a dashboard reduces
them; issuer/report/conversation group IDs must survive conversion.

For ongoing development, use deterministic evidence/arithmetic/replay checks to
reject broken candidates before spending on model trials. A small predeclared
development pilot can diagnose failures, but cannot become confirmatory evidence
merely because it is affordable. Repetition counts and sample size still depend
on the claim, observed variability and reconciled budget. Do not adopt a vendor's
suggested initial task count as a power calculation for this project.

No multi-judge committee is justified by this research. Add model grading only
for semantics deterministic checks cannot establish, retain individual judgments,
and preserve the existing requirement for independent domain calibration.

## Integrity and handoff

Reservation/exposure metadata was rechecked. No held-out source content or
benchmark examples were opened. The Anthropic page displayed an Apple-founder
prompt and generic flight/software examples, not a financial worked answer;
record that visibility without treating it as a new finance development case.
All six frozen dispositions remain unchanged.

No runtime changes or paid experiments. This document is handed to implementation
for review, a research-ledger link and a focused documentation commit. The
comparison reinforces current evaluation policy and adds a specific future
adapter acceptance case; it does not establish an accuracy improvement.
