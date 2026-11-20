# Daloopa retrieval benchmark — quick and full

Implemented 2026-11-20 alongside the existing external suite. This is an adapted
API-agent evaluation of Daloopa's public questions, not a replication of its
historical chatbot web-app leaderboard. No Daloopa model accuracy is established
by preparation or offline tests.

## Prepare once

```sh
uv run python -m provenance.benchmark_data --name daloopa-public --output runs/benchmark-data/daloopa
uv run python -m provenance.daloopa --input runs/benchmark-data/daloopa/train.csv --source-manifest runs/benchmark-data/daloopa/source.json --output runs/benchmark-prepared/daloopa
```

Downloads are pinned to Hugging Face revision
`af16f65b841cf6a2921de57394127426c6161a13` and a SHA256 in
[external-sources.json](external-sources.json). Raw third-party data, prepared gold,
model traces and evidence snapshots remain in ignored `runs/`. Use new directories
for every preparation and execution; existing results are never overwritten.

The 3,000 historical answer rows become **500 distinct questions**. Historical
chatbot answers never enter agent inputs. The entire inventory is preserved:
427 references currently parse conservatively, 72 require reference review, and
one issuer (AMD) is reserved. The published parsed-number column is inconsistent
about scale, so it is retained for audit but not used as unquestioned gold.
Ambiguous sequences, units, periods and conflicting references remain unscored.

## Quick and full

```sh
yarn benchmark                       # plan only: fixed 25-question quick selection
yarn benchmark:full                  # plan only: full 500-case inventory
```

Quick selection uses seeded round-robin sampling across category/difficulty from
cases with parseable references. It is stable for a given prepared manifest and
is a subset of full. It is not an unbiased estimate of the full benchmark.

Full executes all 499 nonreserved questions, including the 72 cases awaiting
reference review; their answers are retained but their numerical scores remain
null. AMD remains an explicit reserved case, not a silent deletion or failure.
Neither profile opens the six FinanceBench reservation contents. The other
reserved issuers and known aliases are also excluded. Full is public development
evaluation, not a new unseen-company validation claim.

Both profiles use the same per-question limits: six model calls, eight tool
calls, 90 seconds, 30 seconds per request, and 1,800 output tokens. The existing
research runtime can repair one invalid answer and use its finalization step;
there are no batch retries. Quick is faster because it selects fewer questions.
The full dataset is not shortened or replaced.

## Live execution

Export the existing `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and conservative
`OPENROUTER_INPUT_USD_PER_MILLION` / `OPENROUTER_OUTPUT_USD_PER_MILLION` values.
Web retrieval additionally requires `EXA_API_KEY` and a positive conservative
`EXA_MAX_REQUEST_USD` (the local setup uses $0.03 per request). Credentials are never written into benchmark artifacts.

```sh
yarn benchmark --live --web --budget-usd 2 --per-task-usd 0.08 --output runs/daloopa-quick-01
yarn benchmark:full --live --web --budget-usd 30 --per-task-usd 0.08 --output runs/daloopa-full-01
```

Budgets are upper bounds, not expected costs. A low cap can stop tasks or the
batch; stops remain visible in the denominator. `--no-spend-limit` is an explicit
alternative to spending flags. Without `--live`, commands never call a model.

Alternatively supply `--corpus path/to/issuer-corpus` using the existing Sources
manifest format. This is labeled frozen-corpus access; it does not measure open-web
retrieval. Corpus metadata is checked before opening text files. Reserved-issuer
and known benchmark-answer websites are blocked from retrieval; this is not a
proof that every mirror or indirect contamination source is excluded. Original
source status must still be reviewed. Do not place gold in an accessible corpus.

## What the results mean

`submission.json` preserves the complete selection, durable pending reservations,
actual inputs, outputs, trace and evidence snapshots, code/configuration hashes,
costs and stops. An uncertain charge stops the whole batch. An interrupted pending
request is not automatically resumed or retried.

`score.json` reports exact numeric matching, 1%/5% tolerances, quote validity,
completion, category/difficulty/unit slices, cost and latency. Zero references
require exact zero for relative-tolerance success. Units and signs are preserved;
no currency conversion is inferred. Only the `requested_answer` claim is scored,
so a correct incidental number cannot mask the wrong requested answer.

Numeric matching is **not** proof of correct metric, period, accounting basis or
source support. `supported_accuracy` remains null until required reviews are
complete. Reference-unresolved and reserved cases remain in the full inventory;
scorable and selected denominators are shown separately, with an all-selected
lower bound. Wilson intervals describe only the evaluated fixed selection.

Each completed run emits `review-template.json`. A reviewer verifies the original
reference, metric, period, basis, original source, citation support and absence of
unsupported additions. Record identity, human/agent kind and explanatory notes.
Reviews bind exact task, report and evidence hashes; stale reviews fail closed.
Agent review is not human finance validation.

```sh
yarn benchmark:score --prepared runs/benchmark-prepared/daloopa --submission runs/daloopa-quick-01/submission.json --reviews runs/reviewed-answers.json --output runs/reviewed-score.json
```

Preparation emits `reference-review-template.json` for unresolved gold. Fill only
reviewed entries with a verified value/unit, original-source URL and locator,
reviewer identity/kind and notes. Reprepare into a new directory with
`--reference-reviews path/to/reviews.json`. Reviews cannot unlock reserved issuers.
Updated references create a new preparation identity and may change quick
selection; never compare its scores as if the original selection were unchanged.

Sources: [Daloopa methodology](https://daloopa.com/benchmark/an-open-source-benchmark-to-measure-llm-accuracy-in-financial-retrieval),
[pinned dataset card](https://huggingface.co/datasets/daloopa/financial-retrieval/blob/af16f65b841cf6a2921de57394127426c6161a13/README.md).

## Exa integration verification

The `build-with-exa` skill was read completely on 2026-11-20, including its search,
contents and prompting references. Installed `exa-py` 2.29.0 in the project
environment. The integration uses the documented raw HTTP endpoints to preserve
the existing durable budgets, hard timeouts and no-retry behavior. Web searches
require model-authored `query` and `objective`, forward the objective unchanged,
and request highlights. Five results and bounded returned content are intentional
lean-benchmark limits. No category, freshness or API domain filters are added.

The system prompt includes the skill's search-before-answering instruction and
primary-source query guidance. Full document reads use `/contents` and inspect
per-URL statuses even on HTTP 200. Web execution uses model-input receipts to
record the actual augmented prompt and tool schema. The old frozen-corpus runtime
and benchmark suite retain their original prompt/tool definitions.

A live search/read smoke test succeeded through project code for the already
exposed Cloudflare packet. Estimated Exa cost: $0.008; no uncertain-cost flag.
Local secrets are stored only in the ignored `.env` with owner-only permissions.
