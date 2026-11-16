"""Acquire a frozen six-document SEC cohort without reading financial answers."""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from eval.scripts.table_assessment_run import runtime_digest

MAX_BYTES = 10 * 1024 * 1024
USER_AGENT = "ProvenanceXL-research/1 (https://github.com/ktpei/prov; noncommercial assessment)"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class FilingIdentity(HTMLParser):
    """Collect only the three declared DEI identity fields; never financial facts."""

    fields = {"dei:documenttype", "dei:documentperiodenddate", "dei:entitycentralindexkey"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {field: set() for field in self.fields}
        self.active = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        name = dict(attrs).get("name", "").lower()
        if tag == "ix:nonnumeric" and name in self.fields:
            if self.active is not None:
                raise ValueError("Nested identity facts are ambiguous")
            self.active = name
            self.parts = []

    def handle_data(self, data):
        if self.active is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "ix:nonnumeric" and self.active is not None:
            self.values[self.active].add(" ".join("".join(self.parts).split()))
            self.active = None
            self.parts = []


def identity(raw, document):
    parser = FilingIdentity()
    parser.feed(raw.decode("utf-8", errors="strict"))
    parser.close()
    values = parser.values
    periods = set()
    for value in values["dei:documentperiodenddate"]:
        normalized = value
        for pattern in ("%B %d, %Y", "%B %d %Y"):
            try:
                normalized = datetime.strptime(value, pattern).date().isoformat()
                break
            except ValueError:
                pass
        periods.add(normalized)
    if (
        parser.active is not None
        or values["dei:documenttype"] != {document["form"]}
        or periods != {document["period_end"]}
        or str(int(document["cik"]))
        not in {
            str(int(value))
            for value in values["dei:entitycentralindexkey"]
            if value.isascii() and value.isdigit()
        }
    ):
        raise ValueError(
            "Response does not establish the selected filing type, period and registrant CIK"
        )
    return {key: sorted(value) for key, value in values.items()}


def now():
    return datetime.now(timezone.utc).isoformat()


def persist(report, output):
    temporary = output / ".acquisition.json.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(output / "acquisition.json")


def acquire(selection_path, expected_sha256, output):
    raw_selection = Path(selection_path).read_bytes()
    if hashlib.sha256(raw_selection).hexdigest() != expected_sha256:
        raise ValueError("Frozen selection hash mismatch")
    selection = json.loads(raw_selection)
    documents = selection["documents"]
    if len(documents) != 6 or len({d["source_id"] for d in documents}) != 6:
        raise ValueError("Exactly six unique selected sources required")
    issuers = {d["issuer_id"] for d in documents}
    if len(issuers) != 3 or any(
        sum(d["issuer_id"] == issuer for d in documents) != 2 for issuer in issuers
    ):
        raise ValueError("Exactly three issuers with two sources each required")
    for document in documents:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", document["source_id"]):
            raise ValueError("Unsafe source ID")
        cik = str(int(document["cik"]))
        accession = document["accession"].replace("-", "")
        if not re.fullmatch(
            rf"https://www\.sec\.gov/Archives/edgar/data/{cik}/{accession}/[a-zA-Z0-9_-]+\.htm",
            document["primary_url"],
        ):
            raise ValueError("Primary URL does not match selected SEC accession")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "version": "native-html-acquisition-v1",
        "selection_sha256": expected_sha256,
        "python": sys.version,
        "runtime_sha256": runtime_digest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "user_agent": USER_AGENT,
        "max_response_bytes": MAX_BYTES,
        "request_policy": "Sequential; one second between requests; 20-second socket-operation timeout; no redirects or retries; identity encoding",
        "document_denominator": 6,
        "documents": [
            {"source_id": d["source_id"], "url": d["primary_url"], "status": "pending"}
            for d in documents
        ],
    }
    persist(report, output)
    opener = urllib.request.build_opener(NoRedirect)
    for number, (document, entry) in enumerate(zip(documents, report["documents"], strict=True)):
        if number:
            time.sleep(1)
        entry.update(status="request_started", requested_at=now())
        persist(report, output)
        body = bytearray()
        try:
            request = urllib.request.Request(
                document["primary_url"],
                headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
            )
            with opener.open(request, timeout=20) as response:
                entry.update(
                    http_status=response.status,
                    final_url=response.geturl(),
                    content_type=response.headers.get_content_type(),
                    declared_content_length=response.headers.get("Content-Length"),
                    content_encoding=response.headers.get("Content-Encoding", "identity"),
                )
                if (
                    response.status != 200
                    or response.geturl() != document["primary_url"]
                    or entry["content_type"] != "text/html"
                    or entry["content_encoding"].lower() != "identity"
                ):
                    raise ValueError("Unexpected HTTP status, URL, content type or encoding")
                while len(body) <= MAX_BYTES:
                    chunk = response.read(min(64 * 1024, MAX_BYTES + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                entry.update(
                    observed_at=now(),
                    response_bytes=len(body),
                    response_sha256=hashlib.sha256(body).hexdigest(),
                )
                if len(body) > MAX_BYTES:
                    raise ValueError("Response exceeds byte limit")
                declared_length = entry["declared_content_length"]
                if declared_length is not None and int(declared_length) != len(body):
                    raise ValueError("Declared response length differs from received bytes")
            entry["identity_fields"] = identity(bytes(body), document)
            filename = document["source_id"] + ".html"
            (output / filename).write_bytes(body)
            entry.update(
                status="identity_verified",
                original_file=filename,
                index_size_matches=len(body) == document["index_reported_bytes"],
            )
            # Size differences are explicit diagnostics, not automatic substitution/rejection.
        except BaseException as exc:
            entry.update(
                status="failed" if isinstance(exc, Exception) else "interrupted",
                error=f"{type(exc).__name__}: {exc}"[:1000],
                finished_at=now(),
            )
            if isinstance(exc, urllib.error.HTTPError):
                entry["http_status"] = exc.code
            if body:
                filename = document["source_id"] + ".partial"
                (output / filename).write_bytes(body)
                entry.update(
                    partial_file=filename,
                    partial_bytes=len(body),
                    partial_sha256=hashlib.sha256(body).hexdigest(),
                )
            persist(report, output)
            if not isinstance(exc, Exception):
                raise
        else:
            entry["finished_at"] = now()
            persist(report, output)
    report["completed_at"] = now()
    report["identity_verified_count"] = sum(
        d["status"] == "identity_verified" for d in report["documents"]
    )
    persist(report, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = acquire(args.selection, args.sha256, args.output)
    print(
        json.dumps(
            {
                "documents": report["document_denominator"],
                "identity_verified": report["identity_verified_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
