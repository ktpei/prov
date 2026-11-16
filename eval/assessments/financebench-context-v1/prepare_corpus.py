"""Prepare six frozen tasks and ingest their verified local originals without retrieval."""

import argparse
import copy
import json
import re
from pathlib import Path

from eval.scripts.parent_read_assessment import _write
from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmark_adapters import adapt_records
from provenance.benchmarks import canonical_hash, prepare, score_run
from provenance.evidence_coverage import digest
from provenance.ingestion import _package_version, ingest
from provenance.reference_issues import apply_reference_issues
from provenance.sources import Sources

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ACQUIRED = ROOT / "runs/financebench-context-v1-acquisition"
DATA = ROOT / "runs/benchmark-data/financebench-public-v2"


def execute(protocol_path, output):
    protocol_path, output = Path(protocol_path), Path(output)
    raw = protocol_path.read_bytes()
    protocol = _load_object(raw, "Preparation protocol")
    _require_exact_keys(
        protocol,
        {"version", "runtime_sha256", "files_sha256", "package_versions"},
        "Preparation protocol",
    )
    if protocol["version"] != "financebench-context-preparation-v1":
        raise ValueError("Unsupported preparation protocol")
    expected_paths = {
        "eval/assessments/financebench-context-v1/prepare_corpus.py",
        "eval/assessments/financebench-context-v1/preparation-plan.md",
        "eval/assessments/financebench-context-v1/selection.json",
        "eval/assessments/financebench-context-v1/acquisition-result.json",
        "eval/development-exposures.json",
        "eval/reference-issues.json",
        "runs/benchmark-data/financebench-public-v2/financebench-public.jsonl",
        "runs/benchmark-data/financebench-public-v2/source.json",
    }
    selection = _load_object((HERE / "selection.json").read_bytes(), "Selection")
    receipt = _load_object((HERE / "acquisition-result.json").read_bytes(), "Acquisition")
    for selected in selection["selected"]:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", selected["doc_name"]):
            raise ValueError("Unsafe selected document name")
        expected_paths.add(f"runs/financebench-context-v1-acquisition/{selected['doc_name']}.pdf")
    _require_exact_keys(protocol["files_sha256"], expected_paths, "Preparation file identities")

    def verify():
        if (
            protocol_path.read_bytes() != raw
            or runtime_digest() != protocol["runtime_sha256"]
            or {name: _package_version(name) for name in ["pypdf", "fonttools"]}
            != protocol["package_versions"]
            or any(
                digest(ROOT / name) != expected
                for name, expected in protocol["files_sha256"].items()
            )
        ):
            raise ValueError("Preparation frozen identity mismatch")

    verify()
    selected = selection["selected"]
    if (
        len(selected) != 6
        or len({s["task_id"] for s in selected}) != 6
        or len({s["doc_name"] for s in selected}) != 6
    ):
        raise ValueError("Expected six unique selected slots")
    if (
        receipt["status"] != "complete"
        or receipt["verified_count"] != 6
        or [s["doc_name"] for s in selected] != [d["doc_name"] for d in receipt["documents"]]
    ):
        raise ValueError("Acquisition does not cover exact selection")
    for source, acquired in zip(selected, receipt["documents"], strict=True):
        if (
            acquired["status"] != "verified_blob"
            or acquired["task_id"] != source["task_id"]
            or acquired["file"] != source["doc_name"] + ".pdf"
            or digest(ACQUIRED / acquired["file"]) != acquired["sha256"]
            or int(canonical_hash([17, source["doc_name"]])[:8], 16) % 5 == 0
        ):
            raise ValueError("Acquired identity or original development assignment mismatch")
    exposures = _load_object((ROOT / "eval/development-exposures.json").read_bytes(), "Exposures")
    groups = [r["group"] for r in exposures["groups"]]
    if any(s["doc_name"] not in groups for s in selected):
        raise ValueError("Selected source lacks development reservation")
    source = _load_object((DATA / "source.json").read_bytes(), "Release source")
    if (
        source["sha256"] != digest(DATA / "financebench-public.jsonl")
        or source["sha256"] != selection["task_sha256"]
        or source["revision"] != selection["revision"]
    ):
        raise ValueError("Release identity mismatch")
    ids = {s["task_id"] for s in selected}
    records = [
        r
        for r in map(json.loads, (DATA / "financebench-public.jsonl").read_text().splitlines())
        if r["financebench_id"] in ids
    ]
    if len(records) != 6 or any(
        next(s["doc_name"] for s in selected if s["task_id"] == r["financebench_id"])
        != r["doc_name"]
        for r in records
    ):
        raise ValueError("Selected release rows mismatch")
    tasks = adapt_records(
        "financebench", records, subset=source["subset"], source_split=source["source_split"]
    )
    issues = _load_object((ROOT / "eval/reference-issues.json").read_bytes(), "Reference registry")
    tasks, applied = apply_reference_issues(tasks, source, issues)
    bundle = prepare(
        tasks, source=source, count=6, seed=17, condition="full_agent", development_groups=groups
    )
    if bundle["manifest"]["selected_ids"] != selection["prepared_order_ids"]:
        raise ValueError("Prepared order differs from frozen selection")
    bundle["manifest"].update(
        development_exposures_sha256=canonical_hash(exposures),
        reference_registry_sha256=canonical_hash(issues),
        applied_reference_issues=applied,
        selection_sha256=digest(HERE / "selection.json"),
    )
    score_run(bundle, {"prepared_sha256": canonical_hash(bundle["manifest"]), "predictions": []})
    verify()
    output.mkdir(exist_ok=False)
    result = {
        "version": "financebench-context-preparation-result-v1",
        "protocol_sha256": digest(protocol_path),
        "status": "running",
        "selected_denominator": 6,
        "prepared_ids": selection["prepared_order_ids"],
        "prepared_files_sha256": None,
        "documents": [{"id": s["doc_name"], "status": "pending"} for s in selected],
        "retrieval_executed": False,
        "annotations_authored": False,
    }
    _write(output / "preparation.json", result)
    manifests = []
    try:
        (output / "prepared").mkdir()
        for key, value in bundle.items():
            _write(output / "prepared" / (key + ".json"), value)
        prepared_hashes = {
            name: digest(output / "prepared" / name)
            for name in ["manifest.json", "tasks.json", "inputs.json"]
        }
        result["prepared_files_sha256"] = prepared_hashes
        _write(output / "preparation.json", result)
        for source, acquired, case in zip(
            selected, receipt["documents"], result["documents"], strict=True
        ):
            verify()
            case["status"] = "running"
            _write(output / "preparation.json", result)
            sid = source["doc_name"]
            directory = output / "corpus" / "parts" / sid
            spec = {
                "id": sid,
                "title": sid,
                "company": source["company"],
                "doc_type": source["doc_type"],
                "doc_period": source["doc_period"],
                "url": source["doc_link"],
                "download_url": acquired["url"],
                "dataset_revision": selection["revision"],
                "published": None,
                "retrieved": acquired["finished_at"][:10],
                "availability_note": "Mirror acquisition observation is not a verified publication date.",
                "input_file": str(ACQUIRED / acquired["file"]),
            }
            try:
                manifest = ingest({"sources": [spec]}, directory)
                Sources(directory)
                if manifest["sources"][0]["original_sha256"] != acquired["sha256"]:
                    raise ValueError("Extracted original differs from acquired bytes")
            except Exception as error:
                case.update(status="failed", error=f"{type(error).__name__}: {error}"[:1000])
            else:
                item = copy.deepcopy(manifest["sources"][0])
                for field in ["text_file", "original_file"]:
                    item[field] = f"parts/{sid}/{item[field]}"
                manifests.append(item)
                case.update(
                    status="extracted",
                    original_sha256=item["original_sha256"],
                    text_sha256=item["sha256"],
                    source_manifest_sha256=digest(directory / "sources.json"),
                    page_count=item["extraction"]["page_count"],
                    line_count=len(item["line_locations"]),
                    empty_native_text_pages=item["extraction"]["empty_native_text_pages"],
                    warning_count=item["extraction"]["warning_count"],
                    text_completeness="not_verified",
                )
            _write(output / "preparation.json", result)
        verify()
        if any(
            digest(output / "prepared" / name) != expected
            for name, expected in prepared_hashes.items()
        ):
            raise ValueError("Prepared files changed during extraction")
        for case in result["documents"]:
            if case["status"] == "extracted":
                directory = output / "corpus" / "parts" / case["id"]
                if digest(directory / "sources.json") != case["source_manifest_sha256"]:
                    raise ValueError("Per-source manifest changed during extraction")
                Sources(directory)
        if len(manifests) == 6:
            corpus = output / "corpus"
            _write(corpus / "sources.json", {"version": "2", "sources": manifests})
            checked = Sources(corpus)
            binding = {
                "version": "financebench-full-documents-v2",
                "prepared_sha256": canonical_hash(bundle["manifest"]),
                "dataset_revision": selection["revision"],
                "sources_manifest_sha256": digest(corpus / "sources.json"),
                "source_ids": sorted(checked.documents),
                "source_hashes": {sid: d["sha256"] for sid, d in checked.documents.items()},
                "original_hashes": {
                    sid: d["original_sha256"] for sid, d in checked.documents.items()
                },
                "selection_sha256": digest(HERE / "selection.json"),
                "acquisition_sha256": digest(HERE / "acquisition-result.json"),
                "limitations": [
                    "Native extraction is not verified financial completeness.",
                    "No publication-availability claim.",
                ],
            }
            _write(corpus / "benchmark_binding.json", binding)
            result.update(
                status="complete",
                corpus_manifest_sha256=digest(corpus / "sources.json"),
                corpus_binding_sha256=digest(corpus / "benchmark_binding.json"),
            )
        else:
            result.update(
                status="blocked_extraction",
                reason="Retain all six slots; corpus assessment cannot proceed.",
            )
        result["extracted_count"] = len(manifests)
        _write(output / "preparation.json", result)
    except BaseException as error:
        result.update(
            status="invalidated" if isinstance(error, Exception) else "interrupted",
            error_type=type(error).__name__,
        )
        _write(output / "preparation.json", result)
        raise
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = execute(args.protocol, args.output)
    print(
        json.dumps(
            {"status": result["status"], "selected": 6, "extracted": result["extracted_count"]}
        )
    )
