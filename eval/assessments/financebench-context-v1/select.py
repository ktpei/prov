"""Deterministic metadata-only selection; no question/reference fields are projected."""

import json
from collections import defaultdict
from pathlib import Path

from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REVISION = "cc39aeb4afdf33909ee1412188bf89035950c2eb"
TASK_SHA = "a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877"
DOC_SHA = "1c69127783879de8cdadb159d2181f39bc3123b8e0ebf74031c3969d69189575"
ALIASES = {
    "MRO/2007": "Marathon Oil",
    "RSG/2015": "Republic Services",
    "AES/2002": "AES Corporation",
    "GS/2017": "Goldman Sachs",
    "GPN/2009": "Global Payments",
}


def select():
    task_path = ROOT / "runs/benchmark-data/financebench-public-v2/financebench-public.jsonl"
    doc_path = ROOT / "runs/benchmark-data/financebench-documents/financebench-documents.jsonl"
    registry_path = ROOT / "eval/development-exposures.json"
    if digest(task_path) != TASK_SHA or digest(doc_path) != DOC_SHA:
        raise ValueError("Pinned data identity mismatch")
    tasks = [
        {"id": row["financebench_id"], "doc_name": row["doc_name"], "company": row["company"]}
        for row in map(json.loads, task_path.read_text().splitlines())
    ]
    if len({r["id"] for r in tasks}) != len(tasks):
        raise ValueError("Duplicate task ID")
    docs = defaultdict(list)
    for row in map(json.loads, doc_path.read_text().splitlines()):
        docs[row["doc_name"]].append(row)
    registry = json.loads(registry_path.read_bytes())
    exposed = {r["group"] for r in registry["groups"]}
    known = dict(ALIASES)
    unresolved = []
    for group in sorted(exposed):
        if group in docs:
            if len(docs[group]) != 1:
                raise ValueError("Ambiguous exposed document identity")
            known[group] = docs[group][0]["company"]
        elif group not in known:
            unresolved.append(group)
    excluded_companies = {v.casefold() for v in known.values()}
    groups = defaultdict(list)
    for task in tasks:
        groups[task["doc_name"]].append(task)
    ledger = []
    for name, candidates in sorted(groups.items()):
        rows = docs.get(name, [])
        entry = {"doc_name": name, "task_ids": sorted(t["id"] for t in candidates)}
        if len(rows) != 1:
            entry.update(disposition="ambiguous_or_missing_metadata", metadata_rows=rows)
            if any(r["doc_type"] == "10k" for r in rows):
                raise ValueError("Ambiguous eligible 10-K join")
            ledger.append(entry)
            continue
        doc = rows[0]
        if any(t["company"] != doc["company"] for t in candidates):
            raise ValueError("Company metadata mismatch")
        entry.update(document=doc, group_rank=canonical_hash([17, "context-validation-v1", name]))
        if doc["doc_type"] != "10k":
            reason = "not_10k"
        elif int(canonical_hash([17, name])[:8], 16) % 5 == 0:
            reason = "internal_final"
        elif name in exposed:
            reason = "exposed_group"
        elif doc["company"].casefold() in excluded_companies:
            reason = "known_exposed_company"
        else:
            reason = "eligible"
        entry["disposition"] = reason
        ledger.append(entry)
    selected, companies = [], set()
    for entry in sorted(
        (e for e in ledger if e["disposition"] == "eligible"),
        key=lambda e: (e["group_rank"], e["doc_name"]),
    ):
        company = entry["document"]["company"].casefold()
        if company in companies:
            entry["disposition"] = "same_company_as_selected"
            continue
        if len(selected) == 6:
            continue
        task_id = min(entry["task_ids"], key=lambda i: (canonical_hash([17, i]), i))
        entry["disposition"] = "selected"
        selected.append(
            {"selection_rank": len(selected) + 1, "task_id": task_id, **entry["document"]}
        )
        companies.add(company)
    if len(selected) != 6:
        raise ValueError("Insufficient eligible companies")
    return {
        "version": "financebench-context-selection-v1",
        "revision": REVISION,
        "seed": 17,
        "task_sha256": TASK_SHA,
        "document_metadata_sha256": DOC_SHA,
        "selector_sha256": digest(__file__),
        "plan_sha256": digest(HERE / "plan.md"),
        "registry_sha256": digest(registry_path),
        "registry_snapshot": registry,
        "known_exposed_company_map": known,
        "unresolved_exposed_groups": unresolved,
        "selected": selected,
        "prepared_order_ids": sorted(
            [r["task_id"] for r in selected], key=lambda i: (canonical_hash([17, i]), i)
        ),
        "ledger": ledger,
        "metadata_conflicts": {name: rows for name, rows in docs.items() if len(rows) != 1},
    }


if __name__ == "__main__":
    result = select()
    with (HERE / "selection.json").open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["selected"], indent=2))
