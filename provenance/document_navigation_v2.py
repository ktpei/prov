"""Second navigation treatment: preserve target rows within bounded read context."""

import copy
import json

from provenance.document_navigation import (
    NAVIGATION_INSTRUCTIONS,
    NAVIGATION_TOOLS,
    NavigableExaSources,
)
from provenance.sources import _query_terms

NAVIGATION_V2_TOOLS = copy.deepcopy(NAVIGATION_TOOLS)
NAVIGATION_V2_TOOLS[1]["description"] = (
    "Read up to 80 numbered lines, bounded by response size. Include the target row "
    "and its headers. If next_start_line is returned, continue there for omitted lines."
)
NAVIGATION_V2_INSTRUCTIONS = (
    NAVIGATION_INSTRUCTIONS.replace(
        "Reads return at most 30 lines; use next_start_line or targeted neighboring reads",
        "Reads return up to 80 lines within a character budget; use next_start_line or neighboring reads",
    )
    + """
After find_in_source locates a promising metric row, read that range immediately
before spending another turn on finding. Include its header and units when possible.
Reserve time to read evidence before the final answer; discovery alone cannot be cited.
Query-term coverage is lexical, not a claim that the metric is present or absent.
If repeated finds miss the distinctive metric, change source or query rather than
searching that same document again, especially when extraction reached its cap.
Prefer precise financial-statement rows over rounded narrative amounts when both
are available. Do not infer table columns from detached numbers without headers.
"""
)


class NavigableExaSourcesV2(NavigableExaSources):
    def search(self, query, timeout, objective=None):
        result = super().search(query, timeout, objective)
        # Discovery stays compact, leaving room for a wider exact evidence read.
        for hit in result["results"]:
            if "highlights" in hit:
                hit["highlights"] = [text[:700] for text in hit["highlights"][:1]]
        return result

    def find(self, source_id, query, timeout):
        result = super().find(source_id, query, timeout)
        terms = _query_terms(query)
        lines = self.documents[source_id]["text"].splitlines()
        present = _query_terms("\n".join(lines)) & terms
        result["missing_query_terms"] = sorted(terms - present)
        for match in result["matches"]:
            tokens = _query_terms("\n".join(lines[match["start_line"] - 1 : match["end_line"]]))
            match["matched_query_terms"] = sorted(tokens & terms)
        return result

    def read(self, source_id, start, end, timeout):
        if type(start) is not int or type(end) is not int or not 1 <= start <= end < start + 80:
            raise ValueError("Read requires a positive range of at most 80 lines")
        source = self._document(source_id, timeout)
        lines = source["text"].splitlines()
        size, actual_end = 0, start - 1
        for line in range(start, min(end, len(lines)) + 1):
            size += len(json.dumps({"line": line, "text": lines[line - 1]}))
            if size > 9000:
                break
            actual_end = line
        if actual_end < start:
            raise ValueError("No source lines fit; verify start_line against total_lines")
        # Bypass v1's 30-line clamp, retaining Sources' exact citation bookkeeping.
        from provenance.sources import Sources

        result = Sources.read(self, source_id, start, actual_end, timeout)
        result["extraction_at_character_limit"] = source.get("extraction_at_character_limit", False)
        return result
