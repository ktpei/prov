"""Bind unresolved external-reference issues to their exact source content."""

from __future__ import annotations

import copy
import re

from provenance.benchmarks import canonical_hash

_VERSION = "finance-reference-issues-v1"
_ISSUE_FIELDS = (
    "id",
    "dataset",
    "subset",
    "source_split",
    "revision",
    "source_sha256",
    "task_id",
    "task_sha256",
    "category",
    "note",
    "review",
)
_SOURCE_FIELDS = ("dataset", "subset", "source_split", "revision", "sha256")
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _validate_source(source):
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    for field in _SOURCE_FIELDS:
        _text(source.get(field), f"source {field}")
    if not _REVISION.fullmatch(source["revision"]):
        raise ValueError("source revision must be an immutable 40- or 64-character hex commit")
    if not _SHA256.fullmatch(source["sha256"]):
        raise ValueError("source sha256 must be a 64-character hex digest")


def _validate_registry(registry):
    if not isinstance(registry, dict) or registry.get("version") != _VERSION:
        raise ValueError(f"registry version must be {_VERSION}")
    if set(registry) != {"version", "issues"}:
        raise ValueError("registry contains unsupported v1 fields")
    issues = registry.get("issues")
    if not isinstance(issues, list):
        raise ValueError("registry issues must be a list")

    ids, targets = set(), set()
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError(f"registry issue {index} must be an object")
        if set(issue) != set(_ISSUE_FIELDS):
            raise ValueError(f"registry issue {index} contains unsupported v1 fields")
        for field in _ISSUE_FIELDS:
            _text(issue.get(field), f"registry issue {index} {field}")
        if not _REVISION.fullmatch(issue["revision"]):
            raise ValueError(f"registry issue {index} revision must be immutable hex")
        for field in ("source_sha256", "task_sha256"):
            if not _SHA256.fullmatch(issue[field]):
                raise ValueError(f"registry issue {index} {field} must be a sha256 digest")
        if issue["id"] in ids:
            raise ValueError(f"duplicate reference issue ID: {issue['id']}")
        ids.add(issue["id"])
        target = tuple(issue[field] for field in ("dataset", "subset", "source_split", "task_id"))
        if target in targets:
            raise ValueError(f"duplicate reference issue target: {target!r}")
        targets.add(target)
    return issues


def _review_message(issue):
    return (
        f"Unresolved reference issue {issue['id']} ({issue['category']}): "
        f"{issue['note']} Review: {issue['review']}"
    )


def apply_reference_issues(tasks, source, registry):
    """Deep-copy tasks and attach only identity-bound unresolved-review annotations."""
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    _validate_source(source)
    issues = _validate_registry(registry)
    by_target = {
        tuple(issue[field] for field in ("dataset", "subset", "source_split", "task_id")): issue
        for issue in issues
    }

    annotated = copy.deepcopy(tasks)
    applied = []
    for original, task in zip(tasks, annotated, strict=True):
        if not isinstance(original, dict) or not isinstance(task, dict):
            raise ValueError("tasks must contain objects")
        try:
            target = tuple(original[field] for field in ("dataset", "subset", "source_split", "id"))
        except KeyError as exc:
            raise ValueError(f"task missing identity field {exc.args[0]}") from exc
        issue = by_target.get(target)
        if issue is None:
            continue
        if (
            any(source[field] != issue[field] for field in ("dataset", "subset", "source_split"))
            or source["revision"] != issue["revision"]
            or source["sha256"] != issue["source_sha256"]
        ):
            raise ValueError(f"reference issue {issue['id']} source identity mismatch")
        try:
            task_hash = canonical_hash(original)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"reference issue {issue['id']} task cannot be content-hashed"
            ) from exc
        if task_hash != issue["task_sha256"]:
            raise ValueError(f"reference issue {issue['id']} task identity mismatch")
        reference = task.get("reference")
        if not isinstance(reference, dict):
            raise ValueError(f"reference issue {issue['id']} task reference must be an object")
        existing = reference.get("requires_review")
        if existing is not None and (not isinstance(existing, str) or not existing.strip()):
            raise ValueError("task requires_review must be a non-empty string when present")
        existing_issues = reference.get("reference_issues", [])
        if not isinstance(existing_issues, list) or any(
            not isinstance(value, str) or not value.strip() for value in existing_issues
        ):
            raise ValueError(
                "task reference_issues must be a list of non-empty strings when present"
            )
        message = _review_message(issue)
        reference["requires_review"] = f"{existing} {message}" if existing else message
        reference["reference_issues"] = [*existing_issues, issue["id"]]
        applied.append(issue["id"])
    return annotated, applied
