"""Objective-aware Exa search for the existing bounded research loop.

Uses the documented raw HTTP API to preserve the application's durable budget
settlement, strict timeouts and no-retry policy. Search snippets are discovery
context; citations still require explicit read_source calls.
"""

import copy
import hashlib
from urllib.parse import urlparse

from provenance.controls import LimitReached
from provenance.model import INSTRUCTIONS
from provenance.sources import TOOL_SCHEMAS, Sources
from provenance.transport import ProviderError

OBJECTIVE_DESCRIPTION = (
    "Goal for this search turn; say which documents should rank first, which should be "
    "excluded, and what specific facts or figures to pull from them."
)
EXA_TOOL_SCHEMAS = copy.deepcopy(TOOL_SCHEMAS)
EXA_TOOL_SCHEMAS[0]["description"] = (
    "Search the live web and local company evidence. Returns relevant URLs and short "
    "highlights; read_source opens numbered evidence for citations."
)
EXA_TOOL_SCHEMAS[0]["parameters"]["properties"]["objective"] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 4096,
    "description": OBJECTIVE_DESCRIPTION,
}
EXA_TOOL_SCHEMAS[0]["parameters"]["required"].append("objective")
EXA_INSTRUCTIONS = (
    INSTRUCTIONS
    + """
Call search before answering unless you're certain the answer can't have changed since your training cutoff.
For each search provide both query and objective. The objective should state the
research goal, which original documents to prioritize, and which facts to find.
For company financial research queries, start query with:
Prefer a specific primary or official answer page.
For lookups of a specific known page, send the page lookup unchanged. Search
highlights are discovery context, not read evidence; call read_source before citing.
"""
)


class ExaSources(Sources):
    def search(self, query, timeout, objective=None):
        if not self.exa_key:
            return super().search(query, timeout)
        if not isinstance(objective, str) or not objective.strip() or len(objective) > 4096:
            raise ValueError("Web search requires a nonempty objective of at most 4096 characters")
        ranked, idf, average_length = self._local_ranking(query)
        hits = self._passage_hits(ranked[:5], idf, average_length)
        result = self._exa(
            "search",
            {
                "query": query,
                "objective": objective,
                "type": "auto",
                # Intentional lean benchmark budget: at most five candidates per search.
                "numResults": 5,
                "contents": {"highlights": True},
            },
            timeout,
        )
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
            highlights = item.get("highlights", [])
            hits.append(
                {
                    **self.metadata(self.documents[source_id]),
                    "highlights": [h[:1500] for h in highlights[:3] if isinstance(h, str)],
                    "note": "Discovery highlights; use read_source for citable numbered lines.",
                }
            )
        return {"results": hits, "mode": "corpus+web"}

    def _exa(self, endpoint, payload, timeout):
        result = super()._exa(endpoint, payload, timeout)
        if endpoint == "contents":
            # HTTP 200 may still contain per-URL crawl failures. Costs are settled first.
            requested = set(payload["urls"])
            for status in result.get("statuses", []):
                if status.get("id") in requested and status.get("status") != "success":
                    raise ProviderError("Exa could not extract the requested source")
        return result

    def call(self, name, args, timeout):
        if name != "search" or not self.exa_key:
            return super().call(name, args, timeout)
        try:
            if not isinstance(args, dict) or set(args) != {"query", "objective"}:
                raise ValueError("Web search requires query and objective")
            query = args["query"]
            if not isinstance(query, str) or not query.strip() or len(query) > 500:
                raise ValueError("query must contain 1–500 characters")
            return self.search(query, timeout, args["objective"])
        except LimitReached:
            raise
        except (ValueError, ProviderError) as exc:
            return {"error": str(exc)}
