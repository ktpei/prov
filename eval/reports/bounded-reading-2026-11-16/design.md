# Ranked parent reading: implementation and assessment design

Status: standalone reader, frozen benchmark runner and separate trace-replay
grader implemented and synthetically verified. The real three-case comparison is
not yet run. Execution rules are in plan.md; later outcomes belong in report.md.

The preceding component diagnostic found complete packets in selected parent
passages for 2/3 exposed tasks, but none in returned snippets. The next question
is whether bounded tool reads deliver those packets. It is not whether a model
uses them correctly. Existing retrieval reports, packets and scores stay frozen.

## Implemented policy

`ranked-parent-once-v1` accepts only ordered source-ID/start/end projections, at
most five. The caller must establish their provenance through exact search replay.
The reader rejects extra fields, unknown/nonlocal/changed text and invalid ranges
before issuing a call. It reads the exact parent bounds once per rank, without
expansion, continuation, retries, replacements or evidence-based stopping.

One five-slot execution supplies top-1/3/5 prefix measurements. Fewer available
hits remain fewer attempts. Ordinary tool range/size failures consume their slot;
unexpected exceptions, source mutation and forged responses abort the execution.
Interrupted journals retain the plan, completed responses and in-flight rank;
remaining planned slots are not silently executed or removed.

Each started call and result is flushed and fsynced to a new-only journal. Returned
source identity, original/text hashes, numbered lines, locations and locator must
match the frozen source. Deep snapshots prevent mutable metadata or later tool
responses from rewriting earlier results. Only exact returned complete lines
count; the requested range is not a substitute. Truncation compares actual end
to requested end; continuation hints are ignored even when non-null.

Record attempted/successful calls, requested lines, unique returned source lines,
gross text characters and canonical response JSON bytes. Repeated text counts
toward gross delivery cost but not unique coverage. The tool's 18,000-character
limit excludes JSON overhead/newline separators; it is not a token or byte cap.
This standalone baseline does not simulate the agent's 32K context projection.

## Pending assessment requirements

Before any real run, bind the implementation/runtime, exact corpus and prepared
files, saved search report and projected hit plan in a new protocol. Keep packet
labels out of the reader. Persist each task's outcome and retain all three cases,
including failures. A separate grader must replay search and complete read traces
before opening the already frozen component packets. Do not grade a merely
requested range or reconstruct missing response text from source files.

Report parent opportunity, original snippets and actual read responses separately.
Use the existing complete-alternative rule, per-role results, complete union and
single-response completeness. Any snippets-plus-reads union would be a separately
named condition. Actual read coverage must not exceed parent opportunity; complete
faithful reads should match it; prefix-union coverage must be nondecreasing.
Preserve the Ulta fiscal-year convention issue and posthoc development caveat.
No default promotion or semantic accuracy claim follows from these three cases.

## Research basis and interpretation

[KILT](https://aclanthology.org/2021.naacl-main.200.pdf) distinguishes provenance
retrieval from downstream answers and accommodates complete evidence sets. Its
page metric is not the present line-component metric.
[ALCE](https://aclanthology.org/2023.emnlp-main.398.pdf) separates answer correctness
from citation support and studies passage versus snippet inputs under context
limits. Its entailment-based citation metrics do not confer semantic meaning on
our deterministic line coverage.
[Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) shows that relevant
information's availability does not guarantee its successful use by the studied
models. Preserve delivery order and stop the current claim at evidence delivery.
These sources motivate distinctions, not a guarantee that this policy is optimal.

## Verification

Eleven synthetic tests cover successful prefixes, overlaps/duplicates, exact size
limits, truncation, failed first slots, zero hits, malformed plans, nonlocal text,
forged responses, interruption, mutable source metadata/text, response aliasing
and boolean-versus-integer identity changes.
All 289 repository tests and lint pass. Independent review found three mutation
hazards and a boolean/numeric equality bypass; all were fixed and independently
rechecked before any real reading experiment. No paid calls or
new benchmark source reads occurred in this implementation stage.

Runner/grader integration adds six synthetic tests for replay-before-packets,
forged reports/plans, journal/result/inventory tampering, interruption, changed
inputs and failed/empty prefix slots. All 295 tests and lint pass.
