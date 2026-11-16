"""Offline FinanceBench corpus identity, retrieval, and extraction diagnostics."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from provenance.benchmarks import canonical_hash, load_bundle, score_run
from provenance.finance_retrieval import POLICIES as COMPONENT_POLICIES
from provenance.finance_retrieval import retrieve as component_retrieve
from provenance.sources import Sources

VERSION = "financebench-source-quality-v1"
RETRIEVAL_VERSION = "bm25-v2"
FIXED_K = (1, 3, 5)


def _normalized(text):
    return " ".join(text.split())


def _page_key(source_id, page):
    return {"source_id": source_id, "page": page}


def _sorted_keys(keys):
    return [_page_key(source_id, page) for source_id, page in sorted(keys)]


def _validate(bundle, corpus_directory):
    manifest = bundle["manifest"]
    prepared_sha256 = canonical_hash(manifest)
    score_run(bundle, {"prepared_sha256": prepared_sha256, "predictions": []})
    if manifest["source"]["dataset"] != "financebench" or manifest["condition"] != "full_agent":
        raise ValueError("Source diagnostics require a FinanceBench full-agent preparation")

    corpus_directory = Path(corpus_directory)
    binding = json.loads((corpus_directory / "benchmark_binding.json").read_text())
    binding_sha256 = canonical_hash(binding)
    sources = Sources(corpus_directory, retrieval_version=RETRIEVAL_VERSION)
    if not sources.documents or not sources.passages:
        raise ValueError("Corpus contains no searchable documents")
    selected = sorted({task["metadata"]["doc_name"] for task in bundle["tasks"]})
    source_ids = binding.get("source_ids")
    if (
        not isinstance(source_ids, list)
        or any(not isinstance(source_id, str) for source_id in source_ids)
        or len(source_ids) != len(set(source_ids))
    ):
        raise ValueError("Binding source IDs must be unique strings")
    if not selected or source_ids != sorted(source_ids) or selected != source_ids:
        raise ValueError("Prepared and binding source IDs differ")
    if source_ids != sorted(sources.documents):
        raise ValueError("Binding and corpus source IDs differ")
    if binding.get("version") != "financebench-full-documents-v2":
        raise ValueError("Unsupported FinanceBench corpus binding version")
    if binding.get("prepared_sha256") != prepared_sha256:
        raise ValueError("Binding prepared hash differs from prepared benchmark")
    if binding.get("dataset_revision") != manifest["source"]["revision"]:
        raise ValueError("Binding dataset revision differs from prepared source")
    if any(
        sources.documents[key].get("dataset_revision") != manifest["source"]["revision"]
        for key in source_ids
    ):
        raise ValueError("Corpus dataset revision differs from prepared source")

    actual_hashes = {key: sources.documents[key].get("sha256") for key in source_ids}
    actual_original_hashes = {
        key: sources.documents[key].get("original_sha256") for key in source_ids
    }
    if any(
        not sources.documents[key].get("original_file") or not actual_original_hashes[key]
        for key in source_ids
    ):
        raise ValueError("Every corpus source requires verified original bytes")
    if binding.get("source_hashes") != actual_hashes:
        raise ValueError("Binding source hashes differ from corpus metadata")
    if binding.get("original_hashes") != actual_original_hashes:
        raise ValueError("Binding original hashes differ from corpus metadata")
    if (
        binding.get("sources_manifest_sha256")
        != hashlib.sha256((corpus_directory / "sources.json").read_bytes()).hexdigest()
    ):
        raise ValueError("Binding source manifest hash differs; original locations are not trusted")
    return sources, binding, prepared_sha256, binding_sha256


def _page_texts(source):
    pages = {}
    for line, location in zip(
        source["text"].splitlines(), source.get("line_locations", []), strict=False
    ):
        page = location.get("page") if isinstance(location, dict) else None
        if type(page) is int and page >= 1:
            pages.setdefault(page, []).append(line)
    return {page: _normalized("\n".join(lines)) for page, lines in pages.items()}


def _hit_record(hit, sources):
    source_id = hit.get("id")
    if source_id not in sources.documents:
        raise ValueError("Search returned an unknown corpus source")
    start, end = hit.get("start_line"), hit.get("end_line")
    lines = sources.documents[source_id]["text"].splitlines()
    locations = sources.documents[source_id].get("line_locations", [])
    if (
        type(start) is not int
        or type(end) is not int
        or not (1 <= start <= end <= len(lines))
        or len(locations) != len(lines)
    ):
        raise ValueError("Search hit has invalid passage line bounds")
    covered_locations = locations[start - 1 : end]
    if any(
        not isinstance(location, dict)
        or type(location.get("page")) is not int
        or location["page"] < 1
        for location in covered_locations
    ):
        raise ValueError("Search hit lines must map to positive original page numbers")
    pages = {
        location["page"]
        for location in covered_locations
        if isinstance(location, dict)
        and type(location.get("page")) is int
        and location["page"] >= 1
    }
    score = hit.get("score")
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("Search hit score must be finite")
    return {
        "id": source_id,
        "source_id": source_id,
        "locator": f"L{start}-L{end}",
        "start_line": start,
        "end_line": end,
        "snippet_locator": hit.get("snippet_locator"),
        "original_location": hit.get("original_location"),
        "passage_original_locations": covered_locations,
        "passage_pages": sorted(pages),
        "score": score,
    }, {(source_id, page) for page in pages}


def _reference_flags(reference):
    issues = reference.get("reference_issues", [])
    if not isinstance(issues, list):
        issues = [str(issues)]
    requires_review = bool(reference.get("requires_review"))
    return {
        "unresolved": requires_review or bool(issues),
        "requires_review": requires_review,
        "reference_issues": issues,
        "diagnostic_only": True,
    }


def evaluate_corpus(
    bundle,
    corpus_directory,
    *,
    source_scope="selected_corpus",
    query_policy="original-question-v1",
    include_snippets=False,
):
    """Return identity-bound, offline retrieval and text-concordance diagnostics."""
    if source_scope not in {"selected_corpus", "declared_document"}:
        raise ValueError("Unknown diagnostic source scope")
    if query_policy not in {"original-question-v1", *COMPONENT_POLICIES}:
        raise ValueError("Unknown diagnostic query policy")
    sources, binding, prepared_sha256, binding_sha256 = _validate(bundle, corpus_directory)
    all_documents = dict(sources.documents)
    permitted_documents = {item["id"]: item["context"]["doc_name"] for item in bundle["inputs"]}
    page_texts = {
        source_id: _page_texts(sources.documents[source_id]) for source_id in sources.documents
    }
    rows = []
    pooled_expected = 0
    pooled_found = {k: 0 for k in FIXED_K}
    macro_recall = {k: 0.0 for k in FIXED_K}
    all_required = {k: 0 for k in FIXED_K}

    for task in bundle["tasks"]:
        evidence = task["reference"]["evidence"]
        expected = {(entry["doc_name"], entry["evidence_page_num"] + 1) for entry in evidence}
        sources.documents = (
            {permitted_documents[task["id"]]: all_documents[permitted_documents[task["id"]]]}
            if source_scope == "declared_document"
            else all_documents
        )
        if query_policy in COMPONENT_POLICIES:
            hits, query_trace = component_retrieve(
                sources, task["question"], timeout=1, policy=query_policy
            )
        else:
            hits = sources.search(task["question"], timeout=1)["results"]
        if len(hits) > 5:
            raise ValueError("Retrieval returned more than the fixed top five")
        raw_hits, hit_pages = [], []
        for rank, hit in enumerate(hits, 1):
            raw, pages = _hit_record(hit, sources)
            if include_snippets:
                raw["snippet"] = hit.get("snippet", "")
            raw_hits.append({"rank": rank, **raw})
            hit_pages.append(pages)

        retrieval = {}
        for k in FIXED_K:
            retrieved = set().union(*hit_pages[:k]) if hit_pages[:k] else set()
            matched = expected & retrieved
            recall = len(matched) / len(expected) if expected else 0.0
            complete = bool(expected) and matched == expected
            retrieval[f"top_{k}"] = {
                "retrieved_distinct_page_keys": _sorted_keys(retrieved),
                "expected_pages_retrieved": _sorted_keys(matched),
                "expected_page_recall": recall,
                "all_required_pages_retrieved": complete,
            }
            pooled_found[k] += len(matched)
            macro_recall[k] += recall
            all_required[k] += int(complete)

        concordance = []
        for entry in evidence:
            source_id = entry["doc_name"]
            page = entry["evidence_page_num"] + 1
            normalized = _normalized(entry["evidence_text"])
            extracted_page = page_texts.get(source_id, {}).get(page)
            if extracted_page is None:
                status = "missing_page"
            elif normalized in extracted_page:
                status = "found"
            else:
                status = "not_found"
            concordance.append(
                {
                    "source_id": source_id,
                    "page": page,
                    "evidence_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
                    "evidence_char_count": len(normalized),
                    "status": status,
                    "exact_text_found": status == "found",
                }
            )

        pooled_expected += len(expected)
        rows.append(
            {
                "id": task["id"],
                "searched_source_ids": sorted(sources.documents),
                "reference_flags": _reference_flags(task["reference"]),
                "expected_distinct_page_keys": _sorted_keys(expected),
                "expected_distinct_page_count": len(expected),
                "retrieval": retrieval,
                "retrieved_hits": raw_hits,
                "evidence_text_concordance": concordance,
            }
        )
        if query_policy in COMPONENT_POLICIES:
            rows[-1]["query_trace"] = query_trace

    denominator = len(bundle["tasks"])
    report = {
        "version": VERSION,
        "binding_version": binding["version"],
        "prepared_sha256": prepared_sha256,
        "binding_sha256": binding_sha256,
        "source_hashes": binding["source_hashes"],
        "original_hashes": binding["original_hashes"],
        "dataset_revision": binding["dataset_revision"],
        "retrieval_version": RETRIEVAL_VERSION,
        "source_scope": source_scope,
        "fixed_k": list(FIXED_K),
        "task_denominator": denominator,
        "retrieval_interpretation": {
            "page_coverage_basis": "full passage start/end lines mapped to original pages",
            "query_focused_snippet_content_evaluated": False,
        },
        "concordance_method": (
            "Case-sensitive exact containment after whitespace normalization within one full "
            "extracted original page; numeric token matches alone do not qualify."
        ),
        "summary": {
            f"top_{k}": {
                "pooled_expected_page_recall": (
                    pooled_found[k] / pooled_expected if pooled_expected else 0.0
                ),
                "macro_task_expected_page_recall": macro_recall[k] / denominator,
                "all_required_pages_task_rate": all_required[k] / denominator,
            }
            for k in FIXED_K
        },
        "tasks": rows,
        "limitations": [
            (
                "Gold annotations may be incomplete; unresolved reference flags are diagnostics, "
                "not correctness claims."
            ),
            (
                "Exact-text concordance is case-sensitive after whitespace normalization and is "
                "sensitive to extraction quality."
            ),
            (
                "Page recall measures passage page coverage, not answer correctness, semantic "
                "entailment, sufficient evidence, or agent completion."
            ),
            (
                "Query-focused snippets are not used as full-passage page coverage, and a page "
                "hit does not imply the snippet contains the answer."
            ),
            (
                "No OCR completeness, chart interpretation, table geometry, or "
                "semantic-completeness claim is made."
            ),
        ],
    }
    if query_policy in COMPONENT_POLICIES:
        report["query_policy"] = query_policy
        report["query_count"] = sum(len(row["query_trace"]) for row in rows)
        report["ranking_interpretation"] = (
            "Round-robin by per-query rank, original query first; deduplicate exact passages; "
            "retain five passages. Hit scores remain originating-query BM25 scores, not fused scores."
        )
    json.dumps(report, allow_nan=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-scope",
        choices=["selected_corpus", "declared_document"],
        default="selected_corpus",
    )
    parser.add_argument(
        "--query-policy",
        choices=["original-question-v1", *COMPONENT_POLICIES],
        default="original-question-v1",
    )
    args = parser.parse_args()
    report = evaluate_corpus(
        load_bundle(args.prepared),
        args.corpus,
        source_scope=args.source_scope,
        query_policy=args.query_policy,
    )
    with args.output.open("x") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "tasks": report["task_denominator"],
                "output": str(args.output),
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
