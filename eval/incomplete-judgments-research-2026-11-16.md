# Incomplete judgments and alternative evidence

Research reviewed on 2026-11-16. This document proposes an evaluation-validity
audit; it does not execute that audit, add accepted evidence alternatives, revise
annotations, or change any frozen score.

## What the existing result establishes

The compact-read assessment's five-read result of **1/6** measures coverage of
the complete, frozen source-location packets. It does not establish that the
other five delivered evidence sets are semantically insufficient, nor does a
location pass establish a correct financial answer.

The [saved-result diagnosis](assessments/financebench-compact-read-v1/retrieval-gap-diagnosis.json)
identifies potentially relevant 3M segment material outside the frozen locations.
It does not establish an independently sufficient alternative. The necessity of
the company-level comparison and the distinction between excluding M&A alone and
using organic growth remain unadjudicated. Relevant material, complete support,
and agreement with a benchmark reference are separate properties.

The [original preparation and annotation plan](assessments/financebench-context-v1/preparation-plan.md)
deliberately limited initial review to referenced pages and justified adjacent
context. That provides a reproducible location target, not an exhaustive census
of supporting evidence throughout each filing. Preserve that plan, its packets,
and all original results. Report annotation scope alongside the location score.

## Primary methodology findings

**Unjudged does not mean irrelevant.** Buckley and Voorhees show that conventional
retrieval measures can become unreliable under substantially incomplete relevance
judgments. Their `bpref` metric distinguishes judged negatives from unjudged
documents. It does not test whether multiple passages jointly provide all facts
and qualifications needed for a financial answer, and is not a replacement for
our complete-component metric. The paper also cautions about small numbers of
relevant documents and assumptions about which documents enter the judged pool.
[Retrieval Evaluation with Incomplete Information, SIGIR 2004](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=150469)

**Pooling is established practice, but shallow pools can be biased.** TREC combines
top results from multiple submitted runs for assessment. Its overview describes
leave-out-uniques analyses to examine sensitivity to judgments contributed by a
particular run. Separate research finds that insufficient pools can favor relevant
documents containing topic-title words. Pool diversity and depth matter; pooling
two policies that return identical passages adds no retrieval diversity.
[TREC 2021 overview](https://trec.nist.gov/pubs/trec30/papers/Overview-2021.pdf) ·
[Bias and the Limits of Pooling for Large Collections, 2007](https://www.nist.gov/publications/bias-and-limits-pooling-large-collections)

**Topical relevance is weaker than complete support.** TREC Deep Learning passage
guidelines distinguish passages that answer a query from passages merely related
to it. Our task additionally needs set-level sufficiency: compatible entities,
periods, units, operands, comparisons and material qualifications must jointly
support the declared interpretation. This additional requirement is our proposed
financial-evidence adaptation, not a claim that TREC's passage labels already
establish it.
[TREC 2020 Deep Learning overview, passage judging guidelines](https://trec.nist.gov/pubs/trec29/papers/OVERVIEW.DL.pdf)

**Incomplete judgments do not automatically invalidate system comparisons.**
An expanded TREC-8 assessment found system rankings nearly unchanged after judging
new results, with reported Kendall correlations above 0.99. The original collection
used deep, diverse pools and a substantial judgment budget. That finding does not
establish stability for six cases annotated around reference pages; it motivates
measuring sensitivity instead of assuming either robustness or invalidity.
[Can Old TREC Collections Reliably Evaluate Modern Neural Retrieval Models?, 2022](https://arxiv.org/abs/2201.11086)

**Judging after submission is not inherently invalid.** TREC separates development
data from evaluation data, collects system submissions, and then assesses results.
The crucial boundary is whether systems and evaluation procedures were fixed
before judgment feedback influenced them. A result-triggered audit of already
inspected development cases cannot recreate that prospective separation.
[How to TREC](https://trec.nist.gov/howto.html)

## Proposed separate all-six blinded audit

This is a proposal requiring its own frozen protocol before execution.
It uses saved results and leaves the historical evaluation untouched.

1. **Freeze scope and artifacts before judging.** Bind original protocols, packets,
   saved responses, originals, extracted text and location maps by hash. Include
   all six cases, not only suspected misses. Predeclare every contributing
   condition and the same depth of five saved reads. Deduplicate identical source
   spans and include the original annotated evidence as controls. No new retrieval
   is needed. Record pool construction and per-case pool size; do not claim that
   this small pool exhausts alternative evidence.

2. **Separate custody from judgment.** A custodian keeps the condition, rank,
   retention and original-label mappings. Two independent reviewers receive
   anonymized evidence in a fixed randomized order without policy attribution,
   old scores or the motivating diagnosis. Reviewers need a fresh context;
   participants in the outcome diagnosis cannot claim to be outcome-blind.
   Randomization and masked attribution reduce opportunities for favoritism but
   do not guarantee unbiased judgment. The source identity and context necessary
   to interpret the evidence must remain available.

3. **Fix the information need before showing pooled evidence.** Reviewers first
   document question interpretations, required facts and unresolved ambiguity.
   Keep the benchmark reference out of this first interpretation pass; subsequently
   record agreement or disagreement with it separately. For the known 3M issue,
   distinguish excluding M&A alone from organic growth and define the comparison
   implied by overall growth. Do not remove a company-level requirement merely
   because returned passages lack it. If interpretation cannot be resolved, retain
   separate declared interpretations or an unresolved disposition rather than
   selecting the one that improves a score.

4. **Judge components and complete alternatives.** Record supported roles, missing
   roles, contradictions and uncertainty. Each accepted alternative must satisfy
   every required role under one declared interpretation; fragments from
   incompatible alternatives cannot be combined. Evidence distributed across
   pages may qualify if entity, period, metric and unit relationships are supported.
   Source spans must remain exact and bound to original/text hashes. Predeclare
   any original-page review needed for headers, units or qualifications, including
   scope limits and stopping rules. Such review context is not delivered evidence
   and receives no retrieval credit unless present in the actual saved response.

5. **Lock judgments before revealing condition attribution.** Preserve both initial
   reviews and resolve disagreements through an independent third reviewer.
   Freeze adjudicated alternatives and reasons before the custodian maps them to
   policies or reports score changes. Apply the same locked judgments to every
   condition and prefix. Coding-agent review must be labeled as such; it does not
   establish human financial validation.

6. **Publish a new diagnostic beside the old results.** Retain all-six denominators,
   operational failures and unresolved cases. Report original-location coverage,
   coverage under adjudicated alternatives, reviewer disagreement, pool scope and
   the provenance of every accepted alternative. Score only evidence actually
   delivered or retained by each condition, never the entire pooled evidence set.
   A pass under newly mapped alternatives is still a coverage result unless
   semantic sufficiency has separately been adjudicated. No claim of financial
   answer accuracy follows from replay or location matching alone.

## Alternative locations versus changed requirements

An **alternative-location addition** supplies another independently complete set
of source spans for the same required roles and interpretation. A **rubric
revision** changes an interpretation or adds, removes or changes required roles.
These must have separate recorded versions and reasons. A revision must not be
presented as merely filling a missing location judgment.

Keep original packet bytes and scores immutable in both cases. Record before/after
requirements, independent rationale, disagreements and the scope of re-evaluation.
Adjudication may reject a proposed alternative, retain ambiguity, or find the old
requirements overly restrictive; none of those outcomes should be predetermined.

The current audit would remain **post-hoc development diagnostics** because an
observed result motivated it. Blinding new reviewers does not make the cohort
untouched again, and one successful alternative would not establish completeness
of the expanded judgment set or general superiority of a retrieval policy.

## How prospective validation should differ

Reserve unexposed source/company groups using metadata only, preserve existing
partition rules and exposure exclusions, and freeze the retrieval policy before
opening validation content. Keep policy developers separate from annotation and
adjudication, with no label or outcome feedback before submissions are locked.

Prefer an independent, outcome-blind source annotation pass under a predeclared
scope broad enough to investigate alternatives beyond reference pages. Freeze
interpretation rules, review budgets, ambiguity handling, stopping rules and
complete-evidence criteria in advance. Record unresolved evidence and scope
limits rather than claim exhaustive annotation.

Prospectively pooled validation is also defensible: predeclare participating
systems, equal pooling depths, any independent source-review supplement, blinding,
adjudication and analysis before runs; lock all submissions before judging; then
apply the same judgments to all systems. This is judging after frozen submission,
not changing judgments after inspecting which system benefits. It must be described
accurately rather than claimed to have had labels frozen before retrieval.

Report the sensitivity of conclusions to alternative judgments and pool coverage.
With six cases, do not infer broad ranking stability from TREC's larger studies.
Once validation outcomes guide another policy or rubric change, that set becomes
development evidence for the next cycle; use a separately untouched set for a new
confirmatory claim.

## Scope of this research cycle

Reviewed the saved diagnosis and existing annotation plan plus the primary
methodology sources linked above. No new FinanceBench examples, source-document
reads, retrieval experiments, model calls, annotation changes or score changes
were performed. The audit and prospective validation designs remain unexecuted.
