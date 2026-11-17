# Cloudflare live OpenRouter check — 2026-11-16

Explicitly requested live execution of all nine existing Cloudflare development
questions using `deepseek/deepseek-v4.1-flash-1017`, LangGraph and the default
search/read tools. Baseline recorded by runner: `0fdb980`; shared checkout dirty.
No runtime edits, retries or policy promotions. New arithmetic/typed-read tools
are not integrated into this runner.

Read-only credential preflight: environment credential rejected (401); project-local
credential authenticated with $3 remaining key allowance and zero daily usage.
No secrets saved here. Public catalog listed the selected model; configured
$0.40/$1.60 per million input/output rates conservatively exceed its listed
$0.036/$0.50 rates. Pricing used is an application estimate, not an invoice.

Selected all nine cases before dispatch, aggregate cap $0.27, per-task cap $0.03.
The existing runner persists reservations before requests and stops on uncertain
billing. All nine tasks were attempted, with 50 recorded model calls; four completed,
three passed mechanical checks, five stopped with `spend_limit`. Estimated cost
$0.078254, no uncertain-cost flags. Prior unresolved comparison reservations remain
counted: $0.5078571 + $0.078254 = $0.5861111, leaving $0.4138889 against the historical
$1 authorization (not an account balance).

| Task | Result | Automatic checks |
|---|---|---|
| packet-01 | completed: answer returned | fail |
| packet-02 | stopped: spend_limit | fail |
| packet-03 | completed: answer returned | pass |
| packet-04 | stopped: spend_limit | fail |
| packet-05 | stopped: spend_limit | fail |
| packet-06 | stopped: spend_limit | fail |
| packet-07 | stopped: spend_limit | fail |
| packet-08 | completed: answer returned | pass |
| packet-09 | completed: answer returned | pass |

Five stops reflect conservative next-request reservations, not spending the full
three cents on each question. Do not interpret them as wrong financial answers.
Packet-01 gives the detailed filing value of $430.082m and rounds it to $430.1m in
prose; the frozen grader expects the release value/source. Its primary converted
claim cites headers while a separate thousands claim cites the number, so this is
also a claim-level support issue, not a blanket semantic pass.
Packet-03 supplies guidance endpoints with release/call support. Packet-08 abstains
but includes extra numerical guidance in prose without structured claims.
Packet-09 supplies the cover date and release evidence, but its assertion that
any 2024 deck figures are forward-looking is overbroad and needs semantic review.
Mechanical success is not a human-validated financial success rate.

[Ledger and per-task grading](experiment.json); each `packet-XX.json` preserves
its result and full event trace. Existing tests were unchanged; the preceding
shared-checkout lint and 523-test run passed. No new test pass is claimed here.
