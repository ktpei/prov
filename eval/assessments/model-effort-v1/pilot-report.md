# Model/effort pilot: stopped before quality measurement

The frozen pilot at `1422bad` made one request from a clean checkout, then
stopped for billing review. No successful output or model-quality score exists.
This is a transport/measurement failure, not an incorrect financial answer.

The first row was Costco with DeepSeek low effort. The adapter recorded
`Comparison transport failed (ProviderError)` after approximately 0.159 seconds.
Its sanitizer retained the exception class but not the transport's safe HTTP
status/category, so the precise cause cannot be recovered from this artifact.
No provider response, generation ID or usage was received. Do not infer a
specific HTTP status, provider rejection reason or model incompatibility.

The runner stopped the remaining 15 rows without retries: eleven eligible
requests and four rows belonging to the predeclared 3M reference exclusion.
Those four rows carry the stop status because the loop never reached their
reference check; the frozen rubric remains authoritative for their exclusion.
All four arm identities and sixteen original rows remain in the durable ledger.
There are zero completed answers to send for blinded semantic grading.

The full $0.0132189 attempt reservation remains uncertain. Combined with
$0.4814193 historical conservative accounting, the authorization ledger is
$0.4946382 against the $1 limit. Read-only key checks before and after showed
no aggregate usage increase, but that is not request-specific billing proof
and does not release the reservation. No second attempt was made.

[pilot-result.json](pilot-result.json) records counts and local artifact hashes.
The earlier [infrastructure acceptance](infrastructure-report.md) remains an
offline result; it did not establish live compatibility. Shared-checkout lint
and 513 tests passed before the protocol commit. The continuous improvement
goal remains active. The next bounded cycle must preserve safe transport error
categories, reconcile the uncertain charge, and freeze any revised live protocol
before another comparison. No model promotion or accuracy gain is supported.
