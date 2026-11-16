"""Separate, hash-bound grading of frozen native-table assessment traces."""

import argparse
import json
import math
from pathlib import Path

from eval.scripts.table_assessment_run import (
    _canonical,
    _digest,
    _load_object,
    _native_html_source_ids,
    _require_exact_keys,
    _status_counts,
    _validate_protocol,
    _validate_questions,
    runtime_digest,
)
from provenance.sources import Sources
from provenance.table_structure import extract_html_tables
from provenance.table_tools import TableSources


def _same(actual, expected, message):
    if _canonical(actual) != _canonical(expected):
        raise ValueError(message)


def _verify_trace(trace, tool, arguments, response):
    if not isinstance(trace, dict):
        raise ValueError("Trace must be an object")
    serialized = _canonical(response)
    for key, expected in {
        "tool": tool,
        "args": arguments,
        "response": response,
        "response_canonical_sha256": _digest(serialized.encode()),
        "response_unicode_characters": len(serialized),
        "response_utf8_bytes": len(serialized.encode()),
    }.items():
        _same(trace.get(key), expected, f"Trace replay mismatch: {key}")
    latency = trace.get("latency_seconds")
    if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
        raise ValueError("Invalid recorded trace latency")


def _verify_execution(run_protocol, questions, report, corpus):
    if (
        report.get("version") != "table-assessment-run-report-v1"
        or report.get("runtime_version") != "table-assessment-run-runtime-v1"
        or report.get("run_status") != "completed"
        or report.get("post_run_integrity_verified") is not True
    ):
        raise ValueError("Only completed integrity-verified runs can be graded")
    for key in ("questions_sha256", "corpus_manifest_sha256", "runtime_sha256", "search_version"):
        _same(report.get(key), run_protocol[key], f"Run identity mismatch: {key}")
    _same(report.get("model_calls"), 0, "Unexpected model calls")
    _same(report.get("task_denominator"), len(questions), "Run denominator mismatch")
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != len(questions):
        raise ValueError("Run cases missing or duplicated")
    tables = TableSources(corpus, search_version=run_protocol["search_version"])
    for question, case in zip(questions, cases, strict=True):
        if not isinstance(case, dict):
            raise ValueError("Invalid run case")
        for key in ("id", "source_id", "question"):
            _same(case.get(key), question[key], "Run question identity/order mismatch")
        trace = case.get("trace")
        if not isinstance(trace, list) or not trace:
            raise ValueError("Run case requires an actual search trace")
        arguments = {"source_id": question["source_id"], "query": question["question"]}
        search = tables.call("search_tables", arguments, timeout=10)
        _verify_trace(trace[0], "search_tables", arguments, search)
        expected_count = 1
        if "error" in search:
            status = "search_error"
            error = search["error"]
        elif not search["results"]:
            status = "no_hit"
            error = None
        else:
            expected_count = 2
            if len(trace) != 2:
                raise ValueError("Exactly one read required after a search hit")
            hit = search["results"][0]
            arguments = {
                "source_id": question["source_id"],
                "table_id": hit["table_id"],
                "row_indices": hit["matched_row_indices"][:3],
            }
            read = tables.call("read_table", arguments, timeout=10)
            _verify_trace(trace[1], "read_table", arguments, read)
            error = read.get("error")
            status = "read_error" if "error" in read else "completed"
        if len(trace) != expected_count or case.get("status") != status:
            raise ValueError("Run trace count/status mismatch")
        if error is not None:
            _same(case.get("error"), error, "Run error differs from tool response")
        elif "error" in case:
            raise ValueError("Unexpected error on successful observation")
    _same(report.get("status_counts"), _status_counts(cases), "Run status counts mismatch")
    return cases


def _validate_annotations(annotations, questions, sources, corpus, run_protocol):
    _require_exact_keys(
        annotations,
        {"version", "questions_sha256", "corpus_manifest_sha256", "sources", "cases"},
        "Annotations",
    )
    if annotations["version"] != "table-assessment-annotations-v1":
        raise ValueError("Unsupported annotations")
    for key in ("questions_sha256", "corpus_manifest_sha256"):
        _same(annotations[key], run_protocol[key], "Annotation identity mismatch")
    source_ids = {case["source_id"] for case in questions}
    bindings = annotations["sources"]
    if not isinstance(bindings, dict) or set(bindings) != source_ids:
        raise ValueError("Annotation source set mismatch")
    cells = {}
    for source_id in sorted(source_ids):
        source = sources.documents[source_id]
        sidecar = extract_html_tables(corpus / source["original_file"])
        _same(
            bindings[source_id],
            {
                "original_sha256": sidecar["original_sha256"],
                "sidecar_version": sidecar["version"],
                "sidecar_sha256": _digest(_canonical(sidecar).encode()),
            },
            "Annotation sidecar identity mismatch",
        )
        cells[source_id] = {
            table["id"]: {
                cell["id"]: cell
                for row in table["rows"]
                for cell in row["cells"]
                if cell["text"] and cell["visibility"] != "explicitly_hidden"
            }
            for table in sidecar["tables"]
        }
    cases = annotations["cases"]
    if not isinstance(cases, list) or len(cases) != len(questions):
        raise ValueError("Annotation case denominator mismatch")
    for question, case in zip(questions, cases, strict=True):
        if not isinstance(case, dict):
            raise ValueError("Annotation case must be an object")
        _require_exact_keys(
            case,
            {"id", "source_id", "disposition", "required_components", "alternatives", "reason"},
            "Annotation case",
        )
        for key in ("id", "source_id"):
            _same(case[key], question[key], "Annotation case identity/order mismatch")
        roles = case["required_components"]
        if (
            not isinstance(roles, list)
            or not roles
            or any(not isinstance(role, str) or not role.strip() for role in roles)
            or len(set(roles)) != len(roles)
        ):
            raise ValueError("Required evidence components must be unique and nonempty")
        if case["disposition"] not in ("mapped", "unmapped", "unresolved"):
            raise ValueError("Invalid annotation disposition")
        if not isinstance(case["reason"], str):
            raise ValueError("Annotation reason must be a string")
        alternatives = case["alternatives"]
        if case["disposition"] != "mapped":
            if alternatives != [] or not case["reason"].strip():
                raise ValueError(
                    "Unmapped/unresolved cases require a reason and no partial alternatives"
                )
            continue
        if not isinstance(alternatives, list) or not alternatives:
            raise ValueError("Mapped cases require complete evidence alternatives")
        seen_alternatives = set()
        for alternative in alternatives:
            if not isinstance(alternative, dict):
                raise ValueError("Evidence alternative must be an object")
            _require_exact_keys(alternative, {"table_id", "components"}, "Evidence alternative")
            identity = _canonical(alternative)
            if identity in seen_alternatives:
                raise ValueError("Duplicate evidence alternative")
            seen_alternatives.add(identity)
            table_id = alternative["table_id"]
            if not isinstance(table_id, str) or table_id not in cells[case["source_id"]]:
                raise ValueError("Evidence table absent")
            components = alternative["components"]
            if not isinstance(components, dict) or set(components) != set(roles):
                raise ValueError("Each alternative must cover every required component")
            for identities in components.values():
                if (
                    not isinstance(identities, list)
                    or not identities
                    or any(not isinstance(identity, str) for identity in identities)
                    or len(set(identities)) != len(identities)
                    or any(
                        identity not in cells[case["source_id"]][table_id]
                        for identity in identities
                    )
                ):
                    raise ValueError("Evidence component must map to nonempty visible cells")
    return cases


def grade(
    protocol_path,
    run_protocol_path,
    questions_path,
    report_path,
    annotations_path,
    receipt_path,
    corpus,
    output,
):
    """Verify frozen execution before opening evaluator annotations; never alter inputs."""
    paths = {
        "run_protocol": Path(run_protocol_path),
        "questions": Path(questions_path),
        "report": Path(report_path),
        "annotations": Path(annotations_path),
        "receipt": Path(receipt_path),
    }
    corpus, output = Path(corpus), Path(output)
    protocol_raw = Path(protocol_path).read_bytes()
    protocol = _load_object(protocol_raw, "Grade protocol")
    _require_exact_keys(
        protocol, {"version", *(name + "_sha256" for name in paths)}, "Grade protocol"
    )
    if protocol["version"] != "table-assessment-grade-protocol-v1":
        raise ValueError("Unsupported grade protocol")
    if output.exists():
        raise ValueError("Grade output already exists")
    raw = {}
    # Annotation bytes are deliberately not opened until all execution checks finish.
    for name in ("run_protocol", "questions", "report", "receipt"):
        raw[name] = paths[name].read_bytes()
        if _digest(raw[name]) != protocol[name + "_sha256"]:
            raise ValueError(f"Frozen {name} hash mismatch")
    run_protocol = _load_object(raw["run_protocol"], "Run protocol")
    _validate_protocol(run_protocol)
    if run_protocol["version"] != "table-assessment-run-protocol-v2":
        raise ValueError("Grading requires a precommitted assessment receipt")
    if run_protocol["assessment_receipt_sha256"] != protocol["receipt_sha256"]:
        raise ValueError("Assessment receipt differs from execution commitment")
    receipt = _load_object(raw["receipt"], "Assessment receipt")
    _require_exact_keys(
        receipt,
        {
            "version",
            "questions_sha256",
            "annotations_sha256",
            "corpus_manifest_sha256",
            "runtime_sha256",
        },
        "Assessment receipt",
    )
    if receipt["version"] != "table-assessment-receipt-v1":
        raise ValueError("Unsupported assessment receipt")
    for key in ("questions_sha256", "corpus_manifest_sha256", "runtime_sha256"):
        _same(receipt[key], run_protocol[key], "Assessment receipt identity mismatch")
    _same(
        receipt["annotations_sha256"],
        protocol["annotations_sha256"],
        "Annotations changed after commitment",
    )
    manifest = (corpus / "sources.json").read_bytes()
    if _digest(manifest) != run_protocol["corpus_manifest_sha256"]:
        raise ValueError("Corpus manifest mismatch")
    if runtime_digest() != run_protocol["runtime_sha256"]:
        raise ValueError("Runtime changed since execution freeze")
    if _digest(raw["questions"]) != run_protocol["questions_sha256"]:
        raise ValueError("Run questions mismatch")
    questions = _validate_questions(
        _load_object(raw["questions"], "Questions"), _native_html_source_ids(json.loads(manifest))
    )
    report = _load_object(raw["report"], "Report")
    _same(report.get("protocol_sha256"), protocol["run_protocol_sha256"], "Run protocol mismatch")
    _same(
        report.get("assessment_receipt_sha256"), protocol["receipt_sha256"], "Run receipt mismatch"
    )
    cases = _verify_execution(run_protocol, questions, report, corpus)
    raw["annotations"] = paths["annotations"].read_bytes()
    if _digest(raw["annotations"]) != protocol["annotations_sha256"]:
        raise ValueError("Frozen annotations hash mismatch")
    sources = Sources(corpus)
    annotations = _validate_annotations(
        _load_object(raw["annotations"], "Annotations"), questions, sources, corpus, run_protocol
    )
    results = []
    for case, annotation in zip(cases, annotations, strict=True):
        alternatives = []
        for alternative in annotation["alternatives"]:
            search = case["trace"][0]["response"]
            hits = search.get("results", [])
            read = case["trace"][-1]["response"] if len(case["trace"]) == 2 else {}
            ids = {cell["id"] for cell in read.get("cells", [])}
            same_table = read.get("table_id") == alternative["table_id"]
            presence = {
                role: same_table and set(required) <= ids
                for role, required in alternative["components"].items()
            }
            alternatives.append(
                {
                    "table_id": alternative["table_id"],
                    "table_hit_at_k": {
                        str(k): any(h["table_id"] == alternative["table_id"] for h in hits[:k])
                        for k in (1, 3, 5)
                    },
                    "required_component_presence": presence,
                    "complete_context_present": case["status"] == "completed"
                    and all(presence.values()),
                }
            )
        results.append(
            {
                "id": case["id"],
                "source_id": case["source_id"],
                "disposition": annotation["disposition"],
                "run_status": case["status"],
                "reason": annotation["reason"],
                "alternatives": alternatives,
                "complete_context_present": any(
                    a["complete_context_present"] for a in alternatives
                ),
            }
        )
    # Detect mutable local inputs before publishing any grade.
    if Path(protocol_path).read_bytes() != protocol_raw or any(
        path.read_bytes() != raw[name] for name, path in paths.items()
    ):
        raise ValueError("Grading inputs changed during evaluation")
    if (corpus / "sources.json").read_bytes() != manifest or runtime_digest() != run_protocol[
        "runtime_sha256"
    ]:
        raise ValueError("Grading corpus/runtime changed")
    Sources(corpus)
    result = {
        "version": "table-assessment-grade-report-v1",
        "bindings": protocol,
        "grade_protocol_sha256": _digest(protocol_raw),
        "selected_denominator": len(cases),
        "mapped_denominator": sum(a["disposition"] == "mapped" for a in annotations),
        "complete_context_count": sum(r["complete_context_present"] for r in results),
        "disposition_counts": {
            status: sum(a["disposition"] == status for a in annotations)
            for status in ("mapped", "unmapped", "unresolved")
        },
        "table_hit_counts": {
            str(k): sum(
                any(a["table_hit_at_k"][str(k)] for a in r["alternatives"]) for r in results
            )
            for k in (1, 3, 5)
        },
        "execution_replay_verified": True,
        "semantic_answer_correctness": "not_measured",
        "limitations": "Replay establishes consistency, not cryptographic proof of historical execution or human annotation completeness.",
        "cases": results,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "grade.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "protocol",
        "run-protocol",
        "questions",
        "report",
        "annotations",
        "receipt",
        "corpus",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = grade(
        args.protocol,
        args.run_protocol,
        args.questions,
        args.report,
        args.annotations,
        args.receipt,
        args.corpus,
        args.output,
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("selected_denominator", "mapped_denominator", "complete_context_count")
            }
        )
    )


if __name__ == "__main__":
    main()
