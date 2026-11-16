# Pinned TAT-QA metric source

Upstream: https://github.com/NExTplusplus/TAT-QA
Revision: `870accc41953dcde885aabeb963d94aabdc0fbc3`.
Code license: MIT, Copyright (c) 2021 Fengbin Zhu; full notice in `LICENSE`.
Dataset licensing is separate (CC BY 4.0) and no dataset is vendored here.

| Original file | Original SHA256 |
| --- | --- |
| `tatqa_metric.py` | `2aeeac479f89f8c76300af1cc0e8d098eb86af84bc386b38b6ab4af484a6dea8` |
| `tatqa_utils.py` | `a84bb2f960737cf0a53733637a674cc4b20ef030a2be6a4b21dc2c4356f415ec` |
| `LICENSE` | `46e27ffbc49c3fd44a9595c2213f8a5f4319a81b53238e49ce1eec39e7e25662` |

Only upstream code modification: `from tatqa_utils import *` becomes
`from .tatqa_utils import *` for package-relative loading. Tests reverse that one
change and verify the original hashes. The original formatting and regex escape
strings remain; Python may report upstream SyntaxWarnings when compiling them.
Ruff excludes this frozen third-party directory.

The first-party wrapper in `provenance/official_metrics.py` validates prediction
shape/size, converts finite JSON numeric values to plain decimal strings (preserving zero
and preventing upstream scientific-notation mantissa misparsing), rejects
scientific-notation strings and all-blank lists, and reports EM, F1, and scale
accuracy separately. These are explicit wrapper-v2 adaptations; the vendored
metric itself is unchanged. It does not execute
programs, download code, or establish semantic support. Install the locked
`benchmark-metrics` extra to use this scorer. Repository tests install that extra.
