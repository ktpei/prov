# Complete-submission capture condition

This condition tests delivery of the four metadata-verified SEC submission
containers, preserving the same six selected filing identities. The two existing
Old Dominion issuer copies are not fetched again. Captured containers are
**unverified bytes**, never primary filing evidence or an eligible corpus.
No document members are extracted by this capture path.

Independent metadata research found these advertised complete-submission sizes:

| Source | Index-advertised bytes | Index document count |
| --- | ---: | ---: |
| Casey’s July | 2,884,074 | 44 |
| Casey’s October | 3,154,371 | 45 |
| Ameren June | 20,859,766 | 109 |
| Ameren September | 21,181,149 | 108 |

The exact official index URLs are in [the candidate record](submission-candidates.json).
These are metadata claims, not verified downloaded lengths. Their total is
48,079,360 bytes. A 32 MiB per-response cap accommodates each advertised size;
it is a local assessment resource limit, not an SEC limit.

Capture freezes exact routes and input/code hashes before requests. Each candidate
gets one sequential GET with identity encoding; redirects, retries and ranged
requests are disabled. Socket operations time out after 20 seconds. A 120-second
elapsed limit is checked between response reads. Header/chunk parsing may perform
multiple socket reads, so this is not a hard total-duration bound. Response bytes are bounded in memory, then written
without decoding or newline normalization. A one-byte overflow probe is retained
and counted explicitly in the partial-file size. New output directories only.

Receipts preserve all six dispositions, HTTP metadata, start/end/elapsed times,
EOF observation, byte counts, hashes and bounded partials. Failed candidates are
not replaced. A successful transport is `captured_unverified`, including a body
that might later prove invalid. Neither HTTP 200, EOF, matching Content-Length,
nor matching index length proves identity or intact submission framing.

[SEC archive guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
describes the complete disseminated submission route. The
[PDS specification](https://www.sec.gov/info/edgar/specifications/pds_dissemination_spec.pdf)
describes concatenated originals, generated renderings and encoded attachments;
its stream control-block rules must not be presumed to describe archive `.txt`
wrappers exactly. A later extractor needs a separate verified format policy,
unique exact primary-member selection, container/member hashes and offsets, and
independent filing identity checks. Reachability and primary-file equivalence
remain unverified before the capture attempt.

Five synthetic capture tests cover failed HTTP responses, wrong URLs and member
metadata, oversize bodies, wrong media, declared-length mismatch, elapsed limits,
interruption, output reuse, and zero identity promotion. Lint and all 264 tests pass.
