"""Evaluator-only line-component coverage, separate from financial correctness."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from eval.scripts.table_assessment_run import _load_object, _require_exact_keys, runtime_digest
from provenance.benchmarks import canonical_hash, load_bundle
from provenance.source_quality import evaluate_corpus
from provenance.sources import Sources, locator_range


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def span(value, line_count):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("Evidence span must be [start, end]")
    start, end = value
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= line_count:
        raise ValueError("Evidence span is outside source")
    return set(range(start, end + 1))


def coverage(cases, rows, sources):
    if not isinstance(cases, list) or [c.get("id") for c in cases] != [r["id"] for r in rows]:
        raise ValueError("Packet cases must match exact report order and denominator")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate packet case")
    results = []
    for case, row in zip(cases, rows, strict=True):
        _require_exact_keys(
            case,
            {"id", "source_id", "disposition", "reason", "required_components", "alternatives"},
            "Packet case",
        )
        source_id = case["source_id"]
        if source_id not in sources.documents:
            raise ValueError("Unknown packet source")
        lines = sources.documents[source_id]["text"].splitlines()
        roles = case["required_components"]
        if (
            not isinstance(roles, list)
            or any(not isinstance(r, str) or not r.strip() for r in roles)
            or len(set(roles)) != len(roles)
            or not isinstance(case["reason"], str)
        ):
            raise ValueError("Invalid packet components or reason")
        alternatives = case["alternatives"]
        if not isinstance(alternatives, list):
            raise ValueError("Packet alternatives must be a list")
        mapped = case["disposition"] == "mapped"
        if not mapped:
            if (
                case["disposition"] not in {"unmapped", "unresolved"}
                or alternatives
                or not case["reason"].strip()
            ):
                raise ValueError("Ineligible packets require a reason and no alternatives")
        elif not roles or not alternatives:
            raise ValueError("Mapped packet needs complete alternatives")
        validated = []
        for alternative in alternatives:
            if not isinstance(alternative, dict) or set(alternative) != set(roles):
                raise ValueError("Each alternative must include every required component")
            components = {}
            for role, spans in alternative.items():
                if not isinstance(spans, list) or not spans:
                    raise ValueError("Each component requires nonempty spans")
                components[role] = set().union(*(span(s, len(lines)) for s in spans))
                if any(not lines[n - 1].strip() for n in components[role]):
                    raise ValueError("Empty source lines cannot be evidence components")
            if components in validated:
                raise ValueError("Duplicate evidence alternative")
            validated.append(components)
        parents, snippets = [], []
        for hit in row["retrieved_hits"]:
            if hit["source_id"] != source_id:
                parents.append(set())
                snippets.append(set())
                continue
            parent = span([hit["start_line"], hit["end_line"]], len(lines))
            parents.append(parent)
            text = hit.get("snippet")
            if not isinstance(text, str):
                raise ValueError("Replayed hit lacks snippet text")
            if not text:
                snippets.append(set())  # Empty long-line fallback never grants evidence.
                continue
            start, end = locator_range(hit["snippet_locator"])
            seen = span([start, end], len(lines))
            if not seen <= parent or text != "\n".join(lines[start - 1 : end]):
                raise ValueError("Snippet does not match its exact parent source slice")
            snippets.append(seen)
        measures = {}
        for name, windows in [
            ("parent_passage_opportunity", parents),
            ("returned_snippets", snippets),
        ]:
            measures[name] = {}
            for k in [1, 3, 5]:
                available = set().union(*windows[:k])
                alternatives_result = []
                for components in validated:
                    role_presence = {
                        role: required <= available for role, required in components.items()
                    }
                    alternatives_result.append(
                        {
                            "components_present": role_presence,
                            "complete": all(role_presence.values()),
                        }
                    )
                measures[name][f"top_{k}"] = {
                    "complete": any(a["complete"] for a in alternatives_result),
                    "single_hit_complete": any(
                        all(required <= window for required in a.values())
                        for window in windows[:k]
                        for a in validated
                    ),
                    "alternatives": alternatives_result,
                }
        results.append(
            {
                "id": case["id"],
                "source_id": source_id,
                "disposition": case["disposition"],
                "reason": case["reason"],
                "coverage": measures,
            }
        )
    return results


def grade(protocol_path, prepared, corpus, report_path, packets_path, output):
    protocol_path, corpus, report_path, packets_path, output = map(
        Path, [protocol_path, corpus, report_path, packets_path, output]
    )
    protocol_raw = protocol_path.read_bytes()
    protocol = _load_object(protocol_raw, "Coverage protocol")
    _require_exact_keys(
        protocol,
        {
            "version",
            "report_sha256",
            "packets_sha256",
            "corpus_manifest_sha256",
            "prepared_sha256",
            "prepared_files_sha256",
            "corpus_binding_sha256",
            "runtime_sha256",
        },
        "Coverage protocol",
    )
    if protocol["version"] != "pdf-evidence-coverage-protocol-v1":
        raise ValueError("Unsupported coverage protocol")
    if output.exists():
        raise ValueError("Coverage output already exists")
    prepared = Path(prepared)
    _require_exact_keys(
        protocol["prepared_files_sha256"],
        {"manifest.json", "tasks.json", "inputs.json"},
        "Prepared file hashes",
    )
    bundle = load_bundle(prepared)

    def verify():
        if (
            digest(report_path) != protocol["report_sha256"]
            or digest(corpus / "sources.json") != protocol["corpus_manifest_sha256"]
            or canonical_hash(load_bundle(prepared)["manifest"]) != protocol["prepared_sha256"]
            or runtime_digest() != protocol["runtime_sha256"]
            or protocol_path.read_bytes() != protocol_raw
            or digest(corpus / "benchmark_binding.json") != protocol["corpus_binding_sha256"]
            or any(
                digest(prepared / name) != expected
                for name, expected in protocol["prepared_files_sha256"].items()
            )
        ):
            raise ValueError("Coverage frozen identity mismatch")
        Sources(corpus)  # Recheck original and extracted byte identities.

    verify()
    report = _load_object(report_path.read_bytes(), "Retrieval report")
    replay = evaluate_corpus(
        bundle,
        corpus,
        source_scope=report.get("source_scope", "selected_corpus"),
        query_policy=report.get("query_policy", "original-question-v1"),
        include_snippets=True,
    )
    stripped = copy.deepcopy(replay)
    for row in stripped["tasks"]:
        for hit in row["retrieved_hits"]:
            del hit["snippet"]
    if canonical_hash(stripped) != canonical_hash(report):
        raise ValueError("Retrieval report does not replay exactly")
    # Labels are opened only after exact retrieval replay; never passed to search.
    if digest(packets_path) != protocol["packets_sha256"]:
        raise ValueError("Packet hash mismatch")
    packets = _load_object(packets_path.read_bytes(), "Coverage packets")
    _require_exact_keys(
        packets, {"version", "corpus_manifest_sha256", "sources", "cases"}, "Coverage packets"
    )
    if (
        packets["version"] != "pdf-evidence-components-v1"
        or packets["corpus_manifest_sha256"] != protocol["corpus_manifest_sha256"]
    ):
        raise ValueError("Packet version or corpus mismatch")
    sources = Sources(corpus)
    expected_sources = {c["source_id"] for c in packets["cases"]}
    if not isinstance(packets["sources"], dict) or set(packets["sources"]) != expected_sources:
        raise ValueError("Packet source bindings mismatch")
    for sid, binding in packets["sources"].items():
        source = sources.documents.get(sid, {})
        if binding != {k: source.get(k) for k in ["original_sha256", "sha256"]} or not all(
            binding.values()
        ):
            raise ValueError("Packet original/text identity mismatch")
    permitted = {i["id"]: i["context"]["doc_name"] for i in bundle["inputs"]}
    if any(permitted.get(c["id"]) != c["source_id"] for c in packets["cases"]):
        raise ValueError("Packet source differs from declared task document")
    cases = coverage(packets["cases"], replay["tasks"], sources)
    result = {
        "version": "pdf-evidence-coverage-report-v1",
        "protocol_sha256": hashlib.sha256(protocol_raw).hexdigest(),
        "selected_denominator": len(cases),
        "mapped_denominator": sum(c["disposition"] == "mapped" for c in cases),
        "cases": cases,
        "semantic_correctness": "not_measured",
        "replay_verified": True,
        "limitations": [
            "Posthoc development component annotations, not human validation.",
            "Line coverage does not establish correct column association, calculation or complete annotation adequacy.",
            "Parent passages are opportunities to read; only returned nonempty snippets count as already exposed text.",
        ],
    }
    result["summary"] = {
        name: {
            f"top_{k}_complete_count": sum(
                c["coverage"][name][f"top_{k}"]["complete"] for c in cases
            )
            for k in [1, 3, 5]
        }
        for name in ["parent_passage_opportunity", "returned_snippets"]
    }
    verify()
    if digest(packets_path) != protocol["packets_sha256"]:
        raise ValueError("Packets changed while grading")
    with output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["protocol", "prepared", "corpus", "report", "packets", "output"]:
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    result = grade(
        args.protocol, args.prepared, args.corpus, args.report, args.packets, args.output
    )
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
