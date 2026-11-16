# Native HTML assessment progress

The plan and gates are frozen snapshots. Record later outcomes here without
rewriting their byte identities.

## Frozen acquisition attempt 1

Implementation and selection were committed before requests: code `2b00126`,
[gate 0](gate-0-implementation.json), [gate 1](gate-1-selection.json), freeze commit
`16562f0`. The [first attempt](acquisition-attempt-1.json) received HTTP 403 for all
six selected primary URLs: **0/6 identity-verified downloads**. The
[gate 2 failure receipt](gate-2-acquisition-attempt-1.json) preserves all six cases.
No originals, corpus, publication observation bounds, questions, annotations or
retrieval results were created from these failures. This is an acquisition result,
not zero finance accuracy. No automatic retries or replacement documents occurred.
A later attempt requires a separately recorded policy decision and receipt.

## Access review after attempt 1

SEC requests a declared User-Agent and shows company name plus administrative
email as its example. The reviewed guidance does not establish that absence of an
email caused these 403s. No contact address was inferred or message sent to SEC.
[Access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
[developer guidance](https://www.sec.gov/about/developer-resources).

Independent metadata-only research found two candidate issuer-hosted HTML links
for the same Old Dominion accessions in its official filing list:

- https://ir.odfl.com/sec-filings/all-sec-filings/content/0000950170-25-103916/odfl-20250630.htm
- https://ir.odfl.com/sec-filings/all-sec-filings/content/0001193125-25-268415/odfl-20250930.htm

At that checkpoint, their bodies had not been fetched. Candidate accession/filename matches do not
establish byte equivalence with SEC originals; any alternate delivery artifact
requires its own URL/hash/receipt and an explicit new acquisition protocol. The
Casey's exact filing-detail pages were located, but later metadata views returned
403. Ameren's dynamic official list did not yet yield verified exact document
links. No PDF replacement, repeated SEC request, or alternate acquisition occurred.
The related source-ingestion chat is researching those remaining metadata routes.

## Alternate-delivery policy prepared before acquisition

The source-ingestion chat verified issuer-published HTML links for all six
selected filing identities from official listing/detail metadata, without opening
filing bodies. Casey's uses opaque node links; Ameren links to a CDN with opaque
HTML filenames; Old Dominion embeds the accession and primary filename in its
paths. The [delivery policy](issuer-delivery-policy-v1.json) records every exact
URL, metadata source and explicit link-identity convention. This is metadata
provenance, not proof of SEC-original byte equivalence.

The separate acquisition policy binds the unchanged selection and prior failed
receipt. It permits only the listed HTTPS delivery hosts/URLs, rejects credentials,
ports, path parameters, redirects and automatic fallbacks, and retains all six
source dispositions. Missing routes would issue no request. Existing HTTP/body
and DEI identity checks remain in force. The acquisition-only implementation
change requires an explicit amended runtime freeze; earlier gates remain intact.

If acquired, these files are **issuer-published delivery artifacts**, not verified
SEC-original bytes. Neither SEC `not_before` nor SEC `observed_by` automatically
transfers to them. Original SEC acceptance metadata stays separate. No existing
availability controls, original-source equivalence, corpus eligibility or financial
accuracy will be declared from matching CIK/form/period alone. The original
six-document assessment scope is preserved; alternate-artifact diagnostics are a
separate condition until their evidence and applicability are reviewed.

## Alternate-delivery attempt 2: partial acquisition

The acquisition-only amendment was committed as `119ab3f` before requests. The
[receipt](acquisition-attempt-2-issuer.json) and linked
[result gate](gate-2-acquisition-attempt-2-issuer.json) retain all six sources:
**2/6 identity-verified issuer copies**, both Old Dominion; Casey’s returned two
HTTP 403 responses, and Ameren returned two HTTP 200 bodies that failed the frozen
inline-XBRL identity verifier. No retries or replacements occurred.

Metadata-only inspection by an independent coding agent found both Ameren bodies
are generated EDGAR Online rXBRL viewer representations: viewer scripts/styles,
rendered identity rows, no actual inline-XBRL identity tags, and no selected
accession string. The rendered rows show the expected form, period and registrant,
but do not establish native filing geometry or SEC byte equivalence. Both bodies
remain rejected under the frozen policy; a rendered-document condition would
require its own protocol. Financial tables and answer cells were not inspected.

[Offline eligibility diagnostics](issuer-eligibility-attempt-2.json) extracted
585/588 text lines and 24 tables each from the two verified Old Dominion copies.
These counts establish extraction execution, not completeness or financial
semantics. [The local artifact inventory](issuer-artifact-inventory-attempt-2.json)
binds original/partial bytes, text, source manifests and geometry sidecars. Copies
carry their actual delivery URLs and acquisition observation upper bounds, with
no transferred SEC availability lower bound. The six-document assessment remains
incomplete: no questions, annotations, retrieval runs or model calls were created.
Both corpora were independently rebuilt offline from their recorded source metadata:
manifest/text bytes and parsed sidecars replayed exactly. The frozen plan and
runtime hashes still match their gates. Lint and all 247 tests passed for the
frozen implementation.

## Metadata research after partial acquisition

The related source-ingestion chat found no additional issuer route verified as
original filing HTML. Its Ameren archive-directory inspection found six XBRL
members in each official ZIP, without the selected primary `.htm`; Casey’s
quarterly archive led to earnings materials, not another selected 10-Q copy.
These are bounded negative research findings, not proof that no route exists.

The [submission candidates](submission-candidates.json) record the four unchanged
accessions' SEC complete-submission containers, based on official filing-index
metadata and documented archive paths. No submission bodies were requested.
A future attempt requires a separate freeze, transport/framing checks, exact
primary-member selection and dual container/member provenance. Access and byte
equivalence remain unverified. This metadata record is not an acquisition policy.

## Submission capture prepared

A bounded [container capture condition](submission-capture-notes.md) is implemented
for the four remaining official routes. It retains six cohort dispositions and
never declares primary extraction, identity verification or corpus eligibility.
The 32 MiB cap covers all four index-advertised sizes, including the two Ameren
containers above 20 MB. A separate gate must freeze the implementation and request
policy before any body requests.
