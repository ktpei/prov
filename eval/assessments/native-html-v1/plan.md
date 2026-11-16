# Locked native-HTML development assessment

Status: machinery and cohort planning; no assessment questions authored or real
retrieval runs performed. This is a new development assessment, not the original
15-task holdout. Six documents from three other issuers and 24 questions are the
planned size. The [cohort proposal](cohort-proposal.json) records independently checked SEC
filing-index metadata for Casey’s, Old Dominion and Ameren. It is a proposal,
not an acquisition or a completed freeze gate. No financial tables were opened.

## Scope and claims

Assess source-scoped raw table retrieval and required evidence coverage. Keep
financial answer correctness, semantic header association and agent-selected
source quality separate. Compare the already fixed search v1, v2 and experimental
v3, with the original question, top table, first three candidate rows and one read.
Use the existing 12,000-character cap. No rewritten queries, retries, oracle
substitutions, reduced-window repairs, or paid model calls.

The defensible description is a **locked development assessment authored after
implementation freeze, with documented author and annotator exposure**. Hashes
prove artifact identity, not that agents or people have never seen related data.
A shared filesystem is not an enforced confidentiality boundary. Once developers
inspect results, subsequent tuning needs a replenished assessment to support a
new uninspected-quality claim.

## Ordered freeze gates

1. Freeze implementation, extraction version, separate runner and grader,
   dependency lock, selection rules, strata, metrics and condition list. Commit
   before authoring questions. Exact code/dependency hashes must match at execution.
2. Freeze six metadata-selected source identities and an ordered reserve policy.
   Select independently of retrieval performance; record failures and replacements.
3. Acquire originals locally, preserving URL, time, byte count and SHA-256.
   Freeze exhaustive corpus/sidecar inventories. Raw issuer material stays outside
   Git. Acquisition or extraction failures are recorded, not silently replaced.
4. Author and freeze four questions per document, with unique opaque IDs and
   planned strata. The runtime projection contains only ID, source ID and question.
   Author notes, expected answers and table/cell IDs are forbidden runtime fields.
5. Independently annotate originals against frozen questions, then map evidence
   to exact sidecar cells. Annotators receive no retrieval traces or author's
   proposed answers. Record ambiguity, valid alternatives, disagreements and
   unmapped original evidence. Do not discard extraction failures. Any necessary
   question revision creates a new preserved revision before execution.
   Freeze every necessary component (including entity and qualifications), each
   acceptable alternative evidence set, and mapping/adjudication status. Any
   missing, unsupported or unresolved component prevents a complete-context pass;
   an empty required-cell list cannot pass vacuously. Preserve all selected cases
   and freeze eligibility/treatment for every metric before outcomes are visible.
6. Bind all artifacts in a run manifest. Recompute identities before running into
   a new directory. All 24 selected cases remain in the denominator. Search-only
   execution never opens annotations. Pending/failed cases survive interruption.
7. Freeze execution traces and their hashes before separate grading opens labels.
   Validate actual arguments, response hashes and source identities, not just a
   claimed success field. Preserve every attempt and any invalid-run receipt.

Every gate records its predecessor's byte hash, file inventory (relative path,
bytes, SHA-256), declared actors/context IDs and exposure categories. Commit each
stage. A later receipt may name the preceding commit; never create self-referential
manifest/commit hashes. Timestamps are descriptive, not chronology proof.

## Metrics and decision boundary

Report table hit@1/@3/@5, per-role required-cell coverage, complete context in one
read, no-hit/errors/overflows, response characters/bytes, and paired wins/losses.
Keep fixed denominators and show ambiguous or unmapped evidence separately rather
than treating it as a normal scorable gold answer. Report each issuer/document
and question stratum; do not collapse controls into search accuracy.

This first assessment establishes a broader diagnostic baseline. No search
version is automatically promoted by a single aggregate gain. Promotion criteria
and any successor experiment must be frozen before viewing its outcomes. Default
v2 remains unchanged. Annotation agreement is coding-agent review, not human
financial adjudication.

## Ingestion prerequisite discovered during planning

Synthetic review confirmed legacy `DocumentHTML` can include hidden numeric text,
let hidden headings alter section metadata, and reopen suppression on a mismatched
closing tag. Adjacent visible block numbers in one cell can also merge. Sidecar v2
already suppresses explicit hiding, but its visibility guarantee must not be
attributed to the legacy text path. Existing frozen corpus bytes remain unchanged.

Before new assessment corpus construction, choose and freeze a versioned text
extraction path or explicitly constrain the assessment to verified original-HTML
sidecars and mark legacy text ineligible as evidence. A future text fix should
reuse the bounded visibility predicate, preserve narrative/cell boundaries, reject
ambiguous suppression, and retain the legacy replay path. External CSS, conflicting
styles and rendered visibility remain unresolved. An opt-in `native-html-text-v2` repair now passes synthetic adversarial checks;
its version must be explicitly selected and frozen before acquisition. No new
assessment corpus has been declared ready.


## Proposed question matrix and capability controls

Each filing gets direct-statement, period/sign/scale, and two-operand slots (18
positive slots). Each older filing adds a table-plus-qualification slot (3),
including evidence that may lie outside the current read window. Each newer
filing adds an as-of availability control dated one calendar day before its
acceptance date (3). These controls concern availability of that selected filing,
not whether its underlying facts appeared earlier elsewhere. Ameren positive questions must name the consolidated parent;
its combined filing contains subsidiary registrants as well.

The 21 positive slots and three availability controls have separate denominators.
The current source-scoped table runner cannot enforce publication cutoffs: the
three controls are a declared capability gap, not passes and not ordinary table
recall misses. The broader 24-slot assessment cannot be called complete until
that control path is implemented and assessed. Runtime question schemas must not
silently accept unsupported cutoff fields. Final wording and slot assignments
remain uncreated pending the implementation/ingestion/grader freeze.

Metadata sources are the six SEC filing-index URLs in the proposal. The exact
acceptance strings and listed file sizes were checked on 2026-11-16; they are not
acquisition hashes or observed response lengths. Primary HTML, exhibits and
viewer wrappers remain unopened. Acquisition must record actual bytes, content
type, URL and time, and follow identified sequential SEC access. Do not infer a
UTC instant from a displayed timestamp without establishing its timezone.


## Implemented grading boundary

The runner now accepts a v2 protocol containing only an opaque assessment-receipt
hash in addition to its existing inputs. The separate grader verifies that receipt,
replays exact calls before opening labels, validates complete alternative evidence
sets and preserves mapped/unmapped/unresolved counts. It does not automatically
establish committed gate chronology, annotation adequacy or cutoff enforcement.
See the [schema and commands](../../table-runtime-design.md). No real assessment
has been executed. Metadata proposals were already inspected before the eventual
implementation freeze; that exposure must be retained, not described as blinded
issuer selection. Financial tables and question/answer evidence remain uninspected.
