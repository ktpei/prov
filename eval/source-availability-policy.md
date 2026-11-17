# Selected-source availability controls

This policy gates one exact artifact in its declared source location. It does not
claim that the artifact's financial facts were unavailable through other channels,
that the document remains continuously online, or that an agent has reasoned
correctly about an as-of question.

SEC acceptance is not an exact public-availability timestamp. SEC describes a
usual but unguaranteed lag before documents appear on its website and says it does
not supply a timestamp for first website availability. Do not invent an upper
bound by adding a typical delay. [SEC Webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions).

## Bound semantics

A source manifest may include `availability` with exactly `original_sha256`,
`not_before`, `observed_by`, and `basis`. The hash must match that source's original
bytes. `basis` records the evidence claim; the evaluator does not independently
verify its truth. Each bound is null or an explicit-offset timestamp. Missing
metadata means no temporal evidence, not proof of nonpublication.

- Before `not_before`: `not_yet_available`, blocked.
- At or after `observed_by`: `available`, permitted.
- Between bounds, or without a bound establishing either conclusion: `unknown`, blocked.
- A null question cutoff: `not_requested`, permitted; malformed metadata still fails validation.

Equal bounds identify an exact declared transition. Reversed bounds, malformed
fields or a wrong original hash invalidate input. Comparisons use timezone-aware
instants, not string ordering. The supported timestamp profile requires seconds,
`Z` or an explicit numeric offset, and at most six fractional digits. Naive times,
date-only strings, overflowing timezone minutes and leap seconds are rejected.
The numeric-offset semantics follow [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339).

## Proposed EDGAR assessment convention

For the three prior-calendar-day controls, use midnight at the beginning of the
acceptance calendar date in `America/New_York`, serialized with that date's actual
numeric offset, as a deliberately loose `not_before` bound. This is an assessment
convention for the selected accession's EDGAR publication, not an interpretation
of every API timestamp. SEC describes acceptance before public dissemination;
official filing rules distinguish Eastern Standard and Daylight time.
[Dissemination overview](https://www.sec.gov/files/info/edgar/pdsnewsubscriber.pdf),
[filing-hours/date rules](https://www.govinfo.gov/content/pkg/CFR-2025-title17-vol3/pdf/CFR-2025-title17-vol3-sec232-13.pdf).

The previous day is the preceding Eastern calendar date, not a fixed 24-hour
subtraction across daylight-saving transitions. Bind the accession, document URL
and original hash in acquisition records. `observed_by` must come from successful
retrieval of those exact bytes. Observing a filing today does not establish that
it was available at a historical cutoff. Do not use period end, index visibility,
filename, or an assumed acceptance delay as a substitute. No bounds for the six
proposed filings have yet been declared acquired/verified.

## Runner and grading integration

`table-assessment-run-protocol-v3` retains the opaque receipt commitment and uses
`table-assessment-questions-v2`. Every question has exactly `id`, `source_id`,
`question`, and `as_of`; positive cases use null, controls use timestamps. Metadata
is checked before tool calls. Blocked cases have status `availability_blocked` and
zero traces; no sibling filing is substituted. An entirely blocked run does not
construct table retrieval. Existing non-temporal protocols remain supported.

`table-assessment-annotations-v2` adds the `availability_control` disposition.
Controls require a cutoff, reason and `expected_availability` state, and have empty
financial role/alternative lists. Positive annotations require a null cutoff.
The grader independently recomputes eligibility and requires zero calls for blocked
cases or the normal exact search/read replay for allowed cases. It reports
availability-control outcomes separately from positive and mapped denominators.
An `unknown` control can validate conservative blocking without asserting that the
filing was definitely unpublished. Controls never count as complete financial
context passes.

Synthetic checks cover both blocked and permitted access, uncertainty, missing
bounds, exact endpoints, offset equivalence, invalid metadata even without a
cutoff, wrong source hashes, malformed offsets, and forged always-blocking traces.
These tests do not establish metadata authenticity or real filing accuracy. The
new cohort remains unacquired, unannotated and unrun.
