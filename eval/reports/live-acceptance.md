# Company-context research implementation and live acceptance

2026-11-07 · developer milestone, not production or investment-use validation.

The LangChain/OpenRouter adapter, LangGraph model/tool/answer runtime, SQLite
checkpoint/resume, complete four-document Cloudflare packet, native ingestion,
BM25 passage retrieval, bounded evidence reads, and independent evaluation are
implemented. The model remains a single researcher with only search/read tools.
The developer CLI is not the eventual product interface; Excel and UI work remain
deferred.

## Verification

- `corepack yarn lint`: passed (Ruff, formatting, original dataset validation).
- `corepack yarn test`: **79 passed**, no skipped SDK tests.
- Tests include actual subprocess death during a resumed request, duplicate-attempt
  blocking, stable cached completion, replay cursor restoration, bounded citation
  repair, forced final synthesis, immutable evidence, and experiment-ledger failures.
- Original 25-task benchmark preserved; no heldout inference/tuning performed.
- Four full originals acquired: release/10-Q HTML, 18-page transcript, 116-page deck.
- Extraction anchors **8/8**; fixed-query retrieval **5/8 → 6/8**, excluding the
  absence task. Anchors do not establish complete table/chart interpretation.

## Paid development history

All calls used the user's exact model through OpenRouter and frozen public
company evidence. Reference answers/probes/rubrics never entered agent context.
The table counts mechanics and execution, not semantic task success. Earlier
failures remain archived with full public evidence events.

| Iteration | Tasks run | Completed | Mechanical passes | Estimated USD |
| --- | ---: | ---: | ---: | ---: |
| Initial runtime | 5 | 2 | 0 | 0.0981087 |
| Efficient research instructions | 5 | 2 | 2 | 0.0642348 |
| Bounded context + one citation repair | 5 | 3 | 3 | 0.0553665 |
| BM25 + focused snippets (nine-task batch) | 9 | 5 | 3 | 0.0813705 |
| Final synthesis boundary (four targeted reruns) | 4 | 4 | 3 | 0.0508122 |

Total: **$0.3498927** across **28 development runs**,
below the approved **$0.50 aggregate** cap and user-configured $1 daily limit.
All recorded costs are certain under the harness's token-rate accounting; these
are not provider-invoice charges. We used maximum published input/output rates
of $0.30/$1.20 per million tokens and ignored caching discounts. Account billing
may differ. No paid search, OCR, or GPU service was used.

The nine-task BM25 batch completed five answers with three mechanical passes.
It exposed four stopping failures. The final runtime reserves the last permitted
model turn for synthesis with tools disabled, or synthesizes when the tool budget
is exhausted. Four targeted reruns then all returned validated final answers,
with three mechanical passes. **Do not combine successes from these iterations
into a nine-task final pass rate.** The final policy has not received a fresh
nine-task or independent heldout evaluation.

## What the measurements changed

Repeated searches originally produced 34–71K cumulative input tokens per task.
We now project at most 32K serialized tool-result characters into each model
request, retaining complete recent evidence and omission references. Full evidence
remains in traces/checkpoints and the citation ledger. Retained evidence is not
rewritten. Search uses length-normalized BM25 and exact query-focused snippet
lines, so page headers no longer hide a passage's matching sentence.

The same five tasks used 298,881 initial cumulative input tokens versus 118,423
in the BM25 iteration, but only two completed in each batch, with a different
pair completing. Several interventions changed together; this is not a controlled
attribution of token savings or reliability gains.

A final answer must pass structural/read/quote validation. One bounded repair
attempt can correct rejected citations; original output and feedback stay logged.
Execution limits remain unchanged. Durable pre-request markers block automatic
retry after a crashed paid attempt; only explicit safe pauses resume automatically.
Runtime policy, pricing, question, limits, and corpus/retrieval identity bind resumes.

## Remaining quality gaps

- Some correct answers fail the pre-grader because it requires a rounded value,
  exact period formatting, a particular source, or contiguous percent formatting.
  The benchmark was not rewritten after live results to remove these failures.
- A financially supported explanation can still violate a requested-source
  instruction. Extra claims also increase the burden of semantic review.
- Exact quotes do not prove every claim is entailed or that table headers/units/periods
  are inside its cited span. Numerical facts can appear in prose without a
  corresponding structured claim, including in otherwise correct abstentions.
- Native extraction processed every PDF page but does not verify chart geometry,
  merged cells, rotated text accuracy, or OCR. Spot checks are not an OCR benchmark.
- Local SQLite/main-thread deadlines are developer controls. Multiuser server
  execution, production checkpoint storage, Excel approval/stale-cell controls,
  and browser conversations have not shipped.

Detailed coding-agent reviews: [initial](live-review-initial.md),
[BM25 batch](live-review-bm25.md), and [final synthesis](live-review-finalization.md).
These are not independent human reviews. Human financial review and newly authored,
uninspected evaluation tasks remain necessary.

## Reproduce and inspect

```sh
uv sync --locked
corepack yarn lint
corepack yarn test
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 \
  --benchmark eval/company_tasks.json --task packet-04 \
  --result eval/reports/live/finalization/packet-04.json
```

The optional paid runner is `uv run python -m provenance.experiment --live` with
explicit corpus, benchmark, tasks, budget, per-task cap, and new output directory.
It reserves before each task, persists known charges before grading, and never
reuses an existing output directory. Its cap applies to that experiment directory;
this development run manually subtracted all prior experiment charges before
each subsequent invocation. It is not a cross-process/account-wide spending cap.

Raw reports contain complete event traces. `trace_path` preserves the original
ignored-run path; use the embedded events for portable replay. Historical search
outputs replay using `passage-v1`; newer traces identify `bm25-v2`. Runs recorded
during implementation truthfully report a dirty working tree. The final source
is committed in the handoff branch; no claim is made that all earlier runs used
that identical revision.

## Handoff

Branch: `feat/company-research-end-to-end`, based on supplied remote commit
`968068f`. Git writes and dependency installation work. GitHub push failed because
this environment has no GitHub credential; no remote update or PR is claimed.
The Git bundle contains the full branch and history for import into the local repo.
Credentials were used only for authorized requests and were not saved in repository
files, reports, or the bundle. No new user input is needed for offline use.
