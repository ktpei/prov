# Arelle release choice — checked 2026-11-16

Independent primary-source review by `/root/rubric_methodology`. No package was
installed and no issuer source was opened by this review. Runtime results remain
for 2.47.2; the newer release is only a candidate for a separate regression run.

[Official latest-release metadata](https://api.github.com/repos/Arelle/Arelle/releases/latest)
identified **2.47.5**, published November 12, 2026 at 20:30:21 UTC.
[PyPI's version record](https://pypi.org/pypi/arelle-release/2.47.5/json) reports the
wheel upload at 20:40:13 UTC and Python >=3.11. The
[release tag](https://api.github.com/repos/Arelle/Arelle/git/ref/tags/2.47.5) resolves
to commit `06e7a2d78b1b7426535a44e212276b86296da83a`.

The [2.47.5 XmlUtil implementation](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/XmlUtil.py#L987-L993)
still constructs timezone offsets from signed hours and unsigned minutes. Its
context path continues to use that helper through `datetimeValue`, as shown in
the [context implementation](https://github.com/Arelle/Arelle/blob/2.47.5/arelle/ModelInstanceObject.py#L1045-L1110).
The inspected [master commit](https://github.com/Arelle/Arelle/commit/12cb6e2d815ff64380dd939e5884874dad0b3dcb),
dated November 13, 2026, has the same affected file. Static inspection therefore
finds no release or inspected-development fix for the context-offset defect.

The reviewer fetched the published wheel into memory and verified its hash
against PyPI without installing or saving it:

`a878610b4804d6fa2eb26b97f0ed8fabbd67e38b68257d8e9bfa5f45d4f26bbe`

Its `XmlUtil.py`, inspected tags 2.47.2 through 2.47.5, and inspected master share:

`aadb36ed8a743c9934054eeef7fa8ecc6f58d94edfaa52f96ce27c6fc1dbef38`

[PR 2642](https://github.com/Arelle/Arelle/pull/2642), merged October 2, fixes
timezone preservation in XML Schema `g*` constructors using `ModelValue.tzinfo`.
It does not change the affected `XmlUtil.tzinfo` context path; those regression
tests do not prove this defect is fixed. Official tracker searches did not find
a specific report of this context-helper bug, which is not proof none exists.

Evaluate 2.47.5 through the same offline fixtures before adoption, preserving the
frozen 2.47.2 evidence. Do not call an upgrade a timezone repair. The independent
guard remains necessary until runtime evidence establishes correct boundaries.
Duplicate-warning loss was separately an adapter defect, addressed by guarded v2.
