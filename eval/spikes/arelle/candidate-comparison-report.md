# Controlled Arelle 2.47.5 candidate comparison

The [release review](release-review-2026-11-16.md) nominated 2.47.5 for runtime
testing. This comparison retains the frozen 2.47.2 matrix and all source files.
It is a ten-scenario synthetic compatibility check, not issuer extraction or
financial accuracy, and does not promote any default tool.

## Controlled changes

An exploratory fresh install passed the scenarios but also changed transitive
dependencies: notably python-dateutil moved from 2.9.0.post0 to 4.0.0, six was
removed and tzdata appeared. That environment is not used for the controlled
result. The final harness explicitly rejects it.

[Candidate requirements](candidate-requirements.txt) pin all distribution versions
from the verified clean baseline except `arelle-release`, changed to 2.47.5.
Python remains 3.13.2. The harness verifies all 22 distributions reside inside
the candidate virtual environment and that system packages are disabled. Package
versions are controlled; this is not proof that every runtime byte is identical.

Two temporary adapter copies each receive exactly one declared replacement of
the runtime package-version guard from 2.47.2 to 2.47.5. Original/amended hashes
and unified diffs are recorded. The other six copied input files remain identical.
This changes the permitted runtime version without spoofing package metadata or
rewriting expectations. Temporary files are removed after execution.

Child Python environment overrides are cleared and user-site loading is disabled.
An import-origin probe verifies both adapters, both test helpers and the recorder
resolve to their exact temporary files, and Arelle resolves inside the candidate
environment. All processes inherit the same OS network-denial profile. Six
inspected Arelle source files are hashed and rechecked, alongside the unchanged
model-document and baseline bindings. This is not an exhaustive runtime manifest.

## Comparison rules

Run all fifteen guarded tests and the ten-scenario recorder in fresh processes.
Keep the complete candidate matrix. Compare every ordered case, including source
and dependency hashes, values, diagnostics, rejection messages, duplicate groups
and occurrence acceptance statuses. Remove only `result.adapter_code_sha256`
from case comparisons, after independently checking those hashes against the
two declared amended adapters. Top-level candidate input hashes must exactly
match all eight temporary files.

Outputs across versions are not claimed byte-identical: the adapter amendments
and runtime version intentionally differ. Reproduction within the same candidate
condition can be checked separately. Completed test/scenario failure output is retained before a nonzero
exit; setup errors and timeouts can raise before a failure artifact is written. A changed behavior requires review; because two tests deliberately expect
the old timezone defect, an upstream correction would be a divergence rather
than automatically a regression.

## Verified development observations

Independent implementation review reproduced all fifteen passing tests and all ten matching case records
under the explicit exclusion above. Negative fractional offsets remain rejected;
2.47.5 is not a timezone fix. Complete and consistent duplicates remain visible;
both members of the inconsistent pair remain quarantined. The core suite remains
399 tests and lint passes. The retained comparison embeds parsed candidate JSON, not the original matrix-file
bytes. This is a semantic comparison; retained-result byte reproduction is a
separate verification step.

Negative checks confirm that the uncontrolled dependency environment is rejected,
changed diagnostics and case ordering affect comparison, and only adapter-hash
metadata is excluded. The exact baseline and its requirements are hash-bound.

Under the OS-denial wrapper in [setup](README.md), use the controlled environment:

```sh
/path/to/controlled/bin/python eval/spikes/arelle/compare_candidate.py NEW_OUTPUT.json
```

Dimensions, continuations, broader transformations, equivalent-context duplicate
cases and rendered-cell provenance still require acceptance work before real
filing extraction. The newer runtime is a tested candidate for those development
steps, not a validated general financial ingestion system.

The harness was committed at `1f90d90` before writing the retained
[result](candidate-comparison-result.json). Its SHA-256 matches the independently
reproduced temporary record exactly:
`101b9449588e3d52e57878a960976ec05c7b8efc0fe869a11665dbd23d09cfa4`. [Verification](candidate-comparison-verification.json)
records the 22-distribution check, two gate amendments, 15 tests and 10 matched
cases. This same-condition byte reproduction is distinct from the explicitly
normalized cross-version semantic comparison.
