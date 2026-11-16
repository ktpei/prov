# Six-case retrieval and context comparison protocol

Freeze the exact driver, runtime, baseline snapshot module, earlier-read challenger
module, this plan, selection, prepared manifest/tasks/inputs, corpus manifest/binding
and every annotation artifact before the first search. Use the six prepared IDs in
the annotation receipt's order. No replacements, packet edits, threshold changes,
query variants, retries, model calls or production-policy changes are allowed.

## Execution before labels

The run command parses only prepared `inputs.json` and source metadata/text. It
may hash prepared references and annotation bytes for identity, but does not parse
those labels. Source construction verifies all originals and native text. Restrict
each search to the input's declared document; use original question text and the
existing `Sources.search` entry point with default `bm25-v2`. Pass `timeout=1` to
match historical diagnostics; the local methods do not enforce a one-second
wall-clock deadline. No external credentials or provider calls are supplied.

Persist all six pending cases before dispatch. For each case record search-started
status, save the complete actual search response, then project the ordered results
to source/start/end fields for `read_ranked_passages`. Attempt each exact ranked
parent once, at most five; do not expand or substitute. Save the durable read
journal and result before projection. Failed reads consume their ranks. Zero hits
remain complete execution cases with no evidence. Unexpected search/read/integrity
failures or interruption abort the assessment while preserving completed and
pending slots; an aborted assessment is not a successful six-case comparison.

Import the hash-bound historical `snapshots` implementation. Both policies receive
the same question, full search response and read records. Production remains the
baseline. The challenger is the unchanged `earlier-optional-results-first-v1`
function, installed only on the fresh analysis module and restored in `finally`.
Assert identical canonical-history hashes at every prefix. Independently project
one, three and five attempted-read prefixes, each from its unpruned history, under
32,000 serialized output-string characters. This is not a byte, token or total
prompt budget. Preserve latest search/read requirements, omission notices, failed
latest reads and blocked projections. Omitted locators grant no evidence.

## Replay before grading

The grade command reruns the entire deterministic collection and both projections
into temporary files. Compare every run/snapshot byte and every journal byte, with
exact file inventory, before opening the annotation packet JSON. Verification calls
are reported separately from the original six searches and at-most-thirty reads;
they are integrity replay, not retries used to select better results.

Validate packet schema, corpus/original/text hashes, exact case order, declared
sources and complete alternatives using existing coverage primitives. Report search
parent opportunity and returned snippets, delivered reads, and retained read text
separately. Only retained read text counts toward retention completeness. In
particular, requested parent bounds still attached to an omitted/failed read do
not become retained evidence. All-six and mapped-location denominators remain
explicit. Report failed/truncated reads, blocked projections, and paired wins,
losses and ties at each prefix; make no financial-correctness score.

Recheck frozen inputs, runtime, source identities, run/journal inventory and bytes
before completing grading. Verify written outputs against the computed result.
No result-driven packet or policy tuning is permitted within this version. A later
change requires a separate version preserving this result and all failures.

## Interpretation

These synthetic fixed reading histories measure evidence delivery and retention,
not agent search choices, model answer accuracy or human-validated finance skill.
Keep the frozen annotation's 3M, Coca-Cola and Verizon semantic caveats attached.
Six public development cases and unresolved cross-suite issuer identities do not
support a generalization or contamination-free claim. No default promotion follows
a favorable result alone. The original corpus and holdout remain untouched.
