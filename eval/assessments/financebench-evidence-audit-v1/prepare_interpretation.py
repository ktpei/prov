"""Prepare question-only review packets; reference and retrieval data are excluded."""

import hashlib
import json
from pathlib import Path

from provenance.benchmarks import canonical_hash

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INPUTS = ROOT / "runs/financebench-context-v1-preparation/prepared/inputs.json"
EXPECTED = "72b290d243e917b232e91114217f3997cf444a4e000c57f9b433f1d28072556f"


def project(inputs):
    if not isinstance(inputs, list) or len(inputs) != 6 or len({i["id"] for i in inputs}) != 6:
        raise ValueError("Expected exact six-case input set")
    ordered = sorted(
        inputs,
        key=lambda row: (
            canonical_hash([17, "evidence-audit-interpretation-v1", row["id"]]),
            row["id"],
        ),
    )
    questions, mapping = [], []
    for index, row in enumerate(ordered, 1):
        if not isinstance(row["question"], str) or not row["question"].strip():
            raise ValueError("Expected literal question text")
        case_id = f"Q{index:02d}"
        questions.append({"case_id": case_id, "question": row["question"]})
        mapping.append(
            {
                "case_id": case_id,
                "task_id": row["id"],
                "source_id": row["context"]["doc_name"],
                "original_index": inputs.index(row),
                "question_sha256": hashlib.sha256(row["question"].encode()).hexdigest(),
            }
        )
    return {"stage": "interpretation", "cases": questions}, {"mapping": mapping}


def prepare():
    paths = {
        "inputs": INPUTS,
        "builder": Path(__file__),
        "plan": HERE / "plan.md",
        "instructions": HERE / "reviewer-instructions.md",
    }
    raw = {key: path.read_bytes() for key, path in paths.items()}
    hashes = {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
    if hashes["inputs"] != EXPECTED:
        raise ValueError("Prepared input identity differs")
    questions, custody = project(json.loads(raw["inputs"]))
    if any(path.read_bytes() != raw[key] for key, path in paths.items()):
        raise ValueError("Interpretation input changed")
    output = HERE / "stage-1"
    output.mkdir(exist_ok=False)
    files = {"questions.json": questions, "custodian.json": custody}
    receipts, encoded_files = {}, {}
    for name, value in files.items():
        encoded = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
        encoded_files[name] = encoded
        (output / name).write_bytes(encoded)
        if (output / name).read_bytes() != encoded:
            raise ValueError("Written reviewer packet changed")
        receipts[name] = hashlib.sha256(encoded).hexdigest()
    if any(path.read_bytes() != raw[key] for key, path in paths.items()):
        raise ValueError("Interpretation input changed during write")
    receipt = {
        "version": "blinded-interpretation-preparation-v1",
        "inputs": hashes,
        "outputs": receipts,
        "cases": 6,
        "reference_or_retrieval_fields_in_reviewer_packet": False,
    }
    encoded_files["receipt.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    with (output / "receipt.json").open("xb") as handle:
        handle.write(encoded_files["receipt.json"])
    if {p.name for p in output.iterdir()} != set(encoded_files) or any(
        (output / name).read_bytes() != encoded for name, encoded in encoded_files.items()
    ):
        raise ValueError("Final reviewer packet inventory or bytes changed")
    if any(path.read_bytes() != raw[key] for key, path in paths.items()):
        raise ValueError("Interpretation input changed before completion")
    return receipt


if __name__ == "__main__":
    print(json.dumps(prepare()))
