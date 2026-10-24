"""Small, read-only retrieval tools. Gold answers never enter this module."""

import hashlib
import json
import re
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
        "Search public financial sources. Returns IDs and metadata; read_source retrieves evidence.",
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


class Sources:
    def __init__(self, directory, *, exa_key=None, exa_cap=None, budget=None, request=post_json):
        self.directory = Path(directory)
        manifest = json.loads((self.directory / "sources.json").read_text())
        self.documents = {}
        self.seen = {}
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
            self.documents[source["id"]] = {**source, "text": raw.decode("utf-8")}

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
        terms = set(re.findall(r"\w+", query.lower()))
        ranked = []
        for source in self.documents.values():
            haystack = " ".join(
                str(source.get(k, "")) for k in ("title", "company", "ticker", "text")
            )
            score = len(terms & set(re.findall(r"\w+", haystack.lower())))
            if score:
                ranked.append((score, source))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        hits = [self.metadata(source) for _, source in ranked[:5]]
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
            "lines": selected,
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
