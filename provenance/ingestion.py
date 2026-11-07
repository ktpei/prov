"""Parser-independent page-text ingestion; no OCR or model calls.

Input is a normalized JSON packet. Extraction adapters supply page text; original
page numbers stay separate from the stable line locators used by tools.
"""

import hashlib
import json
import re
import tempfile
from pathlib import Path


def ingest_packet(input_path, output_directory):
    packet = json.loads(Path(input_path).read_text())
    documents = packet["documents"]
    if not isinstance(documents, list) or not documents:
        raise ValueError("Packet requires documents")
    manifest, files, identifiers = [], {}, set()
    for document in documents:
        source_id = document["id"]
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id):
            raise ValueError("Document ID must be a safe filename")
        if source_id in identifiers:
            raise ValueError("Duplicate document ID")
        identifiers.add(source_id)
        for key in ("title", "company", "ticker", "url", "published", "source_type"):
            if not isinstance(document.get(key), str) or not document[key].strip():
                raise ValueError(f"Document requires {key}")
        if not document.get("pages"):
            raise ValueError("Document requires pages")
        lines, pages, previous_page = [], [], 0
        for page in document["pages"]:
            number, content = page["page"], page["text"]
            if type(number) is not int or number <= previous_page:
                raise ValueError("Page numbers must be positive and increasing")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty page extraction must be resolved before ingestion")
            start = len(lines) + 1
            # Bound individual read units without dropping text or inventing structure.
            for line in content.splitlines():
                lines.extend(line[i : i + 200] for i in range(0, max(1, len(line)), 200))
            pages.append({"page": number, "start_line": start, "end_line": len(lines)})
            previous_page = number
        text = "\n".join(lines) + "\n"
        filename = f"{source_id}.txt"
        files[filename] = text
        manifest.append(
            {
                **{
                    key: document[key]
                    for key in (
                        "id",
                        "title",
                        "company",
                        "ticker",
                        "url",
                        "published",
                        "source_type",
                    )
                },
                "text_file": filename,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "pages": pages,
                "locator_note": "Stable extracted-text lines; pages map to supplied original page numbers",
            }
        )
    output = Path(output_directory)
    if output.exists():
        raise ValueError("Output directory already exists; use a new immutable packet path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        root = Path(staging) / "packet"
        root.mkdir()
        for filename, content in files.items():
            (root / filename).write_text(content)
        (root / "sources.json").write_text(
            json.dumps(
                {
                    "version": "page-text-v1",
                    "sources": manifest,
                    "extraction_status": "Parser-supplied text; extraction accuracy requires review",
                },
                indent=2,
            )
            + "\n"
        )
        root.rename(output)
    return {"directory": str(output), "documents": len(manifest)}
