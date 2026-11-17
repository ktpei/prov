"""Deterministic metadata-only selection; no question/reference fields are projected."""

import hashlib
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
    paths = {
        "tasks": task_path,
        "documents": doc_path,
        "registry": registry_path,
        "selector": Path(__file__),
        "plan": HERE / "plan.md",
    }
    snapshots = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in snapshots.items()}
    if hashes["tasks"] != TASK_SHA or hashes["documents"] != DOC_SHA:
        raise ValueError("Pinned data identity mismatch")
    tasks = [
        {"id": row["financebench_id"], "doc_name": row["doc_name"], "company": row["company"]}
        for row in map(json.loads, snapshots["tasks"].splitlines())
    ]
    if len({r["id"] for r in tasks}) != len(tasks):
        raise ValueError("Duplicate task ID")
    docs = defaultdict(list)
    for row in map(json.loads, snapshots["documents"].splitlines()):
        docs[row["doc_name"]].append(
            {key: row[key] for key in ("doc_name", "company", "doc_type", "doc_period", "doc_link")}
        )
    registry = json.loads(snapshots["registry"])
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
    # Also keep the separate, partly inspected native-HTML cohort out of this work.
    other_reserved_companies = ["Casey's General Stores", "Old Dominion Freight Line", "Ameren"]
    excluded_companies = {v.casefold() for v in [*known.values(), *other_reserved_companies]}
    groups = defaultdict(list)
    for task in tasks:
        groups[task["doc_name"]].append(task)
    ledger = []
    for name, candidates in sorted(groups.items()):
        rows = docs.get(name, [])
        original_partition = (
            "internal_final" if int(canonical_hash([17, name])[:8], 16) % 5 == 0 else "development"
        )
        entry = {
            "doc_name": name,
            "task_ids": sorted(t["id"] for t in candidates),
            "original_partition": original_partition,
            "group_rank": canonical_hash([17, "page-ranking-validation-v1", name]),
        }
        if len(rows) != 1:
            entry.update(disposition="ambiguous_or_missing_metadata", metadata_rows=rows)
            if any(r["doc_type"] == "10k" for r in rows):
                raise ValueError("Ambiguous eligible 10-K join")
            ledger.append(entry)
            continue
        doc = rows[0]
        if any(t["company"] != doc["company"] for t in candidates):
            raise ValueError("Company metadata mismatch")
        entry.update(document=doc, normalized_company=doc["company"].casefold())
        if doc["doc_type"] != "10k":
            reason = "not_10k"
        elif original_partition == "internal_final":
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
    if any(digest(path) != hashes[name] for name, path in paths.items()):
        raise ValueError("Selection input changed during reservation")
    return {
        "version": "financebench-page-validation-reservation-v1",
        "status": "metadata_only_reserved_no_content_opened",
        "original_partition": "development",
        "purpose": "prospective_local_validation_not_secret_or_model_unseen",
        "revision": REVISION,
        "seed": 17,
        "task_sha256": TASK_SHA,
        "document_metadata_sha256": DOC_SHA,
        "selector_sha256": hashes["selector"],
        "plan_sha256": hashes["plan"],
        "registry_sha256": hashes["registry"],
        "registry_snapshot": registry,
        "known_exposed_company_map": known,
        "other_reserved_companies": other_reserved_companies,
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
    with (HERE / "reservation.json").open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["selected"], indent=2))
