"""Controller-owned fact delivery; neither semantic admission nor model visibility."""

import json

from provenance.source_availability import availability
from provenance.xbrl_reader import MAX_CHUNK_CHARACTERS, FactReader, canonical, sha

POLICY = "fact-read-authorization-v1"
MAX_PAYLOAD_CHARACTERS = 256_000
READER = "exact-xbrl-fact-reader-v1"


def digest(value):
    return sha(canonical(value).encode())


def copied(value):
    return json.loads(canonical(value))


def require(condition, message):
    if not condition:
        raise ValueError(message)


class FactReadSession:
    """Trusted controller supplies authorization and artifacts, never model arguments.

    Snapshots are backend audit records, not bounded model-facing tool results.
    Persist their digest independently (for example in a trusted checkpoint).
    """

    def __init__(self, export_raw, source_raw, original_raw, *, authorization, run_id):
        require(isinstance(run_id, str) and bool(run_id.strip()), "Invalid run ID")
        auth = copied(authorization)
        require(
            isinstance(auth, dict)
            and set(auth)
            == {
                "source_id",
                "original_sha256",
                "export_sha256",
                "source_sha256",
                "reader",
                "as_of",
            },
            "Invalid source authorization",
        )
        require(auth["reader"] == READER, "Unauthorized reader")
        require(
            isinstance(auth["source_id"], str) and bool(auth["source_id"].strip()),
            "Invalid authorized source",
        )
        require(
            auth["original_sha256"] == sha(original_raw)
            and auth["export_sha256"] == sha(export_raw)
            and auth["source_sha256"] == sha(source_raw),
            "Unauthorized artifact identity",
        )
        source = json.loads(source_raw)
        require(source["id"] == auth["source_id"], "Unauthorized source")
        availability(source, auth["as_of"])  # Validate the fixed controller policy.
        self._reader = FactReader(
            export_raw,
            source_raw,
            original_raw,
            export_sha256=auth["export_sha256"],
            source_sha256=auth["source_sha256"],
        )
        self._run_id, self._authorization = run_id, auth
        self._records, self._deliveries, self._pending = [], [], {}

    def read(self, occurrence_id, *, start=None, length=MAX_CHUNK_CHARACTERS):
        require(isinstance(occurrence_id, str) and bool(occurrence_id), "Invalid occurrence ID")
        require(start is None or (type(start) is int and start >= 0), "Invalid chunk start")
        require(type(length) is int and 1 <= length <= MAX_CHUNK_CHARACTERS, "Invalid chunk length")
        request = {"occurrence_id": occurrence_id, "start": start, "length": length}
        response = copied(self._reader.read(**request, as_of=self._authorization["as_of"]))
        auth = self._authorization
        require(
            response["reader_version"] == auth["reader"]
            and response["source"]["id"] == auth["source_id"]
            and response["original_sha256"] == auth["original_sha256"]
            and response["export_sha256"] == auth["export_sha256"]
            and response["source_metadata_sha256"] == auth["source_sha256"],
            "Reader response identity mismatch",
        )
        record = {
            "run_id": self._run_id,
            "policy": POLICY,
            "sequence": len(self._records),
            "authorization_sha256": digest(auth),
            "request": request,
            "response": response,
        }
        record["id"] = digest(record)
        pending = copied(self._pending)
        delivery = None
        if response["status"] != "availability_blocked":
            require(response["availability"]["allowed"] is True, "Unavailable payload")
            require(response["occurrence_id"] == occurrence_id, "Occurrence identity mismatch")
            size = response["payload_characters"]
            require(type(size) is int and 0 < size <= MAX_PAYLOAD_CHARACTERS, "Payload size limit")
            reserved = sum(
                item["identity"]["payload_characters"]
                for key, item in pending.items()
                if key != occurrence_id
            )
            require(reserved + size <= MAX_PAYLOAD_CHARACTERS, "Aggregate reconstruction limit")
            variable = {
                "status",
                "payload",
                "chunk",
                "chunk_sha256",
                "start",
                "end",
                "next_start",
                "complete_value_delivered",
                "max_chunk_characters",
            }
            identity = {k: v for k, v in response.items() if k not in variable}
            state = pending.get(occurrence_id)
            if state:
                require(state["identity"] == identity, "Chunk envelope changed")
            else:
                state = {"identity": identity, "text": "", "receipts": []}
            status = response["status"]
            text = None
            if status == "complete":
                require(start is None, "Unexpected full response")
                text = canonical(response["payload"])
            elif status == "deferred":
                require(start is None and response["next_start"] == 0, "Invalid deferred response")
            elif status == "chunk":
                chunk = response["chunk"]
                require(
                    type(start) is int
                    and start == len(state["text"])
                    and type(response["start"]) is int
                    and response["start"] == start
                    and isinstance(chunk, str)
                    and bool(chunk)
                    and type(response["end"]) is int
                    and response["end"] == start + len(chunk)
                    and response["end"] <= size
                    and type(length) is int
                    and 0 < len(chunk) <= length
                    and sha(chunk.encode()) == response["chunk_sha256"],
                    "Invalid or noncontiguous chunk",
                )
                require(
                    response["next_start"] == (response["end"] if response["end"] < size else None),
                    "Invalid continuation",
                )
                state["text"] += chunk
                if response["end"] == size:
                    text = state["text"]
            else:
                raise ValueError("Unsupported read status")
            state["receipts"].append(record["id"])
            if text is not None:
                require(
                    len(text) == size and sha(text.encode()) == response["payload_sha256"],
                    "Reconstructed payload identity mismatch",
                )
                payload = json.loads(text)
                require(
                    isinstance(payload, dict) and canonical(payload) == text, "Noncanonical payload"
                )
                require(payload["fact"]["id"] == occurrence_id, "Payload occurrence mismatch")
                delivery = {
                    "run_id": self._run_id,
                    "policy": POLICY,
                    "authorization_sha256": digest(auth),
                    "identity": identity,
                    "read_receipts": state["receipts"],
                    "payload": payload,
                    "disposition": "delivered_not_semantically_admitted",
                }
                delivery["id"] = digest(delivery)
                pending.pop(occurrence_id, None)
            else:
                pending[occurrence_id] = state
        else:
            require(response["availability"]["allowed"] is False, "Invalid availability block")
        # All validation and reconstruction precedes session mutation.
        self._records.append(record)
        self._pending = pending
        if delivery:
            self._deliveries.append(delivery)
        return copied(record)

    def snapshot(self):
        return copied(
            {
                "policy": POLICY,
                "run_id": self._run_id,
                "authorization": self._authorization,
                "reads": self._records,
                "deliveries": self._deliveries,
                "pending": self._pending,
            }
        )


def replay_fact_reads(
    export_raw,
    source_raw,
    original_raw,
    *,
    authorization,
    run_id,
    snapshot,
    expected_snapshot_sha256,
):
    """Expected digest and authorization come from trusted storage, not this snapshot."""
    require(digest(snapshot) == expected_snapshot_sha256, "Snapshot inventory mismatch")
    session = FactReadSession(
        export_raw, source_raw, original_raw, authorization=authorization, run_id=run_id
    )
    require(
        snapshot["run_id"] == run_id
        and snapshot["authorization"] == authorization
        and snapshot["policy"] == POLICY,
        "Session identity mismatch",
    )
    for record in snapshot["reads"]:
        require(session.read(**record["request"]) == record, "Read replay mismatch")
    require(session.snapshot() == snapshot, "Delivery inventory replay mismatch")
    return session.snapshot()
