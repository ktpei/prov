# Working context — 2026-11-03

## User request and constraints

Implement roadmap steps 1–2 of the first ProvenanceXL project brief. Ask when a
decision needs input. User chose: **OpenAI first; configure live calls later**.
No paid API calls should be made during this task. Work is an informal unpaid
side project; keep implementation narrow.

## Confirmed project context

On 2026-11-03 the user confirmed that the first brief in the
[Provenance × Tech@NYU artifact](https://claude.ai/artifact/3cSNqEgPBvGGNVjAj2vjcH)
is our project. The artifact was read directly in Chrome. `project.md` now
records the selected finance harness brief, the separate deal-agent brief,
alternative project ideas, shared ground rules, and semester deliverables.

Keep the distinction between the full sponsor ask (5–7 tools and a measured
25-task evaluation) and currently authorized steps 1–2 (two read-only tools and
no live model evaluation yet). Briefs 2–3 supply context, not authorization to
build a specialist-agent team or expand scope. Preserve the existing OpenAI-first,
live-calls-deferred decision.

## Current state

- Initialized Git from a directory containing only `AGENTS.md`; work is on
  `feat/evaluation-agent-foundation`. No remote or PR destination is configured.
- Five official historical earnings-source extracts and a hash manifest.
- 25 tasks with gold claims and rubrics: 10 dev, 15 heldout; 3 unanswerable.
- Read-only model loop, two tools, OpenAI and optional Exa HTTP adapters,
  conservative budget accounting, limits, traces, and structured answers.
- Offline demo is a hand-authored replay, clearly labeled in output and docs.
- `yarn lint` and `yarn test` pass; the suite contains 33 offline tests.

## Verification boundary

Corpus data was verified against official public documents and statically
checked. Offline runtime tests cover control flow and failure paths. Live
OpenAI/Exa requests and model-quality evaluations remain unverified and deferred
by user choice. No heldout model evaluation has been run.

## Next authorized decision

When the user resumes live setup, choose an exact model, verify current pricing,
configure the rates and per-run budget, then run one development question and
review its trace before any broader evaluation. Preserve the heldout split.
An OpenAI key was present in the environment during inspection; its value was
not exposed, printed, or used in requests. Exa was not configured. Re-check
availability when needed.
