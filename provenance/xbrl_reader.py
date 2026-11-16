"""Opt-in exact-ID reads of trusted experimental XBRL exports; no discovery or grading."""

import hashlib
import json

from provenance.source_availability import availability
from provenance.xbrl_occurrences import _source_nodes

MAX_RESPONSE_CHARACTERS = 12_000
MAX_CHUNK_CHARACTERS = 4_000


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class FactReader:
    """Snapshot authenticated inputs; expected hashes must come from a trusted receipt.

    Hashes authenticate an already validated producer artifact, not its financial
    correctness. This reader does not replace taxonomy/schema validation. Source
    metadata is a single source record, not a corpus manifest. Every response is
    bounded; deferred JSON payloads require reconstruction before complete credit.
    """

    def __init__(self, export_raw, source_raw, original_raw, *, export_sha256, source_sha256):
        if sha(export_raw) != export_sha256 or sha(source_raw) != source_sha256:
            raise ValueError("Authenticated input hash mismatch")
        export = json.loads(export_raw)
        source = json.loads(source_raw)
        if export["version"] != "experimental-typed-xbrl-facts-v1":
            raise ValueError("Unsupported fact export")
        if (
            sha(original_raw) != export["original_sha256"]
            or source["original_sha256"] != export["original_sha256"]
        ):
            raise ValueError("Original source hash mismatch")
        if source.get("reference_sec_url") != export["canonical_url"]:
            raise ValueError("Canonical filing identity mismatch")
        availability(source, None)
        nodes = {}
        for node in _source_nodes(original_raw):
            identifier = node["attributes"].get("id")
            if identifier:
                if identifier in nodes:
                    raise ValueError("Duplicate original source ID")
                nodes[identifier] = node
        self._source = source
        self._identity = {
            "reader_version": "exact-xbrl-fact-reader-v1",
            "delivery_scope": "Selected occurrence, its context/unit and source fragments; duplicate peers, ancestors, descendants, table headers and taxonomy defaults are not implicitly delivered.",
            "export_sha256": export_sha256,
            "source_metadata_sha256": source_sha256,
            "original_sha256": export["original_sha256"],
            "canonical_url": export["canonical_url"],
            "source": {
                key: source.get(key)
                for key in (
                    "id",
                    "title",
                    "url",
                    "reference_sec_url",
                    "artifact_class",
                    "published",
                    "retrieved",
                    "availability",
                )
            },
        }
        continuations = {fragment["id"]: fragment for fragment in export["continuations"]}
        self._payloads = {}
        for fact in export["facts"]:
            identifier = fact["id"]
            if identifier in self._payloads:
                raise ValueError("Duplicate occurrence ID")
            context_id, unit_id = fact["context_id"], fact["unit_id"]
            context = export["contexts"][context_id]
            unit = export["units"][unit_id] if unit_id is not None else None
            fragments = [
                continuations[item["id"]]
                for item in fact["source_occurrence"]["continuation_fragments"]
            ]
            groups = [
                group for group in export["duplicate_groups"] if identifier in group["occurrences"]
            ]
            if (
                any(group["inconsistent"] for group in groups)
                and fact["disposition"] != "quarantined_inconsistent_duplicate"
            ):
                raise ValueError("Inconsistent occurrence is not quarantined")
            original_fragments = []
            for source_id, role in [
                (identifier, "fact"),
                (context_id, "context"),
                *([(unit_id, "unit")] if unit_id else []),
                *[(fragment["id"], "continuation") for fragment in fragments],
            ]:
                node = nodes[source_id]
                raw = original_raw[node["start"] : node["end"]]
                original_fragments.append(
                    {
                        "id": source_id,
                        "role": role,
                        "byte_start": node["start"],
                        "byte_end": node["end"],
                        "sha256": sha(raw),
                        "text": raw.decode("utf-8"),
                    }
                )
            self._payloads[identifier] = canonical(
                {
                    "fact": fact,
                    "context": context,
                    "unit": unit,
                    "duplicate_groups": groups,
                    "continuations": fragments,
                    "original_fragments": original_fragments,
                    "default_scope_note": export["default_scope_note"],
                    "normalization_note": export["normalization_note"],
                    "lexical_note": export["lexical_note"],
                    "limitations": [
                        "Exact-ID delivery is not discovery, rendered visibility or financial sufficiency.",
                        "Taxonomy defaults remain in the authenticated export; no effective-default inference is made.",
                        "Source fragments preserve original bytes when UTF-8 encoded, not rendered text.",
                    ],
                }
            )

    @staticmethod
    def _bounded(response):
        serialized = canonical(response)
        if len(serialized) > MAX_RESPONSE_CHARACTERS:
            raise ValueError("Serialized response exceeds 12000 characters; request rejected")
        return json.loads(serialized)

    def read(self, occurrence_id, *, as_of=None, start=None, length=MAX_CHUNK_CHARACTERS):
        decision = availability(self._source, as_of)
        if not decision["allowed"]:
            return self._bounded(
                {**self._identity, "status": "availability_blocked", "availability": decision}
            )
        if not isinstance(occurrence_id, str) or occurrence_id not in self._payloads:
            raise ValueError("Unknown occurrence ID")
        payload = self._payloads[occurrence_id]
        base = {
            **self._identity,
            "availability": decision,
            "occurrence_id": occurrence_id,
            "payload_sha256": sha(payload.encode()),
            "payload_characters": len(payload),
            "payload_encoding": "canonical JSON, UTF-8 hash, Unicode character offsets",
        }
        if start is None:
            response = {**base, "status": "complete", "payload": json.loads(payload)}
            if len(canonical(response)) <= MAX_RESPONSE_CHARACTERS:
                return self._bounded(response)
            return self._bounded(
                {
                    **base,
                    "status": "deferred",
                    "complete_value_delivered": False,
                    "next_start": 0,
                    "max_chunk_characters": MAX_CHUNK_CHARACTERS,
                }
            )
        if type(start) is not int or not 0 <= start < len(payload):
            raise ValueError("Chunk start must be an in-range integer")
        if type(length) is not int or not 1 <= length <= MAX_CHUNK_CHARACTERS:
            raise ValueError("Chunk length must be an integer from 1 to 4000")
        end = min(start + length, len(payload))
        chunk = payload[start:end]
        return self._bounded(
            {
                **base,
                "status": "chunk",
                "start": start,
                "end": end,
                "next_start": end if end < len(payload) else None,
                "chunk": chunk,
                "chunk_sha256": sha(chunk.encode()),
                "complete_value_delivered": False,
            }
        )
