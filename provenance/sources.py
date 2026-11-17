"""Small, read-only retrieval tools. Gold answers never enter this module."""

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from provenance.controls import LimitReached, positive
from provenance.transport import ProviderError, post_json


def function(name, description, properties):
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


TOOL_SCHEMAS = [
    function(
        "search",
        "Search company evidence passages. Returns bounded line ranges; read_source opens evidence.",
        {"query": {"type": "string", "minLength": 1, "maxLength": 500}},
    ),
    function(
        "read_source",
        "Read up to 80 numbered lines from a source ID returned by search. Cite these exact lines.",
        {
            "source_id": {"type": "string"},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
        },
    ),
]


def locator_range(locator):
    match = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", locator)
    if not match:
        raise ValueError("Locator must be L1 or L1-L5")
    start, end = int(match[1]), int(match[2] or match[1])
    if start < 1 or end < start:
        raise ValueError("Invalid line range")
    return start, end


def _bm25(tokens, idf, average_length):
    """Standard BM25 with fixed k1=1.5, b=.75 and positive Robertson IDF."""
    frequencies = Counter(tokens)
    length_factor = 1.5 * (0.25 + 0.75 * len(tokens) / max(average_length, 1))
    return sum(
        weight * frequencies[term] * 2.5 / (frequencies[term] + length_factor)
        for term, weight in idf.items()
        if frequencies[term]
    )


def _snippet(passage, idf, average_length):
    """Choose complete source lines by query relevance, never rewrite evidence."""
    lines = passage["text"].splitlines()
    best = None
    for start in range(len(lines)):
        selected = []
        size = 0
        for end in range(start, len(lines)):
            size += len(lines[end]) + int(bool(selected))
            if size > 1000:
                break
            selected.append(lines[end])
            text = "\n".join(selected)
            score = _bm25(re.findall(r"\w+", text.lower()), idf, average_length)
            candidate = (score, -len(text), -start, -end, text)
            if best is None or candidate[:4] > best[:4]:
                best = candidate
    if best is None:
        return {
            "snippet": "",
            "snippet_locator": f"L{passage['start_line']}",
            "snippet_note": "Source lines exceed snippet size; use read_source for exact evidence.",
        }
    start = passage["start_line"] - best[2]
    end = passage["start_line"] - best[3]
    return {"snippet": best[4], "snippet_locator": f"L{start}-L{end}"}


class Sources:
    def __init__(
        self,
        directory,
        *,
        exa_key=None,
        exa_cap=None,
        budget=None,
        request=post_json,
        retrieval_version="bm25-v2",
    ):
        if retrieval_version not in {"passage-v1", "bm25-v2"}:
            raise ValueError("Unknown retrieval_version")
        self.retrieval_version = retrieval_version
        self.directory = Path(directory)
        manifest = json.loads((self.directory / "sources.json").read_text())
        self.documents = {}
        self.seen = {}
        self.passages = []
        self.request = request
        self.exa_key, self.exa_cap, self.budget = exa_key, exa_cap, budget
        if exa_key:
            positive(exa_cap, "EXA_MAX_REQUEST_USD")
        for source in manifest["sources"]:
            path = (self.directory / source["text_file"]).resolve()
            if not path.is_relative_to(self.directory.resolve()):
                raise ValueError("Source path escapes corpus")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError(f"Corpus hash mismatch: {source['id']}")
            if source["id"] in self.documents:
                raise ValueError("Duplicate source ID")
            text = raw.decode("utf-8")
            locations = source.get("line_locations", [])
            if locations and len(locations) != len(text.splitlines()):
                raise ValueError("Line location count does not match text")
            if source.get("original_file"):
                original = (self.directory / source["original_file"]).resolve()
                if not original.is_relative_to(self.directory.resolve()):
                    raise ValueError("Original path escapes corpus")
                if hashlib.sha256(original.read_bytes()).hexdigest() != source["original_sha256"]:
                    raise ValueError(f"Original hash mismatch: {source['id']}")
            self.documents[source["id"]] = {**source, "text": text}
            lines = text.splitlines()
            start = 0
            while start < len(lines):
                end = min(start + 32, len(lines))
                # Original pages/sections delimit evidence context when supplied.
                if locations:
                    for offset in range(start + 1, end):
                        if locations[offset] != locations[start]:
                            end = offset
                            break
                passage = "\n".join(lines[start:end])
                self.passages.append(
                    {
                        "source_id": source["id"],
                        "start_line": start + 1,
                        "end_line": end,
                        "text": passage,
                        "terms": re.findall(r"\w+", passage.lower()),
                    }
                )
                start = end if end < start + 32 else start + 24

    def _exa(self, endpoint, payload, timeout):
        reserved = self.budget.reserve(self.exa_cap)
        try:
            result = self.request(
                f"https://api.exa.ai/{endpoint}",
                payload,
                {"x-api-key": self.exa_key},
                timeout,
            )
            actual = result.get("costDollars", {}).get("total")
            if actual is None:
                self.budget.uncertain = True  # retain full reservation when billing is absent
            else:
                self.budget.settle(reserved, actual)
            return result
        except BaseException:
            self.budget.uncertain = True
            raise

    def search(self, query, timeout):
        stopwords = {"the", "a", "an", "of", "to", "and", "in", "for", "what", "was", "is", "did"}
        terms = set(re.findall(r"\w+", query.lower())) - stopwords
        passages = [item for item in self.passages if item["source_id"] in self.documents]
        if self.retrieval_version == "passage-v1":
            counts = {term: sum(term in item["terms"] for item in passages) for term in terms}
            ranked = []
            for passage in passages:
                source = self.documents[passage["source_id"]]
                score = sum(
                    math.log(1 + len(passages) / (1 + counts[term]))
                    * min(passage["terms"].count(term), 3)
                    for term in terms
                )
                metadata_terms = set(
                    re.findall(
                        r"\w+",
                        " ".join(
                            str(source.get(k, "")) for k in ("title", "company", "ticker")
                        ).lower(),
                    )
                )
                score += 0.2 * len(terms & metadata_terms)
                if score:
                    ranked.append((score, passage, source))
        else:
            indexed = []
            for passage in passages:
                source = self.documents[passage["source_id"]]
                metadata = " ".join(
                    str(source.get(key, "")) for key in ("title", "company", "ticker")
                )
                tokens = passage["terms"] + re.findall(r"\w+", metadata.lower())
                indexed.append((passage, source, tokens))
            average_length = sum(len(tokens) for _, _, tokens in indexed) / max(len(indexed), 1)
            counts = {term: sum(term in tokens for _, _, tokens in indexed) for term in terms}
            idf = {
                term: math.log(1 + (len(indexed) - count + 0.5) / (count + 0.5))
                for term, count in counts.items()
            }
            ranked = []
            for passage, source, tokens in indexed:
                score = _bm25(tokens, idf, average_length)
                if score:
                    ranked.append((score, passage, source))
        ranked.sort(key=lambda item: (-item[0], item[2]["id"], item[1]["start_line"]))
        hits = []
        for score, passage, source in ranked[:5]:
            hits.append(
                {
                    **self.metadata(source),
                    "start_line": passage["start_line"],
                    "end_line": passage["end_line"],
                    **(
                        {"snippet": passage["text"][:1000]}
                        if self.retrieval_version == "passage-v1"
                        else _snippet(passage, idf, average_length)
                    ),
                    "score": round(score, 4),
                    "original_location": source.get("line_locations", [{}] * passage["start_line"])[
                        passage["start_line"] - 1
                    ],
                }
            )
        if self.exa_key:
            result = self._exa("search", {"query": query, "type": "auto", "numResults": 5}, timeout)
            for item in result.get("results", [])[:5]:
                url = item.get("url", "")
                parsed = urlparse(url)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                ):
                    continue
                source_id = "web-" + hashlib.sha256(url.encode()).hexdigest()[:16]
                self.documents.setdefault(
                    source_id,
                    {
                        "id": source_id,
                        "url": url,
                        "title": item.get("title", url)[:300],
                        "published": item.get("publishedDate"),
                        "text": None,
                    },
                )
                hits.append(self.metadata(self.documents[source_id]))
        return {"results": hits, "mode": "corpus+web" if self.exa_key else "frozen_corpus"}

    @staticmethod
    def metadata(source):
        return {k: source.get(k) for k in ("id", "title", "url", "published")}

    def read(self, source_id, start, end, timeout):
        if source_id not in self.documents:
            raise ValueError("Unknown source_id; use search first")
        if type(start) is not int or type(end) is not int or not (1 <= start <= end < start + 80):
            raise ValueError("Read requires a positive range of at most 80 lines")
        source = self.documents[source_id]
        if source["text"] is None:
            result = self._exa(
                "contents", {"urls": [source["url"]], "text": {"maxCharacters": 16000}}, timeout
            )
            rows = result.get("results", [])
            if not rows or rows[0].get("url") != source["url"] or not rows[0].get("text"):
                raise ProviderError("No matching document text returned")
            # Wrap long paragraphs into stable local lines without altering characters.
            raw = rows[0]["text"][:16000]
            source["text"] = "\n".join(
                line[i : i + 200]
                for line in raw.splitlines()
                for i in range(0, max(1, len(line)), 200)
            )
        lines = source["text"].splitlines()
        if start > len(lines):
            raise ValueError("start_line is beyond the document")
        end = min(end, len(lines))
        selected, size = [], 0
        for i in range(start, end + 1):
            line = lines[i - 1]
            if size + len(line) > 18000:
                break
            selected.append({"line": i, "text": line})
            size += len(line)
        if not selected:
            raise ValueError("Source line exceeds result size limit")
        actual_end = selected[-1]["line"]
        self.seen.setdefault(source_id, set()).update(range(start, actual_end + 1))
        return {
            **self.metadata(source),
            "lines": [
                {**line, "original_location": source["line_locations"][line["line"] - 1]}
                if source.get("line_locations")
                else line
                for line in selected
            ],
            "next_start_line": actual_end + 1 if actual_end < len(lines) else None,
            "original_sha256": source.get("original_sha256"),
            "context_complete": False,
            "context_note": (
                "Bounded excerpt: headers, units, footnotes or chart geometry may require "
                "surrounding reads and inspection of the original document."
            ),
            "extraction": source.get("extraction"),
            "total_lines": len(lines),
            "locator": f"L{start}-L{actual_end}",
            "sha256": hashlib.sha256(source["text"].encode()).hexdigest(),
            "locator_note": source.get(
                "locator_note", "Lines in retrieved text; not original page numbers"
            ),
        }

    def call(self, name, args, timeout):
        try:
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            if name == "search" and set(args) == {"query"}:
                query = args["query"]
                if not isinstance(query, str) or not query.strip() or len(query) > 500:
                    raise ValueError("query must contain 1–500 characters")
                return self.search(query, timeout)
            if name == "read_source" and set(args) == {"source_id", "start_line", "end_line"}:
                if not isinstance(args["source_id"], str):
                    raise ValueError("source_id must be a string")
                return self.read(args["source_id"], args["start_line"], args["end_line"], timeout)
            raise ValueError("Unknown tool or invalid argument fields")
        except LimitReached:
            raise
        except (ValueError, ProviderError) as exc:
            return {"error": str(exc)}

    def check_citation(self, citation):
        if not isinstance(citation, dict) or set(citation) != {"source_id", "locator", "quote"}:
            raise ValueError("Citation requires source_id, locator, quote")
        source_id, locator, quote = (citation[k] for k in ("source_id", "locator", "quote"))
        if not all(isinstance(v, str) for v in (source_id, locator, quote)):
            raise ValueError("Citation fields must be strings")
        start, end = locator_range(locator)
        if end - start >= 80:
            raise ValueError("Citation span exceeds 80 lines")
        if not set(range(start, end + 1)).issubset(self.seen.get(source_id, set())):
            raise ValueError("Citation refers to unread source lines")
        lines = self.documents[source_id]["text"].splitlines()[start - 1 : end]

        def normalize(text):
            return " ".join(text.split())

        if not quote.strip() or normalize(quote) not in normalize(" ".join(lines)):
            raise ValueError("Citation quote is absent from cited lines")
