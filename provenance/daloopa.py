"""Pinned Daloopa preparation: retain the full inventory, expose only safe task inputs."""

import argparse
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from provenance.benchmarks import canonical_hash, decimal_answer

ROOT = Path(__file__).resolve().parent.parent
VERSION = "daloopa-retrieval-v1"
QUICK_COUNT = 25
SEED = 20261120
# Issuer identity only; never use reserved questions or source contents to identify these.
PROTECTED = {
    "LMT": "Lockheed Martin",
    "AXP": "American Express",
    "AMZN": "Amazon",
    "MSFT": "Microsoft",
    "AMD": "AMD",
    "SQ": "Block",
    "XYZ": "Block",
    "CASY": "Casey's General Stores",
    "ODFL": "Old Dominion Freight Line",
    "AEE": "Ameren",
}
CONTRACT = (
    "Retrieve the explicitly reported figure from original company documents. Do not derive "
    "a substitute figure. Return the normal cited JSON answer with exactly one numeric claim "
    "whose key is requested_answer, in the unit/currency requested by the question. Include "
    "the reporting period and source citations. Do not add unrelated claims. If evidence is "
    "unavailable, return answerable=false and claims=[]."
)
NUMBER = r"(?<![\w.])[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w|\.\d)"
CURRENCIES = "AED AUD BRL CAD CHF CLP CNY EUR GBP INR JPY KRW MXN NIS NOK NZD PEN PHP PLN SAR SEK SGD TWD USD ZAR".split()


def unit(text, *, fallback=None, strict=False):
    """Conservative dimension/scale normalization, never currency conversion or guessing."""
    text = text.lower().replace("_", " ")
    if strict:
        text = text.replace("/", " per ")
    text = re.sub(r"per (?:diluted |basic |ordinary |common )?shares?", "per share", text)
    aliases = {
        "brazilian reais": "brl",
        "japanese yen": "jpy",
        "new taiwan dollars": "twd",
        "chilean pesos": "clp",
        "rmb": "cny",
        "rupees": "inr",
        "yen": "jpy",
        "u.s. dollars": "usd",
        "us dollars": "usd",
        "us$": "usd",
        "r$": "brl",
    }
    for old, new in aliases.items():
        text = text.replace(old, new)
    if strict:
        allowed = set(
            "thousand thousands million millions billion billions trillion trillions crore crores lakh lakhs cent cents percent percentage basis point points bps per share shares barrel barrels pound pounds ton tons tonne tonnes gallon gallons ounce ounces room night nights store stores unit units mw mtpa square foot feet".split()
        )
        allowed.update(code.lower() for code in CURRENCIES)
        tokens = set(re.findall(r"[a-z]+", text))
        if (not tokens and text.strip() != "%") or tokens - allowed:
            raise ValueError("Unsupported unit tokens")
    codes = [code for code in CURRENCIES if re.search(r"\b" + code.lower() + r"\b", text)]
    if len(codes) > 1:
        raise ValueError("Multiple currencies require reference review")
    if "percentage point" in text:
        return "percentage_point", Decimal(1)
    if "basis point" in text or text.strip() == "bps":
        return "percentage_point", Decimal("0.01")
    if re.search(r"\bpercent(?:age)?\b|%", text):
        return "percent", Decimal(1)
    dimension = codes[0] if codes else None
    if dimension is None:
        for name, pattern in [
            ("gallon", r"\bgallons?\b"),
            ("tonne", r"\bmtpa\b|\btonnes?\b"),
            ("barrel", r"\bbarrels?\b"),
            ("ounce", r"\bounces?\b"),
            ("room_night", r"\broom nights?\b"),
            ("store", r"\bstores?\b"),
            ("MW", r"\bmw\b|\bmegawatts?\b"),
            ("unit", r"\bunits?\b"),
        ]:
            if re.search(pattern, text):
                dimension = name
                break
    default_scale = Decimal(1)
    if dimension is None:
        if fallback is None:
            raise ValueError("Unrecognized unit")
        dimension, default_scale = fallback
    scales = [
        (r"\btrillions?\b", "1000000000000"),
        (r"\bbillions?\b", "1000000000"),
        (r"\bmillions?\b", "1000000"),
        (r"\bthousands?\b", "1000"),
        (r"\bcrores?\b", "10000000"),
        (r"\blakhs?\b", "100000"),
        (r"\bcents?\b", "0.01"),
    ]
    found = [Decimal(value) for pattern, value in scales if re.search(pattern, text)]
    if len(found) > 1:
        raise ValueError("Multiple scales require reference review")
    denominator = re.search(r"\bper (share|barrel|pound|tonne|ton|gallon|square foot)\b", text)
    if " per " in text and not denominator:
        raise ValueError("Unrecognized unit denominator")
    if denominator:
        dimension += "/" + denominator[1]
    return dimension, found[0] if found else default_scale


def protected(ticker):
    # Both US-style 'AMD:US' and exchange-prefixed 'NASDAQ:AMD' aliases.
    return any(part.upper() in PROTECTED for part in re.split(r"[:.]", ticker))


def protections():
    paths = [
        "eval/assessments/financebench-page-validation-v1/reservation.json",
        "eval/assessments/financebench-page-validation-v1/exposure-audit.json",
        "eval/development-exposures.json",
        "data/corpus/sources.json",
        "data/cloudflare-2024-q3/sources.json",
    ]
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def reference(rows):
    keys = ("question", "gt_num", "gt_src", "gt_answer", "currency")
    if len({tuple(row[key] for key in keys) for row in rows}) != 1:
        return {"status": "reference_review_required", "reason": "Conflicting upstream references"}
    row = rows[0]
    # Do not trust gt_num: the release mixes base units, display units and ratios.
    # Strip Markdown destinations before parsing, and remove question period literals.
    text = re.sub(r"\]\([^)]*\)", "]", row["gt_answer"])
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    # Preserve signs outside Markdown links/currency symbols, e.g. -[$365 million].
    text = re.sub(r"([+-])\s*[$€£¥₹]\s*(?=\d)", r"\1", text)
    # Strip only explicit period expressions; a number appearing in the question
    # may also be the answer (e.g. 10 stores). Different stated years need review.
    year_pattern = (
        r"\b(?:fy\s*|(?:fiscal|full)[ -]?year\s*|year\s+|(?:in|for|of)\s+|"
        r"q[1-4]\s+(?:of\s+)?(?:fiscal(?:\s+year)?\s+)?|"
        r"(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter\s+(?:of\s+)?)"
        r"((?:19|20)\d{2})\b"
    )
    question_years = set(re.findall(year_pattern, row["question"], re.I))
    answer_years = set(re.findall(year_pattern, text, re.I))
    if question_years and answer_years - question_years:
        return {"status": "reference_review_required", "reason": "Reference period needs review"}
    numeric_text = re.sub(year_pattern, " ", text, flags=re.I)
    numeric_text = re.sub(r"\bQ[1-4]\b", " ", numeric_text, flags=re.I)
    numbers = re.findall(NUMBER, numeric_text)
    if len(numbers) != 1:
        return {
            "status": "reference_review_required",
            "reason": "Non-scalar or ambiguous reference",
        }
    try:
        fallback = unit(row["currency"]) if row["currency"] else None
        requested = unit(row["question"], fallback=fallback)
        actual = unit(text, fallback=requested)
        if actual[0] != requested[0]:
            raise ValueError("Question/reference unit dimensions differ")
        value = decimal_answer(numbers[0].replace(",", ""))
        # Parenthesized financial negatives are not a punctuation-only transformation.
        if re.search(r"\(\s*" + re.escape(numbers[0]) + r"\s*\)", text):
            value = -abs(value)
        return {
            "status": "ready",
            "value": str(value * actual[1]),
            "dimension": actual[0],
            "answer_text": row["gt_answer"],
            "source_url": row["gt_src"],
            "upstream_gt_num": row["gt_num"],
            "verification": "publisher_reference_not_source_verified",
        }
    except ValueError as exc:
        return {"status": "reference_review_required", "reason": str(exc)}


def model_input(task):
    if task["status"] == "reserved_issuer":
        return None
    return {"id": task["id"], "question": task["question"], "output_contract": CONTRACT}


def quick_ids(tasks):
    # Fixed outcome-blind round-robin across category/difficulty, with seeded ordering.
    buckets = defaultdict(list)
    for task in tasks:
        if task["status"] == "ready":
            buckets[(task["category"], task["difficulty"])].append(task)
    for bucket in buckets.values():
        bucket.sort(key=lambda task: canonical_hash([SEED, task["id"]]))
    order = sorted(buckets, key=lambda key: canonical_hash([SEED, key]))
    selected = []
    while order and len(selected) < QUICK_COUNT:
        for key in order[:]:
            selected.append(buckets[key].pop(0)["id"])
            if not buckets[key]:
                order.remove(key)
            if len(selected) == QUICK_COUNT:
                break
    return selected


def prepare(raw, source, reference_reviews=()):
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("Input differs from pinned source hash")
    if source.get("dataset") != "daloopa" or not re.fullmatch(r"[a-f0-9]{40}", source["revision"]):
        raise ValueError("Expected immutable Daloopa source manifest")
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        if not row.get("ticker"):
            raise ValueError("Every row requires an issuer ticker")
        groups[row["ticker"]].append(row)
    if len(groups) != source["question_count"]:
        raise ValueError("Upstream question inventory changed")
    tasks = []
    for ticker, rows in sorted(groups.items()):
        identifier = "daloopa-" + hashlib.sha256(ticker.encode()).hexdigest()[:16]
        task = {"id": identifier, "ticker": ticker}
        if protected(ticker):
            # Never project protected question, reference, or source fields into the bundle.
            task.update(status="reserved_issuer", reference=None)
        else:
            if len(rows) != 6 or len({r["chatbot"] for r in rows}) != 6:
                raise ValueError("Expected six distinct historical chatbot rows per issuer")
            ref = reference(rows)
            task.update(
                status=ref["status"],
                reference=ref,
                question=rows[0]["question"],
                category=rows[0]["category"],
                difficulty=rows[0]["difficulty"],
                currency=rows[0]["currency"],
            )
        tasks.append(task)
    reviews = {row["id"]: row for row in reference_reviews}
    if len(reviews) != len(reference_reviews) or not set(reviews) <= {t["id"] for t in tasks}:
        raise ValueError("Unknown or duplicate reference review IDs")
    for task in tasks:
        if task["id"] not in reviews:
            continue
        review = reviews[task["id"]]
        if task["status"] == "reserved_issuer":
            raise ValueError("Reference review cannot unlock reserved issuers")
        if review.get("original_task_sha256") != canonical_hash(task):
            raise ValueError("Reference review does not match original task")
        for key in ("reviewer", "notes", "source_url", "locator"):
            if not isinstance(review.get(key), str) or not review[key].strip():
                raise ValueError("Reference review needs reviewer, notes, original URL and locator")
        if review.get("reviewer_kind") not in {"human", "agent"}:
            raise ValueError("Reference review must disclose reviewer kind")
        dimension, scale = unit(review["unit"], strict=True)
        value = decimal_answer(review["value"])
        task.update(
            status="ready",
            reference={
                "status": "ready",
                "value": str(value * scale),
                "dimension": dimension,
                "verification": "reviewer_attested_original_source",
                "review": review,
            },
        )
    inputs = [payload for task in tasks if (payload := model_input(task)) is not None]
    manifest = {
        "version": VERSION,
        "source": source,
        "seed": SEED,
        "full_ids": [t["id"] for t in tasks],
        "quick_ids": quick_ids(tasks),
        "tasks_sha256": canonical_hash(tasks),
        "inputs_sha256": canonical_hash(inputs),
        "protections": protections(),
        "protected_tickers": PROTECTED,
        "reference_reviews_sha256": canonical_hash(reference_reviews),
        "limitations": [
            "Public exposed benchmark; neither quick nor full is a secret holdout.",
            "All cases retained; reserved issuers are skipped and unresolved references stay unscored.",
            "Numeric matching is not metric/period correctness or citation entailment.",
            "Publisher reference parsing is provisional until original-source review.",
            "Adapted API agent evaluation, not a replication of historical web-app scores.",
        ],
    }
    return {"manifest": manifest, "tasks": tasks, "inputs": inputs}


def validate(bundle):
    manifest, tasks = bundle["manifest"], bundle["tasks"]
    if manifest["version"] != VERSION or manifest["protections"] != protections():
        raise ValueError("Unknown bundle version or changed evaluation protections; prepare again")
    ids = [task["id"] for task in tasks]
    if len(set(ids)) != len(ids) or ids != manifest["full_ids"]:
        raise ValueError("Full inventory mismatch")
    if len(ids) != manifest["source"]["question_count"]:
        raise ValueError("Question count mismatch")
    if manifest["quick_ids"] != quick_ids(tasks):
        raise ValueError("Quick selection mismatch")
    if canonical_hash(tasks) != manifest["tasks_sha256"]:
        raise ValueError("Task/reference hash mismatch")
    expected = [p for t in tasks if (p := model_input(t)) is not None]
    if bundle["inputs"] != expected or canonical_hash(expected) != manifest["inputs_sha256"]:
        raise ValueError("Safe model input mismatch")
    for task in tasks:
        if protected(task["ticker"]) and task != {
            "id": task["id"],
            "ticker": task["ticker"],
            "status": "reserved_issuer",
            "reference": None,
        }:
            raise ValueError("Protected issuer content must remain sealed")
    return bundle


def load(path):
    return validate(
        {
            key: json.loads((Path(path) / f"{key}.json").read_text())
            for key in ("manifest", "tasks", "inputs")
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-reviews", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source_manifest.read_text())
    bundle = prepare(
        args.input.read_bytes(),
        source,
        json.loads(args.reference_reviews.read_text()) if args.reference_reviews else [],
    )
    validate(bundle)
    args.output.mkdir(parents=True, exist_ok=False)
    for key, value in bundle.items():
        (args.output / f"{key}.json").write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n"
        )
    template = [
        {
            "id": task["id"],
            "original_task_sha256": canonical_hash(task),
            "ticker": task["ticker"],
            "question": task["question"],
            "value": None,
            "unit": "",
            "source_url": "",
            "locator": "",
            "reviewer": "",
            "reviewer_kind": "human",
            "notes": "",
        }
        for task in bundle["tasks"]
        if task["status"] == "reference_review_required"
    ]
    (args.output / "reference-review-template.json").write_text(
        json.dumps(template, indent=2) + "\n"
    )
    from collections import Counter

    print(
        json.dumps(
            {
                "full": len(bundle["tasks"]),
                "quick": len(bundle["manifest"]["quick_ids"]),
                "dispositions": dict(Counter(t["status"] for t in bundle["tasks"])),
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
