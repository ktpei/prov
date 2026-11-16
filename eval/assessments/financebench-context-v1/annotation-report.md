# Six-case evidence annotation — 2026-11-16

All six selected cases have exact evidence-location packets, authored and
independently reviewed before any retrieval or context-retention result on this
cohort. The review covered ten full referenced physical pages; no adjacent-page
expansion was used. `mapped` means the necessary source lines were located, not
that the benchmark reference is a validated financial answer.

| Case | Source / physical pages | Required roles | Complete alternatives | Remaining interpretation issue |
| --- | --- | ---: | ---: | --- |
| 04209 | Costco 2021 / 38 | 4 | 1 | Dollar denomination follows question context |
| 04254 | American Water Works 2021 / 86, 88 | 8 | 1 | Question specifically selects cash-flow D&A |
| 00215 | Verizon 2022 / 23, 56 | 5 | 1 | Capital-intensity metric/threshold not stated |
| 03473 | Coca-Cola 2017 / 74, 76 | 6 | 2 | Consolidated versus shareowner net income |
| 01865 | 3M 2022 / 25 | 5 | 1 | M&A-only exclusion differs from organic growth |
| 00711 | Johnson & Johnson 2022 / 46, 47 | 6 | 1 | Reference uses cost of products sold / mean inventory |

The [packets](annotation/packets.json) preserve prepared task order and bind every
source's original and native-text hashes. The [receipt](annotation/receipt.json)
binds the preparation inputs, packets, primary notes and independent reviews.
Full-page render paths, commands and hashes remain in the primary notes; images
are retained under `runs/financebench-context-v1-annotation/`. Schema and exact
nonempty spans were validated using synthetic empty rows, without executing
retrieval. No financial score is inferred from that validation.

## Reference distinctions preserved

3M reports Consumer organic growth of -0.9%, while the other three segments have
positive organic growth. But removing only acquisitions/divestitures retains
currency translation: organic plus translation is negative for all four segments.
The reference therefore assumes a broader adjustment than the question explicitly
states. The packet retains all segment comparisons and adjustment columns; the
original question and answer remain unchanged and financially unadjudicated.

Coca-Cola reports consolidated net income of 1,283 million and shareowner net
income of 1,248 million. The reference uses the latter. Both divided by mean
assets of 87,583 million round to 0.01 as decimal ratios, hiding the distinction at
the requested precision. Each alternative requires its own complete income basis,
asset operands and statement/period/unit context; partial alternatives cannot mix.

Verizon's reference uses year-end total assets divided by annual revenue. The
source amounts map exactly, but the question does not specify the classification
threshold or that convention. This packet does not establish a universal
capital-intensity classification rule.

Johnson & Johnson's calculation is 31,089 / ((12,483 + 10,387) / 2), approximately
2.7 times. The 2022 balance-sheet column closes on January 1, 2023; calendar-year
assumptions must not silently replace the fiscal-year labels. American Water
Works requires cash-flow-statement D&A as requested, not an interchangeable
similarly named expense. Dollar/currency assumptions are explicit in the notes.

## Limits and next gate

These are coding-agent annotations and independent coding-agent reviews, not
human financial validation. Prepared gold and the frozen preparation's issue
registry snapshot remain unchanged; newly identified semantic caveats are carried
in these packets and notes. Existing semantic evaluation remains disabled.
Native text was visually checked only on the ten inspected pages; the five
empty-native-text pages elsewhere are still not established to be visually blank.

A separately frozen comparison must precede new retrieval. It will preserve the
six-case denominator, original questions, declared-document scope, exact ranked
parent reads, independent one/three/five-read snapshots, current 32K output-character
budget and unchanged baseline/challenger policies. No result-driven annotation
revision is allowed within this version. No paid calls, holdout runs or production
policy changes occurred in annotation.

## Later annotation-scope finding

A [saved-response diagnosis](../../retrieval-research-2026-11-16.md) found relevant
3M segment tables outside these frozen page-25 locations. These packets are not
exhaustive semantic judgments. No alternative was added and no result was regraded;
future alternative-evidence assessment requires a separate version and review.
