"""Assemble full-document FinanceBench evidence from its immutable PDF mirror.

Only document metadata and whole PDFs enter ingestion; question gold never does.
"""

import argparse
import hashlib
import json
import re
import tempfile
import urllib.request
from pathlib import Path

from provenance.benchmark_data import MAX_BYTES, read_records
from provenance.benchmarks import canonical_hash, load_bundle, score_run
from provenance.ingestion import ingest
from provenance.sources import Sources


def build_corpus(bundle, metadata_path, metadata_source, output):
    manifest = bundle["manifest"]
    identity = canonical_hash(manifest)
    score_run(bundle, {"prepared_sha256": identity, "predictions": []})
    if manifest["source"]["dataset"] != "financebench" or manifest["condition"] != "full_agent":
        raise ValueError("Corpus assembly requires a FinanceBench full-agent preparation")
    metadata_path = Path(metadata_path)
    source = json.loads(Path(metadata_source).read_text())
    if (
        source.get("dataset") != "financebench_documents"
        or source.get("revision") != manifest["source"]["revision"]
        or hashlib.sha256(metadata_path.read_bytes()).hexdigest() != source.get("sha256")
    ):
        raise ValueError("Document metadata identity differs from prepared benchmark")
    metadata = read_records(metadata_path)
    selected = sorted({task["metadata"]["doc_name"] for task in bundle["tasks"]})
    documents = {}
    for item in metadata:
        name = item["doc_name"]
        if name not in selected:
            continue
        if name in documents and documents[name] != item:
            raise ValueError("Conflicting selected document metadata identity")
        documents[name] = item
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name not in documents for name in selected):
        raise ValueError("Selected document is missing or has an unsafe identifier")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    specs = []
    with tempfile.TemporaryDirectory(prefix="financebench-input-") as tmp:
        for name in selected:
            item = documents[name]
            url = (
                "https://raw.githubusercontent.com/patronus-ai/financebench/"
                f"{source['revision']}/pdfs/{name}.pdf"
            )
            request = urllib.request.Request(url, headers={"User-Agent": "ProvenanceXL-research/1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or not raw.startswith(b"%PDF-"):
                raise ValueError("Expected a bounded PDF from the pinned document mirror")
            original = Path(tmp) / f"{name}.pdf"
            original.write_bytes(raw)
            specs.append(
                {
                    "id": name,
                    "title": name,
                    "company": item.get("company"),
                    "doc_type": item.get("doc_type"),
                    "doc_period": item.get("doc_period"),
                    "url": item.get("doc_link"),
                    "download_url": url,
                    "dataset_revision": source["revision"],
                    "published": None,
                    "availability_note": "Publication date is not verified by year-only dataset metadata.",
                    "input_file": str(original),
                }
            )
        ingest({"sources": specs}, output)
    verified = Sources(output)
    binding = {
        "version": "financebench-full-documents-v1",
        "prepared_sha256": identity,
        "document_metadata_sha256": source["sha256"],
        "dataset_revision": source["revision"],
        "source_ids": selected,
        "source_hashes": {key: doc["sha256"] for key, doc in verified.documents.items()},
        "original_hashes": {key: doc["original_sha256"] for key, doc in verified.documents.items()},
        "limitations": [
            "Full native PDF extraction, not verified OCR/table geometry.",
            "Dataset document year is not a verified publication timestamp.",
            "Gold evidence and answers are not ingested.",
        ],
    }
    (output / "benchmark_binding.json").write_text(json.dumps(binding, indent=2) + "\n")
    return binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--metadata-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binding = build_corpus(
        load_bundle(args.prepared), args.metadata, args.metadata_source, args.output
    )
    print(
        json.dumps(
            {"documents": len(binding["source_ids"]), "output": str(args.output), "model_calls": 0}
        )
    )


if __name__ == "__main__":
    main()
