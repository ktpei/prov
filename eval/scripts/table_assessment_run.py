"""Run a fixed offline table search-and-read assessment without grading."""

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

from provenance.source_availability import availability, timestamp
from provenance.sources import Sources
from provenance.table_tools import TableSources

PROTOCOL_VERSION = "table-assessment-run-protocol-v1"
QUESTIONS_VERSION = "table-assessment-questions-v1"
RUNTIME_VERSION = "table-assessment-run-runtime-v1"
REPORT_VERSION = "table-assessment-run-report-v1"
SEARCH_VERSIONS = {
    "source-scoped-visible-row-bm25-v1",
    "source-scoped-visible-row-bm25-v2",
    "source-scoped-visible-row-bm25-v3",
}
STATUSES = (
    "pending",
    "running",
    "completed",
    "search_error",
    "no_hit",
    "read_error",
    "failed",
    "interrupted",
    "availability_blocked",
)
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_LEXICAL = re.compile(r"\w", re.UNICODE)
_MAX_ERROR_CHARACTERS = 1000


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _repository_root():
    return Path(__file__).resolve().parents[2]


def runtime_digest():
    """Hash every runtime Python file and pinned project metadata."""
    root = _repository_root()
    paths = {
        *root.glob("provenance/**/*.py"),
        *root.glob("eval/scripts/*.py"),
        root / "pyproject.toml",
        root / "uv.lock",
    }
    mapping = {
        path.relative_to(root).as_posix(): _digest(path.read_bytes())
        for path in paths
        if path.is_file() and "__pycache__" not in path.parts
    }
    return _digest(_canonical(mapping).encode("utf-8"))


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"Nonfinite JSON constant: {value}")


def _load_object(raw, label):
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_exact_keys(value, expected, label):
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{label} fields must be exact; missing={missing}, extra={extra}")


def _validate_sha256(value, label):
    if not isinstance(value, str) or _HEX_SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _is_temporal(protocol):
    return protocol["version"] in {
        "table-assessment-run-protocol-v3",
        "table-assessment-run-protocol-v4",
    }


def _sidecar_version(protocol):
    return protocol.get("sidecar_version", "native-html-tables-v2")


def _validate_protocol(protocol):
    committed = protocol.get("version") in (
        "table-assessment-run-protocol-v2",
        "table-assessment-run-protocol-v3",
        "table-assessment-run-protocol-v4",
    )
    _require_exact_keys(
        protocol,
        {
            "version",
            "questions_sha256",
            "corpus_manifest_sha256",
            "search_version",
            "runtime_sha256",
        }
        | ({"assessment_receipt_sha256"} if committed else set())
        | (
            {"sidecar_version"}
            if protocol.get("version") == "table-assessment-run-protocol-v4"
            else set()
        ),
        "Protocol",
    )
    if protocol["version"] != PROTOCOL_VERSION and not committed:
        raise ValueError(f"Protocol version must be {PROTOCOL_VERSION}")
    if committed:
        _validate_sha256(protocol["assessment_receipt_sha256"], "Assessment receipt")
    if _sidecar_version(protocol) not in ("native-html-tables-v2", "native-html-tables-v3"):
        raise ValueError("Unknown protocol sidecar version")
    for field in ("questions_sha256", "corpus_manifest_sha256", "runtime_sha256"):
        _validate_sha256(protocol[field], f"Protocol {field}")
    if (
        not isinstance(protocol["search_version"], str)
        or protocol["search_version"] not in SEARCH_VERSIONS
    ):
        raise ValueError("Protocol search_version is not a current table search version")


def _native_html_source_ids(manifest):
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise ValueError("Corpus manifest must contain a sources list")
    known = set()
    all_ids = set()
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise ValueError("Corpus manifest source IDs must be strings")
        source_id = source["id"]
        if source_id in all_ids:
            raise ValueError(f"Corpus manifest has duplicate source_id: {source_id}")
        all_ids.add(source_id)
        original_file = source.get("original_file")
        if isinstance(original_file, str) and Path(original_file).suffix.lower() in {
            ".html",
            ".htm",
        }:
            known.add(source_id)
    return known


def _validate_questions(questions, native_html_ids):
    _require_exact_keys(questions, {"version", "cases"}, "Questions")
    temporal = questions["version"] == "table-assessment-questions-v2"
    if questions["version"] != QUESTIONS_VERSION and not temporal:
        raise ValueError(f"Questions version must be {QUESTIONS_VERSION}")
    cases = questions["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("Questions cases must be a nonempty list")
    seen = set()
    for index, case in enumerate(cases):
        label = f"Question case {index}"
        if not isinstance(case, dict):
            raise ValueError(f"{label} must be an object")
        _require_exact_keys(
            case, {"id", "source_id", "question"} | ({"as_of"} if temporal else set()), label
        )
        if temporal and case["as_of"] is not None:
            timestamp(case["as_of"])
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{label} id must be a nonempty string")
        if case_id in seen:
            raise ValueError(f"Duplicate question case id: {case_id}")
        seen.add(case_id)
        source_id = case["source_id"]
        if not isinstance(source_id, str) or source_id not in native_html_ids:
            raise ValueError(f"{label} source_id is not a known native HTML source: {source_id}")
        question = case["question"]
        if (
            not isinstance(question, str)
            or not 1 <= len(question) <= 500
            or _LEXICAL.search(question) is None
        ):
            raise ValueError(f"{label} question must be 1–500 characters and lexically nonempty")
    return cases


def _git_metadata(root):
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return revision, dirty


def _status_counts(cases):
    return {status: sum(case["status"] == status for case in cases) for status in STATUSES}


def _persist(report, output):
    report["status_counts"] = _status_counts(report["cases"])
    temporary = output / ".report.json.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    temporary.replace(output / "report.json")


def _trace_call(tables, tool, args, trace):
    started = time.monotonic()
    response = tables.call(tool, args, timeout=10)
    latency = time.monotonic() - started
    serialized = _canonical(response)
    trace.append(
        {
            "tool": tool,
            "args": args,
            "response": response,
            "response_canonical_sha256": _digest(serialized.encode("utf-8")),
            "response_unicode_characters": len(serialized),
            "response_utf8_bytes": len(serialized.encode("utf-8")),
            "latency_seconds": latency,
        }
    )
    return response


def _bounded_error(exc):
    message = f"{type(exc).__name__}: {exc}"
    return message[:_MAX_ERROR_CHARACTERS]


def run(protocol_path, questions_path, corpus, output):
    """Execute one search and at most one fixed read for every validated question."""
    protocol_path = Path(protocol_path)
    questions_path = Path(questions_path)
    corpus = Path(corpus)
    output = Path(output)

    protocol_raw = protocol_path.read_bytes()
    questions_raw = questions_path.read_bytes()
    manifest_path = corpus / "sources.json"
    manifest_before = manifest_path.read_bytes()
    protocol = _load_object(protocol_raw, "Protocol")
    questions = _load_object(questions_raw, "Questions")
    manifest = _load_object(manifest_before, "Corpus manifest")

    _validate_protocol(protocol)
    if _digest(questions_raw) != protocol["questions_sha256"]:
        raise ValueError("Questions raw SHA-256 does not match protocol")
    if _digest(manifest_before) != protocol["corpus_manifest_sha256"]:
        raise ValueError("Corpus manifest raw SHA-256 does not match protocol")
    current_runtime_sha256 = runtime_digest()
    if current_runtime_sha256 != protocol["runtime_sha256"]:
        raise ValueError("Runtime SHA-256 does not match protocol")
    cases = _validate_questions(questions, _native_html_source_ids(manifest))
    temporal = _is_temporal(protocol)
    if temporal != (questions["version"] == "table-assessment-questions-v2"):
        raise ValueError("Question and run-protocol temporal versions must agree")
    source_metadata = {source["id"]: source for source in manifest["sources"]}
    decisions = (
        [availability(source_metadata[case["source_id"]], case["as_of"]) for case in cases]
        if temporal
        else []
    )
    if output.exists():
        raise ValueError("Output directory already exists; use a new directory")

    revision, dirty = _git_metadata(_repository_root())
    report = {
        "version": REPORT_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "protocol_sha256": _digest(protocol_raw),
        "questions_sha256": _digest(questions_raw),
        "corpus_manifest_sha256": _digest(manifest_before),
        "runtime_sha256": current_runtime_sha256,
        "search_version": protocol["search_version"],
        "git_revision": revision,
        "working_tree_dirty": dirty,
        "model_calls": 0,
        "task_denominator": len(cases),
        "run_status": "pending",
        "cases": [
            {
                "id": case["id"],
                "source_id": case["source_id"],
                "question": case["question"],
                "status": "pending",
                "trace": [],
            }
            for case in cases
        ],
    }
    if temporal:
        for original, case, decision in zip(cases, report["cases"], decisions, strict=True):
            case["as_of"] = original["as_of"]
            case["availability"] = decision
    if "assessment_receipt_sha256" in protocol:
        report["assessment_receipt_sha256"] = protocol["assessment_receipt_sha256"]
    if "sidecar_version" in protocol:
        report["sidecar_version"] = protocol["sidecar_version"]
    output.mkdir(parents=True, exist_ok=False)
    _persist(report, output)

    try:
        tables = (
            TableSources(
                corpus,
                search_version=protocol["search_version"],
                sidecar_version=_sidecar_version(protocol),
            )
            if not temporal or any(d["allowed"] for d in decisions)
            else None
        )
        manifest_after = manifest_path.read_bytes()
        if (
            manifest_after != manifest_before
            or _digest(manifest_after) != protocol["corpus_manifest_sha256"]
        ):
            raise ValueError("Corpus manifest changed during table snapshot construction")
    except BaseException as exc:
        report["run_status"] = "invalid"
        report["error"] = _bounded_error(exc)
        _persist(report, output)
        raise
    report["run_status"] = "running"
    _persist(report, output)

    for case in report["cases"]:
        if temporal and not case["availability"]["allowed"]:
            case["status"] = "availability_blocked"
            _persist(report, output)
            continue
        case["status"] = "running"
        _persist(report, output)
        try:
            search = _trace_call(
                tables,
                "search_tables",
                {"source_id": case["source_id"], "query": case["question"]},
                case["trace"],
            )
            _persist(report, output)
            if "error" in search:
                case["status"] = "search_error"
                case["error"] = search["error"]
            else:
                hits = search["results"]
                if not hits:
                    case["status"] = "no_hit"
                else:
                    hit = hits[0]
                    read = _trace_call(
                        tables,
                        "read_table",
                        {
                            "source_id": case["source_id"],
                            "table_id": hit["table_id"],
                            "row_indices": hit["matched_row_indices"][:3],
                        },
                        case["trace"],
                    )
                    _persist(report, output)
                    if "error" in read:
                        case["status"] = "read_error"
                        case["error"] = read["error"]
                    else:
                        case["status"] = "completed"
            _persist(report, output)
        except BaseException as exc:
            status = "failed" if isinstance(exc, Exception) else "interrupted"
            report["run_status"] = status
            case["status"] = status
            case["error"] = _bounded_error(exc)
            _persist(report, output)
            raise
    try:
        if (
            protocol_path.read_bytes() != protocol_raw
            or questions_path.read_bytes() != questions_raw
            or manifest_path.read_bytes() != manifest_before
            or runtime_digest() != current_runtime_sha256
        ):
            raise ValueError("Assessment inputs changed during execution")
        Sources(corpus)  # Revalidate original and extracted bytes before declaring completion.
    except BaseException as exc:
        report["run_status"] = "invalid"
        report["error"] = _bounded_error(exc)
        _persist(report, output)
        raise
    report["run_status"] = "completed"
    report["post_run_integrity_verified"] = True
    _persist(report, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-digest", action="store_true")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--questions", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runtime_digest:
        if any((args.protocol, args.questions, args.corpus, args.output)):
            parser.error("--runtime-digest cannot be combined with run arguments")
        print(runtime_digest())
        return
    if any(value is None for value in (args.protocol, args.questions, args.corpus, args.output)):
        parser.error("--protocol, --questions, --corpus, and --output are required")
    report = run(args.protocol, args.questions, args.corpus, args.output)
    print(json.dumps({"task_denominator": report["task_denominator"], **report["status_counts"]}))


if __name__ == "__main__":
    main()
