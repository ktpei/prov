"""Offline, fixed-fixture dimensional context observation; not an extraction adapter."""

import argparse
import errno
import hashlib
import importlib.metadata
import json
import socket
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
XBRLI = "http://www.xbrl.org/2003/instance"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def expanded(qname):
    return f"{{{qname.namespaceURI}}}{qname.localName}"


def observe():
    import arelle
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    from arelle.ValidateDuplicateFacts import getDuplicateFactSets
    from lxml import etree

    if importlib.metadata.version("arelle-release") != "2.47.5":
        raise ValueError("Requires Arelle 2.47.5")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("Requires OS network denial")
    cache_root = Path(arelle.__file__).parent / "resources/cache/http/www.xbrl.org"
    paths = {name: HERE / name for name in ("dimensions.xhtml", "synthetic.xsd")}
    for name in (
        "2003/xbrl-instance-2003-12-31.xsd",
        "2003/xbrl-linkbase-2003-12-31.xsd",
        "2003/xl-2003-12-31.xsd",
        "2003/xlink-2003-12-31.xsd",
        "2005/xbrldt-2005.xsd",
        "2006/xbrldi-2006.xsd",
    ):
        paths[f"http://www.xbrl.org/{name}"] = (cache_root / name).resolve()
    captured = {key: path.read_bytes() for key, path in paths.items()}
    manifest_raw = (HERE / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    if {key: digest(raw) for key, raw in captured.items()} != manifest:
        raise ValueError("Declared fixture/dependency hash differs")
    driver_raw = Path(__file__).read_bytes()
    source = etree.fromstring(
        captured["dimensions.xhtml"],
        etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False),
    )
    if source.getroottree().docinfo.doctype:
        raise ValueError("DTD unsupported")
    ids = {element.get("id"): element for element in source.iter() if element.get("id")}
    if len(ids) != sum(bool(element.get("id")) for element in source.iter()):
        raise ValueError("Duplicate source IDs")

    def source_record(element):
        locator = element.getroottree().getpath(element)
        namespaces = {key: value for key, value in element.nsmap.items() if key}
        matches = source.getroottree().xpath(locator, namespaces=namespaces)
        if len(matches) != 1:
            raise ValueError("Context locator does not round-trip")
        original = matches[0]
        # Canonical serialization is a tree representation, never original byte slices.
        serialized = etree.tostring(original, method="c14n")
        if serialized != etree.tostring(element, method="c14n"):
            raise ValueError("Parsed context differs from original strict XML tree")
        return {"xpath": locator, "namespaces": namespaces, "canonical_xml": serialized.decode()}

    with tempfile.TemporaryDirectory() as cache, Session() as session:
        success = session.run(
            RuntimeOptions(
                entrypointFile=str(HERE / "dimensions.xhtml"),
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
        diagnostics = sorted(
            {
                (m["levelname"], m["messageCode"])
                for m in session.get_log_messages()
                if m["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
            }
        )
        models = session.get_models()
        if not success or len(models) != 1 or models[0].errors:
            raise ValueError(f"Validation failed: {diagnostics}")
        if any(level in {"ERROR", "CRITICAL"} for level, _ in diagnostics):
            raise ValueError(f"Validation failed: {diagnostics}")
        model = models[0]
        loaded = {}
        for uri, document in model.urlDocs.items():
            path = Path(document.filepath).resolve()
            key = path.name if path.parent == HERE else uri
            if key not in paths or path != paths[key] or path.read_bytes() != captured[key]:
                raise ValueError("Unexpected or changed dependency")
            loaded[key] = digest(captured[key])
        if loaded != manifest:
            raise ValueError("Loaded dependency inventory differs")
        contexts = {}
        for identifier, context in sorted(model.contexts.items()):
            dimensions = []
            for qname, dimension in sorted(
                context.qnameDims.items(), key=lambda item: expanded(item[0])
            ):
                record = {
                    "dimension": expanded(qname),
                    "kind": "explicit" if dimension.isExplicit else "typed",
                    "location": dimension.contextElement,
                    "source": source_record(dimension),
                }
                if dimension.isExplicit:
                    record["member"] = expanded(dimension.memberQname)
                else:
                    record["typed_member"] = source_record(dimension.typedMember)
                    record["typed_member_name"] = dimension.typedMember.tag
                    record["typed_value"] = str(dimension.typedMember.xValue)
                dimensions.append(record)
            contexts[identifier] = {
                "source": source_record(context),
                "reported_dimensions": dimensions,
                "non_dimensional_content": {
                    location: [source_record(element) for element in context.nonDimValues(location)]
                    for location in ("segment", "scenario")
                },
            }
        facts = [
            {
                "id": fact.id,
                "context_id": fact.contextID,
                "concept": expanded(fact.qname),
                "value": None if fact.isNil else str(fact.xValue),
                "validation_state": fact.xValid,
            }
            for fact in sorted(model.facts, key=lambda fact: fact.id)
        ]
        duplicates = sorted(
            sorted(fact.id for fact in group.facts)
            for group in getDuplicateFactSets(model.facts, includeSingles=False)
        )
        defaults = {
            expanded(q): expanded(member) for q, member in model.qnameDimensionDefaults.items()
        }
    if any(paths[key].read_bytes() != raw for key, raw in captured.items()):
        raise ValueError("Input changed during observation")
    if (HERE / "manifest.json").read_bytes() != manifest_raw or Path(
        __file__
    ).read_bytes() != driver_raw:
        raise ValueError("Manifest or driver changed")
    return {
        "version": "synthetic-dimensional-context-observation-v1",
        "arelle_version": "2.47.5",
        "driver_sha256": digest(driver_raw),
        "manifest_sha256": digest(manifest_raw),
        "loaded_document_sha256": dict(sorted(loaded.items())),
        "diagnostics": diagnostics,
        "contexts": contexts,
        "taxonomy_dimension_defaults": defaults,
        "facts": facts,
        "duplicate_groups": duplicates,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = observe()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
