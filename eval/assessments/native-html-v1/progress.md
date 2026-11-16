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

Their bodies have not been fetched. Candidate accession/filename matches do not
establish byte equivalence with SEC originals; any alternate delivery artifact
requires its own URL/hash/receipt and an explicit new acquisition protocol. The
Casey's exact filing-detail pages were located, but later metadata views returned
403. Ameren's dynamic official list did not yet yield verified exact document
links. No PDF replacement, repeated SEC request, or alternate acquisition occurred.
The related source-ingestion chat is researching those remaining metadata routes.

## Alternate-delivery policy prepared before acquisition

The source-ingestion chat verified issuer-published native-HTML links for all six
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
