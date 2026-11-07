# Cloudflare company source packet

Frozen public company evidence for the company-context research milestone.
Reporting cutoff: November 7, 2024. The May investor presentation predates Q3 results.

| Source | Published | Format / original locations |
| --- | --- | --- |
| [Cloudflare Announces Third Quarter 2024 Financial Results](https://www.cloudflare.net/news/news-details/2024/Cloudflare-Announces-Third-Quarter-2024-Financial-Results/default.aspx) | 2024-11-07 | HTML, section + extracted line |
| [Cloudflare Form 10-Q September 30 2024](https://www.sec.gov/Archives/edgar/data/1477333/000147733324000085/cloud-20240930.htm) | 2024-11-07 | HTML, section + extracted line |
| [Cloudflare Q3 2024 Earnings Call Corrected Transcript](https://www.cloudflare.net/files/doc_financials/2024/q3/CORRECTED-TRANSCRIPT_-Cloudflare-Inc-NET-US-Q3-2024-Earnings-Call-7-November-2024-5_00-PM-ET.pdf) | 2024-11-07 | PDF, 18 pages |
| [Cloudflare Investor Day May 30 2024](https://www.cloudflare.net/files/doc_downloads/Presentations/2024/05/Cloudflare-Investor-Day-2024.pdf) | 2024-05-30 | PDF, 116 pages |

All original bytes, extracted text, SHA256 hashes, and page/section mappings are
in `data/cloudflare-2024-q3`. The loader verifies originals and extracted text.
Read results identify extracted line numbers separately from original pages.

## Reproduce

From the repository root, with `uv sync --locked` complete:

```sh
uv run python -m provenance.ingestion data/cloudflare-2024-q3/packet.json /tmp/cloudflare-reingested
uv run python -m provenance.evaluation --corpus data/cloudflare-2024-q3 --benchmark eval/company_tasks.json
```

Use a new output directory for ingestion. Input paths in packet.json are relative
to the repository root. The originals are frozen, so evaluation needs no network.

## Extraction status

The baseline uses native HTML parsing and pypdf layout text, not OCR. The HTML
parser preserves table-cell separators and omits hidden XBRL metadata. PDF pages
retain original page identity. Every PDF page was processed; text completeness
and table/chart semantics remain unverified.

Visual spot checks compared transcript page 4 and investor-deck page 105 against
the extracted text. Transcript facts and deck operating-margin values survived.
The deck's stacked expense chart components interleave in text: chart-series
interpretation still requires original visual inspection. Reads explicitly flag
incomplete surrounding header/footnote context.

Docling and Unlimited-OCR remain unmeasured challenger parsers. We have not
selected an OCR provider or established a GPU/hosted setup. Successful text
extraction or anchor matching does not establish financial accuracy.
