"""Native document ingestion with immutable originals and original-location mappings.

Run ``python -m provenance.ingestion packet.json output_directory``. Packet JSON
contains a ``sources`` list of metadata plus a local ``input_file`` per source.
Native extraction is not OCR: charts, scans and complex PDF tables need review.
"""

import argparse
import hashlib
import json
import re
import shutil
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class DocumentHTML(HTMLParser):
    """Retain headings and table rows; discard executable/style document content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.locations = []
        self.parts = []
        self.section = "Document"
        self.suppressed = 0
        self.heading = False
        self.row = False

    def flush(self):
        text = " ".join("".join(self.parts).split())
        self.parts = []
        if text:
            if self.heading:
                self.section = text[:300]
            self.lines.append(text)
            self.locations.append({"section": self.section})

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "ix:header", "head"}:
            self.suppressed += 1
        if self.suppressed:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = True
        elif tag == "tr":
            self.flush()
            self.row = True
        elif tag in {"td", "th"} and self.parts:
            self.parts.append(" | ")
        elif tag in {"p", "div", "li", "br", "section"} and not self.row:
            self.flush()

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "ix:header", "head"}:
            self.suppressed = max(0, self.suppressed - 1)
            return
        if self.suppressed:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = False
        elif tag == "tr":
            self.flush()
            self.row = False
        elif tag in {"p", "div", "li", "section"} and not self.row:
            self.flush()

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)


def extract(path):
    """Return complete native text and one location per line; never silently OCR."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        lines, locations, empty = [], [], []
        for number, page in enumerate(reader.pages, 1):
            text = (
                page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or ""
            )
            page_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
            if not page_lines:
                empty.append(number)
                page_lines = ["[No native text extracted; inspect original page or run OCR.]"]
            lines.extend(page_lines)
            locations.extend({"page": number} for _ in page_lines)
        return (
            lines,
            locations,
            {
                "parser": "pypdf-layout",
                "text_completeness": "not_verified",
                "ocr_performed": False,
                "page_count": len(reader.pages),
                "warnings": [
                    "Native PDF text does not establish chart semantics or table alignment.",
                    *([f"Pages without native text: {empty}"] if empty else []),
                ],
            },
        )
    if path.suffix.lower() in {".html", ".htm"}:
        parser = DocumentHTML()
        parser.feed(path.read_text(encoding="utf-8", errors="strict"))
        parser.flush()
        return (
            parser.lines,
            parser.locations,
            {
                "parser": "stdlib-html",
                "warnings": [
                    "HTML table rows retain cell separators; merged-cell geometry needs review."
                ],
            },
        )
    if path.suffix.lower() in {".txt", ".md"}:
        lines = path.read_text().splitlines()
        return lines, [{} for _ in lines], {"parser": "native-text", "warnings": []}
    raise ValueError("Supported input formats: PDF, HTML, TXT, MD")


def ingest(packet, output):
    """Ingest local originals atomically at manifest level; source IDs are immutable."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "sources.json").exists():
        raise ValueError("Output corpus already exists; use a new directory for a new version")
    manifest = {"version": "2", "sources": []}
    for spec in packet["sources"]:
        source_id = spec["id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id):
            raise ValueError("Source ID must be a safe filename")
        if any(source["id"] == source_id for source in manifest["sources"]):
            raise ValueError("Duplicate source ID")
        original = Path(spec["input_file"])
        raw = original.read_bytes()
        lines, locations, extraction = extract(original)
        if not lines:
            raise ValueError(f"No content extracted from {source_id}")
        original_file = f"originals/{source_id}{original.suffix.lower()}"
        (output / "originals").mkdir(exist_ok=True)
        shutil.copyfile(original, output / original_file)
        text = "\n".join(lines) + "\n"
        text_file = f"{source_id}.txt"
        (output / text_file).write_text(text, encoding="utf-8")
        manifest["sources"].append(
            {
                **{key: value for key, value in spec.items() if key != "input_file"},
                "retrieved": spec.get("retrieved", date.today().isoformat()),
                "original_file": original_file,
                "original_sha256": digest(raw),
                "text_file": text_file,
                "sha256": digest(text.encode()),
                "line_locations": locations,
                "extraction": extraction,
                "complete": True,
                "locator_note": "L locators identify extracted lines; original locations supplied separately.",
            }
        )
    (output / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = ingest(json.loads(args.packet.read_text()), args.output)
    print(json.dumps({"sources": len(manifest["sources"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
