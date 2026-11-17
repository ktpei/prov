"""Paired offline validation of a pinned SEC transform plugin on one exposed filing."""

import argparse
import errno
import hashlib
import importlib.metadata
import json
import socket
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "runs/xbrl-dependency-acquisition-v1"
PLUGIN = ROOT / "runs/sec-transforms-26.3"
SEC = "http://www.sec.gov/inlineXBRL/transformation/2015-08-31"
IX = "http://www.xbrl.org/2013/inlineXBRL"
PINNED = {
    "sec_transform/__init__.py": "2296586f945ffd95ab37d3d4147c4e45f42ce4e5f397f61143e053208adefbf1",
    "sec_transform/text2num.py": "6c9b26354320a2fb34fe380cdc71ff7f8d1cc712811e6b10c661e512f0383409",
    "LICENSE": "5537d4d10b76b81b6e8dfd8b644480a4b1efa332fbb0cdb61126c5be781ef7b4",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def expanded(qname):
    return f"{{{qname.namespaceURI}}}{qname.localName}"


def input_paths():
    return [
        Path(__file__).resolve(),
        DATA / "bundle.zip",
        DATA / "bundle-manifest.json",
        PLUGIN / "receipt.json",
        *(PLUGIN / name for name in PINNED),
    ]


def snapshot():
    captured = {path: path.read_bytes() for path in input_paths()}
    for name, digest in PINNED.items():
        if sha(captured[PLUGIN / name]) != digest:
            raise ValueError("Pinned plugin source differs")
    if (
        sha(captured[DATA / "bundle.zip"])
        != "ade3c023038770e773e0bc0f891df772b8b397897d115384335a6df072deb51f"
    ):
        raise ValueError("Frozen filing package differs")
    return captured


def observe(with_plugin):
    from arelle import PluginManager
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    from arelle.ValidateDuplicateFacts import getDuplicateFactSets
    from lxml import etree

    if importlib.metadata.version("arelle-release") != "2.47.5":
        raise ValueError("Arelle 2.47.5 required")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("OS network denial required")
    captured = snapshot()
    manifest = json.loads(captured[DATA / "bundle-manifest.json"])
    bundle = (DATA / "bundle.zip").resolve()
    with zipfile.ZipFile(bundle) as archive:
        for record in manifest["documents"].values():
            if sha(archive.read(record["member"])) != record["sha256"]:
                raise ValueError("Package member differs")
        raw = archive.read(manifest["documents"][manifest["entrypoint"]]["member"])
    if sha(raw) != "7ba28f8a0327378bb816e536b8f7861c233e394f9a041cce8e1d3101374c77b0":
        raise ValueError("Original source differs")
    original = etree.fromstring(
        raw, etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False)
    )
    source_facts = [
        element
        for element in original.iter()
        if element.tag in {f"{{{IX}}}nonFraction", f"{{{IX}}}nonNumeric"}
    ]
    ids = {element.get("id"): element for element in source_facts}
    if None in ids or len(ids) != len(source_facts):
        raise ValueError("Missing or duplicate fact IDs")
    with tempfile.TemporaryDirectory() as cache, Session() as session:
        success = session.run(
            RuntimeOptions(
                entrypointFile=manifest["entrypoint"],
                packages=[str(bundle)],
                plugins=str(PLUGIN / "sec_transform") if with_plugin else None,
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
        initial_diagnostics = [
            message
            for message in session.get_log_messages()
            if message["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
        ]
        models = session.get_models()
        if len(models) != 1:
            raise ValueError("Expected exactly one model")
        model = models[0]
        if model.modelDocument.uri != manifest["entrypoint"]:
            raise ValueError("Canonical entrypoint changed")
        loaded = {}
        for uri, document in model.urlDocs.items():
            expected = manifest["documents"].get(uri)
            if not expected or document.filepath != str(bundle) + "/" + expected["member"]:
                raise ValueError("Undeclared loaded document/path")
            with model.fileSource.file(document.filepath, binary=True)[0] as handle:
                loaded[uri] = sha(handle.read())
            if loaded[uri] != expected["sha256"]:
                raise ValueError("Loaded bytes differ")
        if set(loaded) != set(manifest["documents"]):
            raise ValueError("Loaded document inventory differs")
        manager = PluginManager.getInstance()
        configured = manager.pluginConfig.get("modules", {})
        actual = manager.modulePluginInfos
        names = ["SEC Inline Transforms"] if with_plugin else []
        if sorted(configured) != names or sorted(actual) != names:
            raise ValueError("Plugin inventory differs from explicit allowlist")
        plugin_records = {}
        for name, info in actual.items():
            hook = info["ModelManager.LoadCustomTransforms"]
            source_path = Path(hook.__code__.co_filename).resolve()
            if source_path != (PLUGIN / "sec_transform/__init__.py").resolve():
                raise ValueError("Loaded plugin hook origin differs")
            helper = sys.modules.get(hook.__module__ + ".text2num")
            if (
                helper is None
                or Path(helper.__file__).resolve()
                != (PLUGIN / "sec_transform/text2num.py").resolve()
            ):
                raise ValueError("Loaded transform helper origin differs")
            plugin_records[name] = {
                "version": info["version"],
                "license": info["license"],
                "hook_sha256": sha(source_path.read_bytes()),
                "helper_sha256": sha(Path(helper.__file__).read_bytes()),
            }
        if sorted(f.id for f in model.facts) != sorted(ids):
            raise ValueError("Original/parsed fact inventory differs")
        facts, affected = [], []
        for fact in sorted(model.facts, key=lambda fact: fact.id):
            source = ids[fact.id]
            if etree.tostring(source, method="c14n") != etree.tostring(fact, method="c14n"):
                raise ValueError("Parsed source occurrence differs from original XML tree")
            value = str(getattr(fact, "xValue", None))
            record = {
                "id": fact.id,
                "concept": expanded(fact.qname),
                "context_id": fact.contextID,
                "unit_id": fact.unitID,
                "nil": fact.isNil,
                "validation_state": fact.xValid,
                "typed_value_type": type(getattr(fact, "xValue", None)).__name__,
                "typed_value_sha256": sha(value.encode()),
                "original_occurrence_sha256": sha(etree.tostring(source, method="c14n")),
            }
            facts.append(record)
            if fact.format is not None and fact.format.namespaceURI == SEC:
                affected.append(
                    {
                        **record,
                        "format": expanded(fact.format),
                        "typed_value": value,
                        "source_text": "".join(source.itertext()),
                        "continued_at": source.get("continuedAt"),
                        "source_xpath": original.getroottree().getpath(source),
                    }
                )
        diagnostics = [
            message
            for message in session.get_log_messages()
            if message["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
        ]
        after_values_diagnostic_counts = dict(
            sorted(Counter(m["messageCode"] for m in diagnostics).items())
        )
        groups = sorted(
            [
                {
                    "ids": sorted(f.id for f in group.facts),
                    "complete": group.areAllComplete,
                    "consistent": group.areAllConsistent,
                    "inconsistent": group.areAnyInconsistent,
                }
                for group in getDuplicateFactSets(model.facts, includeSingles=False)
            ],
            key=lambda group: group["ids"],
        )
        diagnostics = [
            message
            for message in session.get_log_messages()
            if message["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
        ]
        result = {
            "version": "pinned-sec-transforms-issuer-observation-v1",
            "runtime": {
                "python": sys.version.split()[0],
                "distributions": dict(
                    sorted(
                        (distribution.metadata["Name"], distribution.version)
                        for distribution in importlib.metadata.distributions()
                    )
                ),
            },
            "with_plugin": with_plugin,
            "api_success": success,
            "model_errors": sorted(model.errors),
            "after_values_diagnostic_counts": after_values_diagnostic_counts,
            "initial_diagnostic_counts": dict(
                sorted(Counter(m["messageCode"] for m in initial_diagnostics).items())
            ),
            "diagnostic_counts": dict(
                sorted(Counter(m["messageCode"] for m in diagnostics).items())
            ),
            "plugin_inventory": plugin_records,
            "loaded_document_sha256": dict(sorted(loaded.items())),
            "facts": facts,
            "affected_facts": affected,
            "duplicate_groups": groups,
            "context_source_sha256": {
                k: sha(etree.tostring(v, method="c14n")) for k, v in sorted(model.contexts.items())
            },
            "unit_source_sha256": {
                k: sha(etree.tostring(v, method="c14n")) for k, v in sorted(model.units.items())
            },
            "registered_sec_transforms": sorted(
                expanded(q)
                for q in (model.modelManager.customTransforms or {})
                if q.namespaceURI == SEC
            ),
        }
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Observation inputs changed")
    result["input_sha256"] = {
        str(path.relative_to(ROOT)): sha(raw) for path, raw in captured.items()
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--with-plugin", action="store_true")
    args = parser.parse_args()
    result = observe(args.with_plugin)
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
