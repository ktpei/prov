"""Source-scoped discovery over immutable extracted documents, with bounded reads."""

import copy
import hashlib
import math
import re

from provenance.controls import LimitReached
from provenance.exa_sources import EXA_INSTRUCTIONS, EXA_TOOL_SCHEMAS, ExaSources
from provenance.sources import _bm25, _query_terms, function
from provenance.transport import ProviderError

# Even JSON-escaped astral Unicode (12 bytes/character) fits the 2 MB transport cap,
# leaving room for provider metadata. This is retained text, not model context.
DOCUMENT_CHAR_LIMIT = 150_000
NAVIGATION_TOOLS = copy.deepcopy(EXA_TOOL_SCHEMAS)
NAVIGATION_TOOLS[1]["description"] = (
    "Read up to 30 numbered lines from a discovered source. Use find_in_source first "
    "to locate the requested table; read surrounding headers and units before answering."
)
NAVIGATION_TOOLS.append(
    function(
        "find_in_source",
        "Find relevant passages anywhere in one discovered document. Returns navigation "
        "snippets and line ranges, not citation evidence. Use read_source on those ranges.",
        {
            "source_id": {"type": "string"},
            "query": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    )
)
NAVIGATION_INSTRUCTIONS = (
    EXA_INSTRUCTIONS.replace(
        "Search is lexical; Boolean operators and quoted phrases have no special syntax.",
        "Web search discovers pages; find_in_source uses lexical matching within a page.",
    )
    + """
Once search finds a promising filing, use find_in_source with distinctive metric
terms to locate evidence inside it rather than searching the web repeatedly or
reading sequentially from the beginning. Then read_source at the returned lines.
Find snippets are navigation only. Read the table headers, units and relevant row
before citing. If the first query finds nothing, try a shorter metric synonym.
Reads return at most 30 lines; use next_start_line or targeted neighboring reads
when a header or row is missing. The cached extraction may be incomplete; a missing
match does not prove the original document lacks the information.
Before finalizing, verify the source period and requested period agree, especially
standalone quarter versus year-to-date. Never substitute a cumulative figure for
a standalone quarter. Keep the answer concise and omit unrelated financial figures.
"""
)


class NavigableExaSources(ExaSources):
    def _document(self, source_id, timeout):
        if source_id not in self.documents:
            raise ValueError("Unknown source_id; use search first")
        source = self.documents[source_id]
        if source["text"] is None:
            result = self._exa(
                "contents",
                {"urls": [source["url"]], "text": {"maxCharacters": DOCUMENT_CHAR_LIMIT}},
                timeout,
            )
            rows = result.get("results", [])
            if not rows or rows[0].get("url") != source["url"]:
                raise ProviderError("No matching document text returned")
            raw = rows[0].get("text")
            if not isinstance(raw, str) or not raw.strip():
                raise ProviderError("No matching document text returned")
            source["extraction_at_character_limit"] = len(raw) >= DOCUMENT_CHAR_LIMIT
            raw = raw[:DOCUMENT_CHAR_LIMIT]
            source["text"] = "\n".join(
                line[i : i + 200]
                for line in raw.splitlines()
                for i in range(0, max(1, len(line)), 200)
            )
        return source

    def find(self, source_id, query, timeout):
        source = self._document(source_id, timeout)
        lines = source["text"].splitlines()
        terms = _query_terms(query)
        passages = [
            (start, re.findall(r"\w+", "\n".join(lines[start : start + 24]).lower()))
            for start in range(0, len(lines), 16)
        ]
        idf = {
            term: math.log(1 + (len(passages) - count + 0.5) / (count + 0.5))
            for term in terms
            if (count := sum(term in tokens for _, tokens in passages))
        }
        average = sum(len(tokens) for _, tokens in passages) / max(len(passages), 1)
        ranked = sorted(
            ((_bm25(tokens, idf, average), start) for start, tokens in passages),
            key=lambda item: (-item[0], item[1]),
        )
        matches = []
        for score, start in ranked:
            if score <= 0 or len(matches) == 3:
                break
            if any(abs(start + 1 - match["start_line"]) < 24 for match in matches):
                continue
            matches.append(
                {
                    "start_line": start + 1,
                    "end_line": min(start + 24, len(lines)),
                    "snippet": "\n".join(lines[start : start + 24])[:900],
                }
            )
        return {
            **self.metadata(source),
            "matches": matches,
            "total_lines": len(lines),
            "sha256": hashlib.sha256(source["text"].encode()).hexdigest(),
            "extraction_at_character_limit": source.get("extraction_at_character_limit", False),
            "context_complete": False,
            "note": "Navigation only; read the returned ranges and neighboring headers to cite.",
        }

    def read(self, source_id, start, end, timeout):
        if type(start) is not int or type(end) is not int or not 1 <= start <= end < start + 80:
            raise ValueError("Read requires a positive range of at most 80 lines")
        source = self._document(source_id, timeout)
        result = super().read(source_id, start, min(end, start + 29), timeout)
        result["extraction_at_character_limit"] = source.get("extraction_at_character_limit", False)
        return result

    def call(self, name, args, timeout):
        if name != "find_in_source":
            return super().call(name, args, timeout)
        try:
            if not isinstance(args, dict) or set(args) != {"source_id", "query"}:
                raise ValueError("find_in_source requires source_id and query")
            if not isinstance(args["source_id"], str):
                raise ValueError("source_id must be a string")
            query = args["query"]
            if not isinstance(query, str) or not query.strip() or len(query) > 500:
                raise ValueError("query must contain 1–500 characters")
            return self.find(args["source_id"], query, timeout)
        except LimitReached:
            raise
        except (ValueError, ProviderError) as exc:
            return {"error": str(exc)}
