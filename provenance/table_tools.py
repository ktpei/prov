"""Opt-in, read-only search and windowed reads over native HTML tables.

``TableSources`` is deliberately separate from the default research graph.  It
validates a frozen corpus with :class:`provenance.sources.Sources`, verifies and
extracts only original ``.html``/``.htm`` files, and keeps the resulting v2
sidecars in memory.  The constructor is the snapshot boundary: subsequent calls
use those verified in-memory records and never read or write corpus files.

``call`` returns JSON-compatible objects.  Tool validation and execution errors
are consistently returned as ``{"error": "..."}``; constructor integrity errors
raise ``ValueError``.  Successful responses use compact UTF-8 JSON serialization
of at most 12,000 characters.  Oversize responses fail atomically rather than
being clipped or partially returned.
"""

import copy
import hashlib
import json
import math
import re
from pathlib import Path

from provenance.sources import Sources, _bm25
from provenance.table_structure import extract_html_tables

MAX_QUERY_CHARACTERS = 500
MAX_ROW_INDICES = 8
MAX_RESULTS = 5
MAX_RESPONSE_CHARACTERS = 12_000
SIDECAR_VERSION = "native-html-tables-v2"
READ_POLICY = "table-window-v1"

_TOKEN = re.compile(r"\w+")


def _tokens(text):
    return _TOKEN.findall(text.lower())


def _visible_text(row):
    return " ".join(
        cell["text"]
        for cell in row["cells"]
        if cell["text"] and cell["visibility"] != "explicitly_hidden"
    )


def _literal_snippet(text, terms, limit=240):
    """Return an unmodified bounded excerpt around the first literal term."""
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not positions:
        return ""
    start = max(0, min(positions) - 80)
    end = min(len(text), start + limit)
    start = max(0, end - limit)
    return text[start:end]


def _encoded_size(value):
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


class TableSources:
    """Immutable local table snapshot for an already-ingested ``Sources`` corpus.

    Search is source-scoped lexical BM25 over visible nonempty row text.  A
    caption and the first five physical rows form a small fixed table-title
    context; they can raise a matching table's score but cannot create semantic
    matches or cause unrelated rows to be returned.  Search does not establish
    read or citation context.

    Reads apply ``table-window-v1``: include the first five physical rows plus
    every requested row and its immediate predecessor, then deduplicate and sort.
    Empty and explicitly hidden cells are omitted.  Empty text is distinct from
    the string ``"0"``.  External CSS visibility remains unresolved, and raw HTML
    header attributes are preserved without resolving header associations.  The
    first-five/predecessor heuristic does not claim to find every header.
    """

    def __init__(self, directory, *, search_version="source-scoped-visible-row-bm25-v2"):
        if search_version not in {
            "source-scoped-visible-row-bm25-v1",
            "source-scoped-visible-row-bm25-v2",
            "source-scoped-visible-row-bm25-v3",
        }:
            raise ValueError("Unknown table search version")
        self.search_version = search_version
        self.directory = Path(directory)
        manifest_path = self.directory / "sources.json"
        manifest_before = manifest_path.read_bytes()
        sources = Sources(self.directory)
        manifest_after = manifest_path.read_bytes()
        if manifest_before != manifest_after:
            raise ValueError("Corpus manifest changed during table snapshot construction")

        self.manifest_sha256 = hashlib.sha256(manifest_before).hexdigest()
        self._sources = {}
        for source_id, source in sources.documents.items():
            original_file = source.get("original_file")
            if not original_file or Path(original_file).suffix.lower() not in {".html", ".htm"}:
                continue
            original = (self.directory / original_file).resolve()
            sidecar = extract_html_tables(original)
            if sidecar["version"] != SIDECAR_VERSION:
                raise ValueError(f"Unexpected table sidecar version: {source_id}")
            if sidecar["original_sha256"] != source["original_sha256"]:
                raise ValueError(
                    f"Original changed during table snapshot construction: {source_id}"
                )
            self._sources[source_id] = {
                "original_sha256": source["original_sha256"],
                "sidecar": sidecar,
                "sidecar_sha256": hashlib.sha256(
                    json.dumps(
                        sidecar,
                        ensure_ascii=False,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest(),
                "tables": {table["id"]: table for table in sidecar["tables"]},
            }
        self._known_source_ids = frozenset(sources.documents)

    def _source(self, source_id):
        if not isinstance(source_id, str):
            raise ValueError("source_id must be a string")
        if source_id not in self._known_source_ids:
            raise ValueError(f"Unknown source_id: {source_id}")
        if source_id not in self._sources:
            raise ValueError(f"source_id is not a verified native HTML source: {source_id}")
        return self._sources[source_id]

    def _identity(self, source_id, source):
        return {
            "source_id": source_id,
            "original_sha256": source["original_sha256"],
            "sidecar_version": source["sidecar"]["version"],
            "sidecar_sha256": source["sidecar_sha256"],
            "corpus_manifest_sha256": self.manifest_sha256,
        }

    @staticmethod
    def _table(source, table_id):
        if not isinstance(table_id, str):
            raise ValueError("table_id must be a string")
        try:
            return source["tables"][table_id]
        except KeyError as exc:
            raise ValueError(f"Unknown table_id: {table_id}") from exc

    def search_tables(self, source_id, query):
        source = self._source(source_id)
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARACTERS:
            raise ValueError("query must contain 1–500 characters")
        query_terms = sorted(set(_tokens(query)))
        if not query_terms:
            raise ValueError("query must contain at least one lexical term")

        indexed = []
        for ordinal, table in enumerate(source["sidecar"]["tables"]):
            rows = []
            for row in table["rows"]:
                text = _visible_text(row)
                rows.append((row["index"], text, _tokens(text)))
            caption = table.get("caption", {}).get("text", "")
            title_text = " ".join([caption, *(text for _, text, _ in rows[:5])]).strip()
            indexed.append((ordinal, table, rows, title_text, _tokens(title_text)))

        row_documents = [tokens for _, _, rows, _, _ in indexed for _, _, tokens in rows]
        title_documents = [tokens for _, _, _, _, tokens in indexed]
        documents = row_documents + title_documents
        average_length = sum(map(len, documents)) / max(len(documents), 1)
        counts = {term: sum(term in document for document in documents) for term in query_terms}
        idf = {
            term: math.log(1 + (len(documents) - count + 0.5) / (count + 0.5))
            for term, count in counts.items()
        }

        ranked = []
        for ordinal, table, rows, title_text, title_tokens in indexed:
            row_matches = []
            for row_index, text, tokens in rows:
                if not set(query_terms).intersection(tokens):
                    continue
                row_matches.append((_bm25(tokens, idf, average_length), row_index, text))
            title_match = bool(set(query_terms).intersection(title_tokens))
            if not row_matches and not title_match:
                continue
            row_matches.sort(key=lambda item: (-item[0], item[1]))
            title_score = _bm25(title_tokens, idf, average_length) if title_match else 0.0
            score = sum(item[0] for item in row_matches[:3]) + 0.25 * title_score
            ranked.append((score, ordinal, table, row_matches, title_text))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        results = []
        for score, _, table, row_matches, title_text in ranked[:MAX_RESULTS]:
            # The read policy already includes these rows; reserve candidates for new context.
            read_candidates = (
                [match for match in row_matches if match[1] >= 5]
                if self.search_version != "source-scoped-visible-row-bm25-v1"
                else row_matches
            )
            if self.search_version == "source-scoped-visible-row-bm25-v3":
                # Softly discount repeated prefix evidence, without deleting metric terms.
                prefix_terms = set(_tokens(title_text))
                candidate_idf = {
                    term: weight * (0.25 if term in prefix_terms else 1.0)
                    for term, weight in idf.items()
                }
                read_candidates = sorted(
                    read_candidates,
                    key=lambda item: (
                        -_bm25(_tokens(item[2]), candidate_idf, average_length),
                        item[1],
                    ),
                )
            snippets = [
                {"row_index": row_index, "text": _literal_snippet(text, query_terms)}
                for _, row_index, text in read_candidates[:MAX_ROW_INDICES]
            ]
            if not snippets:
                snippets = [{"title_context": _literal_snippet(title_text, query_terms)}]
            results.append(
                {
                    "source_id": source_id,
                    "table_id": table["id"],
                    "score": round(score, 4),
                    "matched_row_indices": [
                        row_index for _, row_index, _ in read_candidates[:MAX_ROW_INDICES]
                    ],
                    "literal_match_snippets": snippets,
                }
            )
        response = {
            **self._identity(source_id, source),
            "search_policy": self.search_version,
            "results": results,
            "diagnostics": {
                "semantic_matching": False,
                "search_establishes_read_context": False,
                "title_context": "caption plus first five physical rows; fixed score weight 0.25",
                "external_css_visibility": "unresolved",
            },
        }
        if self.search_version == "source-scoped-visible-row-bm25-v2":
            response["diagnostics"]["read_candidate_policy"] = (
                "Exclude first five prefix rows already included by reads; table scores unchanged."
            )
        if self.search_version == "source-scoped-visible-row-bm25-v3":
            response["diagnostics"]["read_candidate_policy"] = (
                "Exclude first five prefix rows; rerank body rows with BM25 query-term "
                "weights 0.25 for terms in caption/prefix, 1.0 otherwise; table scores unchanged."
            )
        self._ensure_size(response)
        return copy.deepcopy(response)

    def read_table(self, source_id, table_id, row_indices):
        source = self._source(source_id)
        table = self._table(source, table_id)
        if not isinstance(row_indices, list):
            raise ValueError("row_indices must be a list of integers")
        if len(row_indices) > MAX_ROW_INDICES:
            raise ValueError(f"row_indices may contain at most {MAX_ROW_INDICES} rows")
        if any(type(index) is not int for index in row_indices):
            raise ValueError("row_indices must contain integers, not booleans or other types")
        if len(set(row_indices)) != len(row_indices):
            raise ValueError("row_indices must not contain duplicates")
        row_count = len(table["rows"])
        if any(index < 0 or index >= row_count for index in row_indices):
            raise ValueError("row_indices contain a negative or out-of-bounds row")

        included = set(range(min(5, row_count)))
        for index in row_indices:
            included.add(index)
            if index:
                included.add(index - 1)
        included_indices = sorted(included)
        cells = [
            cell
            for index in included_indices
            for cell in table["rows"][index]["cells"]
            if cell["text"] and cell["visibility"] != "explicitly_hidden"
        ]
        response = {
            **self._identity(source_id, source),
            "table_id": table_id,
            "read_policy": READ_POLICY,
            "requested_row_indices": list(row_indices),
            "included_row_indices": included_indices,
            "cells": cells,
            "diagnostics": {
                "empty_cells_omitted": True,
                "explicitly_hidden_cells_omitted": True,
                "empty_is_distinct_from_zero": True,
                "external_css_visibility": "unresolved",
                "raw_header_associations": "not_resolved",
                "limitations": [
                    "The first-five/predecessor window is a context heuristic and does not establish that all headers are included.",
                    "Cell text is v2 whitespace-normalized extracted content, not an original HTML byte quote.",
                    "No value, sign, unit, period, header, metric identity, or financial meaning is inferred.",
                ],
            },
        }
        if "caption" in table:
            response["caption"] = table["caption"]
        self._ensure_size(response)
        return copy.deepcopy(response)

    @staticmethod
    def _ensure_size(response):
        if _encoded_size(response) > MAX_RESPONSE_CHARACTERS:
            raise ValueError(
                f"Serialized response exceeds {MAX_RESPONSE_CHARACTERS} characters; request rejected"
            )

    def call(self, name, args, timeout):
        """Dispatch one local tool call, returning a result object or tool error."""
        try:
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout)
                or timeout <= 0
            ):
                raise ValueError("timeout must be a positive number")
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            if name == "search_tables" and set(args) == {"source_id", "query"}:
                return self.search_tables(args["source_id"], args["query"])
            if name == "read_table" and set(args) == {"source_id", "table_id", "row_indices"}:
                return self.read_table(args["source_id"], args["table_id"], args["row_indices"])
            raise ValueError("Unknown tool or invalid argument fields")
        except ValueError as exc:
            error = {"error": str(exc)}
            if _encoded_size(error) > MAX_RESPONSE_CHARACTERS:
                return {"error": "Tool error exceeds response size limit"}
            return error
