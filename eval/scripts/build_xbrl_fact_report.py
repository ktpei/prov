"""Build an optional typed fact sidecar from the frozen exposed ODFL package."""

import argparse
import errno
import importlib.metadata
import json
import socket
import sys
import tempfile
import zipfile
from pathlib import Path

from eval.spikes.arelle.sec_transforms import DATA, PLUGIN, ROOT, expanded, sha, snapshot
from provenance.xbrl_facts import build_fact_sidecar

OBSERVATION = ROOT / "eval/spikes/arelle/sec-transform-result.json"
OCCURRENCES = ROOT / "eval/reports/xbrl-occurrences-2026-11-16/occurrences.json"


TABLES = ROOT / "runs/native-html-v1-issuer-eligibility/old-dominion-2025-06-30-10q-tables.json"


def build():
    from arelle import PluginManager
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    from lxml import etree

    if importlib.metadata.version("arelle-release") != "2.47.5":
        raise ValueError("Pinned Arelle runtime required")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("OS network denial required")
    captured = snapshot()
    for path in (
        OBSERVATION,
        OCCURRENCES,
        TABLES,
        ROOT / "provenance/xbrl_occurrences.py",
        ROOT / "provenance/table_structure.py",
        Path(__file__).resolve(),
        ROOT / "provenance/xbrl_facts.py",
    ):
        captured[path] = path.read_bytes()
    if (
        sha(captured[OBSERVATION])
        != "6e68cad69b919b0f700f27d8f6fc7a2a416018ef900e55c0f0b01a7747ab2230"
        or sha(captured[OCCURRENCES])
        != "8d4ba2e658b08c17323c02dbed33d515e5c2e7102ed72ebca211cdfbe07c12cb"
    ):
        raise ValueError("Frozen observation/source sidecar differs")
    prior = json.loads(captured[OBSERVATION])["candidate"]
    runtime = {
        "python": sys.version.split()[0],
        "distributions": dict(
            sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
        ),
    }
    if runtime != prior["runtime"]:
        raise ValueError("Runtime distribution identity differs")
    manifest = json.loads(captured[DATA / "bundle-manifest.json"])
    bundle = (DATA / "bundle.zip").resolve()
    with zipfile.ZipFile(bundle) as archive:
        for record in manifest["documents"].values():
            if sha(archive.read(record["member"])) != record["sha256"]:
                raise ValueError("Package member differs")
        raw = archive.read(manifest["documents"][manifest["entrypoint"]]["member"])
    occurrences = json.loads(captured[OCCURRENCES])
    with tempfile.TemporaryDirectory() as cache, Session() as session:
        success = session.run(
            RuntimeOptions(
                entrypointFile=manifest["entrypoint"],
                packages=[str(bundle)],
                plugins=str(PLUGIN / "sec_transform"),
                internetConnectivity="offline",
                disablePersistentConfig=True,
                cacheDirectory=cache,
                keepOpen=True,
                validate=True,
                requireInlineXbrl=True,
                skipDTS=False,
                formulaAction="none",
                validateDuplicateFacts="all",
                logFile="logToStructuredMessage",
            )
        )
        models = session.get_models()
        if not success or len(models) != 1 or models[0].errors:
            raise ValueError("Full validation failed")
        model = models[0]
        manager = PluginManager.getInstance()
        if sorted(manager.pluginConfig.get("modules", {})) != ["SEC Inline Transforms"] or sorted(
            manager.modulePluginInfos
        ) != ["SEC Inline Transforms"]:
            raise ValueError("Plugin allowlist differs")
        plugin = manager.modulePluginInfos["SEC Inline Transforms"]
        hook = plugin["ModelManager.LoadCustomTransforms"]
        helper = sys.modules[hook.__module__ + ".text2num"]
        if (
            Path(hook.__code__.co_filename).resolve()
            != (PLUGIN / "sec_transform/__init__.py").resolve()
            or Path(helper.__file__).resolve() != (PLUGIN / "sec_transform/text2num.py").resolve()
        ):
            raise ValueError("Loaded plugin source origin differs")
        loaded = {}
        for uri, document in model.urlDocs.items():
            expected = manifest["documents"].get(uri)
            if not expected or document.filepath != str(bundle) + "/" + expected["member"]:
                raise ValueError("Undeclared loaded document")
            with model.fileSource.file(document.filepath, binary=True)[0] as handle:
                loaded[uri] = sha(handle.read())
        if loaded != prior["loaded_document_sha256"]:
            raise ValueError("Loaded dependency hashes differ")
        fingerprints = []
        for fact in sorted(model.facts, key=lambda fact: fact.id):
            fingerprints.append(
                {
                    "id": fact.id,
                    "concept": expanded(fact.qname),
                    "context_id": fact.contextID,
                    "unit_id": fact.unitID,
                    "nil": fact.isNil,
                    "validation_state": fact.xValid,
                    "typed_value_type": type(fact.xValue).__name__,
                    "typed_value_sha256": sha(str(fact.xValue).encode()),
                    "original_occurrence_sha256": sha(etree.tostring(fact, method="c14n")),
                }
            )
        if fingerprints != prior["facts"]:
            raise ValueError("Runtime fact fingerprints differ from frozen observation")
        result = build_fact_sidecar(model, raw, occurrences, loaded, captured[TABLES])
        diagnostics = [
            message
            for message in session.get_log_messages()
            if message["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
        ]
        if (
            any(message["levelname"] in {"ERROR", "CRITICAL"} for message in diagnostics)
            or model.errors
        ):
            raise ValueError("Errors after serialization")
        result["diagnostics"] = [
            {"level": message["levelname"], "code": message["messageCode"]}
            for message in diagnostics
        ]
        result["runtime"] = runtime
        result["plugin_inventory"] = prior["plugin_inventory"]
        result["loaded_document_sha256"] = dict(sorted(loaded.items()))
    if any(path.read_bytes() != content for path, content in captured.items()):
        raise ValueError("Sidecar inputs changed")
    result["input_sha256"] = {
        str(path.relative_to(ROOT)): sha(content) for path, content in captured.items()
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "facts": len(result["facts"]),
                "contexts": len(result["contexts"]),
                "units": len(result["units"]),
                "defaults": len(result["taxonomy_defaults"]),
            }
        )
    )
