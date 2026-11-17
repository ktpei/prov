"""Synthetic negative preflight, run under an OS network-denial profile on macOS.

Not a production extractor. Install arelle-release==2.47.2 in an isolated
environment; no project dependency is added. Never open issuer files here.
"""

import argparse
import errno
import hashlib
import importlib.metadata
import json
import platform
import shutil
import socket
import tempfile
from pathlib import Path


def preflight():
    if importlib.metadata.version("arelle-release") != "2.47.2":
        raise ValueError("Preflight requires the inspected Arelle version")
    with socket.socket() as probe:
        probe.settimeout(1)
        denied = probe.connect_ex(("127.0.0.1", 9))
    if denied != errno.EPERM:
        raise ValueError("Expected OS-denied network probe; use the documented profile")
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions

    fixture = Path(__file__).with_name("missing-schema.xhtml")
    raw = fixture.read_bytes()
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        entrypoint = directory / fixture.name
        shutil.copyfile(fixture, entrypoint)
        options = RuntimeOptions(
            entrypointFile=str(entrypoint),
            internetConnectivity="offline",
            disablePersistentConfig=True,
            cacheDirectory=str(directory / "cache"),
            keepOpen=True,
            validate=True,
            requireInlineXbrl=True,
            skipDTS=False,
            formulaAction="none",
            validateDuplicateFacts="all",
            logFile="logToStructuredMessage",
        )
        with Session() as session:
            api_success = session.run(options)
            models = session.get_models()
            errors = sorted(str(code) for model in models for code in model.errors)
            facts = sum(len(model.facts) for model in models)
            diagnostics = sorted(
                {
                    (log["levelname"], log["messageCode"])
                    for log in session.get_log_messages()
                    if log["levelname"] in {"ERROR", "CRITICAL"}
                }
            )
        if not {"IOerror", "ix11.12.1.2:missingReferences"} <= set(errors):
            raise ValueError("Missing schema did not produce expected rejection diagnostics")
        if fixture.read_bytes() != raw or entrypoint.read_bytes() != raw:
            raise ValueError("Synthetic fixture changed")
    return {
        "version": "arelle-missing-schema-preflight-v1",
        "python": platform.python_version(),
        "packages": dict(
            sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
        ),
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "network_control": "macOS sandbox-exec (version 1)(allow default)(deny network*)",
        "loopback_connect_errno": denied,
        "api_success": api_success,
        "parsed_fact_occurrences": facts,
        "validation_error_codes": errors,
        "error_diagnostics": diagnostics,
        "disposition": "dependency_incomplete_rejected",
        "accepted_fact_occurrences": 0,
        "limitations": [
            "Only a synthetic missing-schema negative path; successful typed extraction is untested.",
            "The network-denial profile is OS-enforced; the loopback probe checks one observed path, not all possible transports.",
            "Packages are version-recorded, not a complete hashed loaded-dependency manifest.",
            "No issuer document, full taxonomy, transformation or visible-cell provenance acceptance yet.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = preflight()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
