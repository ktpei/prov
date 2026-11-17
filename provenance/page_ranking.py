"""Experimental local page-rank ablation; not an agent tool or promoted policy."""

import math
import re
from fractions import Fraction

from provenance.sources import _bm25, _query_terms


def compare_page_ranking(sources, query):
    """Score one shared pool; return unchanged hit payloads and auditable rankings.

    Both selections compute passage and page scores. This performs no reads and
    gives no evidence credit for the full page text used only during ranking.
    """
    if sources.exa_key or sources.retrieval_version != "bm25-v2" or len(sources.documents) != 1:
        raise ValueError("Page ranking requires local bm25-v2 sources scoped to one document")
    pages = {}
    for source_id, source in sorted(sources.documents.items()):
        lines = source["text"].splitlines()
        locations = source.get("line_locations")
        extraction = source.get("extraction")
        count = extraction.get("page_count") if isinstance(extraction, dict) else None
        if type(count) is not int or count < 1 or not isinstance(locations, list):
            raise ValueError("Page ranking requires complete physical-page metadata")
        if len(locations) != len(lines):
            raise ValueError("Page ranking requires complete line mappings")
        numbers = [p.get("page") if isinstance(p, dict) else None for p in locations]
        if (
            any(type(n) is not int or not 1 <= n <= count for n in numbers)
            or numbers != sorted(numbers)
            or set(numbers) != set(range(1, count + 1))
        ):
            raise ValueError("Page ranking requires ordered complete physical-page mappings")
        metadata = " ".join(str(source.get(k, "")) for k in ("title", "company", "ticker"))
        page_lines = {number: [] for number in range(1, count + 1)}
        for line, number in zip(lines, numbers, strict=True):
            page_lines[number].append(line)
        for number, content in page_lines.items():
            text = "\n".join(content)
            pages[source_id, number] = re.findall(r"\w+", (text + " " + metadata).lower())
    terms = _query_terms(query)
    average = sum(map(len, pages.values())) / max(len(pages), 1)
    counts = {term: sum(term in tokens for tokens in pages.values()) for term in terms}
    idf = {
        term: math.log(1 + (len(pages) - count + 0.5) / (count + 0.5))
        for term, count in counts.items()
    }
    scores = {key: _bm25(tokens, idf, average) for key, tokens in pages.items()}
    ordered_pages = sorted(pages, key=lambda key: (-scores[key], *key))
    page_ranks = {
        key: rank for rank, key in enumerate((key for key in ordered_pages if scores[key] > 0), 1)
    }
    ranked, passage_idf, passage_average = sources._local_ranking(query)
    pool = ranked[:25]
    candidates = []
    for rank, (score, passage, source) in enumerate(pool, 1):
        mappings = source["line_locations"][passage["start_line"] - 1 : passage["end_line"]]
        physical_pages = {mapping["page"] for mapping in mappings}
        if len(physical_pages) != 1:
            raise ValueError("Page ranking requires single-page candidate passages")
        page = next(iter(physical_pages))
        page_rank = page_ranks.get((source["id"], page))
        fused = Fraction(1, 60 + rank)
        if page_rank is not None:
            fused += Fraction(1, 60 + page_rank)
        candidates.append((fused, rank, page, page_rank, score))
    order = sorted(range(len(pool)), key=lambda i: (-candidates[i][0], candidates[i][1]))
    return {
        "version": "page-rrf-ablation-v1",
        "candidate_limit": 25,
        "read_limit": 5,
        "rrf_constant": 60,
        "page_ranks": [
            {"source_id": key[0], "page": key[1], "rank": page_ranks.get(key), "score": scores[key]}
            for key in ordered_pages
        ],
        "candidates": [
            {
                "source_id": pool[i][2]["id"],
                "start_line": pool[i][1]["start_line"],
                "end_line": pool[i][1]["end_line"],
                "passage_rank": rank,
                "passage_score": score,
                "page": page,
                "page_rank": page_rank,
                "rrf_numerator": fused.numerator,
                "rrf_denominator": fused.denominator,
            }
            for i, (fused, rank, page, page_rank, score) in enumerate(candidates)
        ],
        "control": sources._passage_hits(pool[:5], passage_idf, passage_average),
        "challenger": sources._passage_hits(
            [pool[i] for i in order[:5]], passage_idf, passage_average
        ),
    }
