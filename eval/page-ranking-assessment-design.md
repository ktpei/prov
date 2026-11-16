# Page-ranking assessment wrapper — draft design

**Status: draft, not frozen, not executed.** This document preserves the reviewed
interface plan. Execution requires the protocol freeze described below; reserved
validation content remains closed. The proposed development comparison retains the original six
exposed cases from `financebench-context-v1`; questions, source documents, frozen
annotation packets and denominators remain unchanged.

The [retrieval research proposal](retrieval-research-2026-11-16.md) motivates an
ablation, not an expected improvement. The experiment compares unchanged baseline
passage selection against page/passage reciprocal-rank fusion from a shared pool.
It measures frozen evidence-location coverage, not financial correctness or
exhaustive semantic support.

## Reservation boundary

The separate [validation reservation progress](assessments/financebench-page-validation-v1/progress.md)
records six closed document/question groups, all retaining their original seed-17
development partition membership. Amazon and Microsoft have known prior issuer
exposure; four have no known issuer overlap in the checked records, with unresolved
cross-suite exposure still disclosed. Preserve all six reserved slots without
replacement and do not call the complete reservation unseen issuers. All six
reserved groups remain closed to acquisition, extraction, question/reference
inspection, retrieval and annotation until the separately required policy and
validation protocol freezes. None replaces a case in the original six-case
development comparison described here.

## Interfaces and execution order

Introduce a new assessment wrapper with:

```text
run(protocol_path, run_dir) -> six-case run state
grade(protocol_path, run_dir, grade_dir) -> replay-verified assessment
```

Create all six pending case slots before any ranking. For each case:

1. Construct a hash-verified local `Sources` instance scoped to the declared
   document, with `bm25-v2` retrieval and `pdf-returned-pages-v1` reads.
2. Invoke `compare_page_ranking` exactly once. Persist its full page ranking,
   shared pool of up to 25 positive-score passage candidates, raw passage/page
   scores, exact fusion fractions and both selected hit lists before reading.
3. Produce each branch's search response as
   `{"results": selected_hits, "mode": "frozen_corpus"}`. Preserve existing hit
   payloads; keep page/fusion traces evaluator-owned rather than inserting them
   into model-visible search responses.
4. Use independent source/read state for control and challenger. Each branch calls
   `read_ranked_passages` on its ordered five-or-fewer exact parent ranges, with
   separate journals. No expansion, continuation, replacement of failed slots or
   extra page text is delivered.
5. Reuse the frozen context comparison's `_project` to apply both existing context
   priority policies at top 1/3/5 and the unchanged 32,000 serialized-output-string
   character limit. Histories must be identical between priority policies within
   a retrieval branch; retrieval branches intentionally may select different hits.

Reuse `compare_page_ranking`, `read_ranked_passages`, historical `compare._module`
and `_project`, `coverage`, digest helpers and deterministic encoding helpers.
Do not edit historical scripts or call their top-level `run`/`grade`: their search
dispatch/layout is fixed, and sequential branch grading would open packets before
the second retrieval branch has replayed.

## Freeze and compatibility gates

Bind the new wrapper and plan, page-ranking implementation, historical helper
files, runtime digest, dependency lock, Python version, case order, prepared
inputs, corpus manifest/binding, original/text identities and frozen annotation
artifacts. Bind the reservation status/audit receipt used to establish the closed
validation boundary. Freeze all ranking/read/context parameters explicitly,
including all-page statistics, positive-page ranks, deterministic ties, candidate
limit 25, read limit 5 and reciprocal-rank constant 60.

Require `PYTHONHASHSEED=0` at interpreter startup for execution and replay. Setting
the environment variable inside an already running Python process does not fix
its set iteration order. Preserve the existing BM25 arithmetic and token ordering;
record the Python runtime used with the frozen implementation.

Bind the prior compact assessment artifacts. Check that control search responses,
read responses/journals and context projections match historical compact behavior;
only explicitly enumerated protocol/run attribution differences may be normalized.
Do not broadly discard differing fields or silently accept a changed control.

Both branches must derive from the same persisted candidate artifact. Challenger
hits must be members of that pool, with unchanged bounds, snippets and source
identity. Mapping validation must reject missing, malformed, unordered, incomplete
or cross-page physical-page associations. These are assessment preconditions, not
permission to change default retrieval behavior.

## Whole-wrapper replay before labels

Before grading, verify the complete saved run status and artifact inventory. Replay
the entire wrapper into a new temporary directory, reconstructing shared rankings,
both retrieval branches, all read journals and both context-policy projections.
Require byte-exact equality for the deterministic artifact inventory. Recheck
input/runtime/output identities before opening any packet JSON; hash-only access
to annotation files is permitted earlier.

Only after this whole-wrapper gate succeeds may grading parse packets. Validate
the exact six-case order, source IDs, annotation schema and original/text/corpus
bindings. Recheck identities after grading, and write grades outside the immutable
run inventory. A replay mismatch must prevent packet grading, not merely add a
warning to a scored result.

Elapsed-time telemetry is not deterministic. Store it outside the deterministic
replay inventory, bind it separately by hash, and explicitly freeze this separation.
Do not claim timing bytes replay exactly or exclude arbitrary unexpected files.

## Measurements and accounting

Report shared candidate-pool opportunity, selected-parent opportunity, returned
search snippets, actual returned reads and context-retained coverage separately.
The last four use top 1/3/5 as appropriate. Report blocks, failed/truncated reads,
paired wins/losses/ties by exact case ID for each priority policy, character/byte
budgets, overlap and actual compute costs. Page text used only in scoring receives
no delivered-evidence or citation credit.

`coverage` currently evaluates only top 1/3/5. Passing 25 candidates to it does not
measure pool-25 coverage. After replay and packet validation, add a small
evaluator-only pool-25 calculation that unions the exact candidate line sets and
checks complete alternatives, preserving role-level presence and, if reported,
single-candidate completeness. Never use one enclosing start/end range: that
would incorrectly include gaps between candidates. Pool opportunity is neither
read delivery nor a claim that five reads can deliver the complete pool.

Count shared work honestly: one passage-scoring pass and one page-scoring pass per
case, two derived search responses, and up to ten parent reads across the two
retrieval branches. Both branches share the same scoring construction; do not
report it as two independently executed searches. Each pass scores the complete
eligible passage/page universe, not only 25 items. Report verification replay
separately. Equal caps do not imply equal measured elapsed cost.

## Failures and interpretation

Retain all six original development cases and their frozen order. Ordinary bounded
read failures retain their rank slots and receive no replacement evidence.
Identity, source-mapping, inventory or replay failures abort explicitly, preserve
pending/failed case records and prevent a misleading complete grade. Never shrink
the denominator to successful cases or present an aborted run as a six-case result.

The experiment cannot recover passages outside the shared pool or extend selected
windows. Frozen location annotations are not exhaustive alternative-evidence
judgments; the known 3M convention/alternative-evidence issue and other annotation
caveats remain. No packet changes, new successes, semantic-accuracy claims or
generalization claims follow from this design. Any development result is from
already exposed cases and cannot substitute for the separately gated validation.
