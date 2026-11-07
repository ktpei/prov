# Company document ingestion — first implementation

The current importer accepts parser-supplied **page-text JSON**, not raw PDFs,
slides, or Google Docs URLs. OCR and layout extraction are not implemented. This
boundary lets different extraction engines feed the same search/read tools.
The importer preserves supplied page numbers; it cannot prove they are correct.

## Input contract

A synthetic example (not financial evidence):

```json
{
  "documents": [
    {
      "id": "acme-q3",
      "title": "Acme Q3 presentation",
      "company": "Acme",
      "ticker": "ACME",
      "url": "https://example.com/acme-q3.pdf",
      "published": "2024-11-07",
      "source_type": "investor_presentation",
      "pages": [
        {"page": 1, "text": "Q3 results\nRevenue (USD million): 120"},
        {"page": 2, "text": "Q4 outlook\nNon-GAAP margin: 20%\nExcludes restructuring."}
      ]
    }
  ]
}
```

Keep headings, units, table headers, and footnotes in the supplied text. Empty
pages require extraction review; the importer rejects empty text rather than
silently declaring an incomplete extraction successful. Page numbers must be
positive and increasing, but need not be consecutive (selected pages are allowed).
The manifest does not claim complete-document coverage.

```sh
python3 -m provenance ingest --input packet.json --output data/packets/acme-v1
```

This explicit command writes a new packet directory containing extracted text,
SHA256 checksums, and a source manifest with line-to-page ranges. Existing paths
are never overwritten. These are hashes of extracted text, not hashes of original
PDFs. Retaining original files and extraction configuration remains next work.
Do not use private deal materials; the project uses public sources only.

## Retrieval behavior

Search ranks 20-line windows using lexical term overlap and source metadata,
returning one best matching window per source, up to five local sources. It is
an initial baseline, not semantic search or structure-aware table chunking.
Search snippets do not authorize citations: read the evidence first.

Reads return bounded lines, original page numbers when supplied by the importer,
and `next_start_line` for navigation. They do not infer missing table headers or
repair extraction errors. Keep context supplied to the model bounded; retaining
a complete packet on disk does not put it all into each model request.

A live exploratory run can select a packet with `--corpus data/packets/acme-v1`.
Benchmark `--task` runs reject alternate corpora and web retrieval. New packet
experiments need a separately versioned evaluation; the frozen 25 tasks are unchanged.

## Next extraction comparison

Compare native extraction, Docling, and Unlimited-OCR on representative filing
pages and investor slides. Measure numbers/signs, units, headers, footnotes,
reading order, original-page mapping, extraction coverage, latency, and cost.
Record versions and preserve originals. Add layout-aware chunks and selective
page-image reading after identifying failures. No parser winner is claimed yet.
