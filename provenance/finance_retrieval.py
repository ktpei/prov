"""Question-only experimental DPO component retrieval; no formula or answer inference."""

import re

POLICY = "dpo-component-round-robin-v1"
COMPONENT_QUERIES = (
    "accounts payable trade payables",
    "purchases credit purchases",
    "cost of sales cost of goods sold",
    "inventory inventories",
)


def plan_queries(question):
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        raise ValueError("Question must contain 1–500 characters")
    if not re.search(r"\bdays\s+payable\s+outstanding\b", question, re.IGNORECASE):
        return [question]
    years = " ".join(dict.fromkeys(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", question)))
    queries = [question, *(f"{query} {years}".rstrip() for query in COMPONENT_QUERIES)]
    if any(len(query) > 500 for query in queries):
        raise ValueError("Generated component query exceeds 500 characters")
    return queries


def retrieve(sources, question, *, timeout=1):
    queries = plan_queries(question)
    traces = []
    for query in queries:
        response = sources.search(query, timeout=timeout)
        hits = response["results"]
        if not isinstance(hits, list) or len(hits) > 5:
            raise ValueError("Component search must return at most five hits")
        traces.append({"query": query, "response": response})
    # Each query gets one rank position per round. Original query goes first.
    # BM25 scores from different queries are not treated as comparable.
    selected, seen = [], set()
    for rank in range(5):
        for trace in traces:
            hits = trace["response"]["results"]
            if rank >= len(hits):
                continue
            hit = hits[rank]
            key = (hit["id"], hit["start_line"], hit["end_line"])
            if key not in seen:
                selected.append(hit)
                seen.add(key)
                if len(selected) == 5:
                    return selected, traces
    return selected, traces
