"""Question-only experimental DPO component retrieval; no formula or answer inference."""

import re

POLICY = "dpo-component-round-robin-v1"
CONTEXT_POLICY = "dpo-statement-context-round-robin-v1"
POLICIES = (POLICY, CONTEXT_POLICY)
COMPONENT_QUERIES = (
    "accounts payable trade payables",
    "purchases credit purchases",
    "cost of sales cost of goods sold",
    "inventory inventories",
)


def plan_queries(question, *, policy=POLICY):
    if policy not in POLICIES:
        raise ValueError("Unknown component query policy")
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        raise ValueError("Question must contain 1–500 characters")
    if not re.search(r"\bdays\s+payable\s+outstanding\b", question, re.IGNORECASE):
        return [question]
    years = " ".join(dict.fromkeys(re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", question)))
    components = list(COMPONENT_QUERIES)
    if policy == CONTEXT_POLICY and not re.search(
        r"\b(?:not|never|without|exclude|excluding|avoid|except)\b|don['’]t|rather\s+than|instead\s+of",
        question,
        re.IGNORECASE,
    ):
        if re.search(
            r"\bbalance\s+sheets?\b|\bstatements?\s+of\s+financial\s+position\b",
            question,
            re.IGNORECASE,
        ):
            for index in (0, 3):
                components[index] += " balance sheet sheets statement statements financial position"
        if re.search(
            r"\bp\s*&\s*l\b|\bprofit\s+and\s+loss\b|\bincome\s+statements?\b|\bstatements?\s+of\s+(?:operations|income)\b",
            question,
            re.IGNORECASE,
        ):
            components[2] += " income statement statements operations profit loss"
    queries = [question, *(f"{query} {years}".rstrip() for query in components)]
    if any(len(query) > 500 for query in queries):
        raise ValueError("Generated component query exceeds 500 characters")
    return queries


def retrieve(sources, question, *, timeout=1, policy=POLICY):
    queries = plan_queries(question, policy=policy)
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
