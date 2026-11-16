"""Offline synthetic typed-value and source-ancestry acceptance spike."""

import argparse
import errno
import hashlib
import importlib.metadata
import json
import socket
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
IX = "http://www.xbrl.org/2013/inlineXBRL"
XHTML = "http://www.w3.org/1999/xhtml"
INSTANCE = "http://www.xbrl.org/2003/instance"


def expanded(qname):
    return f"{{{qname.namespaceURI}}}{qname.localName}"


def dependency_paths(path):
    import arelle

    cache = Path(arelle.__file__).parent / "resources/cache/http/www.xbrl.org/2003"
    result = {path.name: path, "synthetic.xsd": path.with_name("synthetic.xsd")}
    for name in (
        "xbrl-instance-2003-12-31.xsd",
        "xbrl-linkbase-2003-12-31.xsd",
        "xl-2003-12-31.xsd",
        "xlink-2003-12-31.xsd",
    ):
        result[f"http://www.xbrl.org/2003/{name}"] = (cache / name).resolve()
    return result


def extract(path, manifest_path=HERE / "typed-manifest.json"):
    """Quarantine the whole fixture on schema errors or ambiguous source identity."""
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    from lxml import etree

    if importlib.metadata.version("arelle-release") != "2.47.2":
        raise ValueError("Pinned Arelle version required")
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("OS network denial required")
    path = Path(path).resolve()
    declared = dependency_paths(path)
    manifest_raw = Path(manifest_path).read_bytes()
    manifest = json.loads(manifest_raw)
    captured = {p: p.read_bytes() for p in declared.values()}
    if {key: hashlib.sha256(captured[p]).hexdigest() for key, p in declared.items()} != manifest:
        raise ValueError("Declared source/dependency hash differs")
    raw = captured[path]
    original = etree.fromstring(
        raw, etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False)
    )
    if original.getroottree().docinfo.doctype:
        raise ValueError("DTD unsupported in synthetic acceptance fixture")
    ids = {}
    for element in original.iter():
        identifier = element.get("id")
        if identifier is not None:
            if identifier in ids:
                raise ValueError("Duplicate source ID")
            ids[identifier] = element
    source_facts = original.findall(f".//{{{IX}}}nonFraction")
    if original.findall(f".//{{{IX}}}nonNumeric") or original.findall(f".//{{{IX}}}fraction"):
        raise ValueError("Only synthetic nonFraction facts are supported")
    if any(len(f) for f in source_facts):
        raise ValueError("Nested fact content unsupported in this fixture")
    if any(not f.get("id") for f in source_facts):
        raise ValueError("Synthetic facts require unique source IDs")
    with tempfile.TemporaryDirectory() as cache:
        options = RuntimeOptions(
            entrypointFile=str(path),
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
        with Session() as session:
            success = session.run(options)
            models = session.get_models()
            diagnostics = sorted(
                {
                    (v["levelname"], v["messageCode"])
                    for v in session.get_log_messages()
                    if v["levelname"] in {"ERROR", "CRITICAL"}
                }
            )
            if not success or len(models) != 1 or diagnostics or models[0].errors:
                raise ValueError(f"Typed validation rejected: {diagnostics}")
            model = models[0]
            if sorted(f.id for f in model.facts) != sorted(f.get("id") for f in source_facts):
                raise ValueError("Source/parsed occurrence inventory differs")
            dependencies = {}
            for uri, document in model.urlDocs.items():
                dependency = Path(document.filepath).resolve()
                content = dependency.read_bytes()
                key = dependency.name if dependency.parent == path.parent else uri
                if (
                    key not in declared
                    or dependency != declared[key]
                    or content != captured[dependency]
                ):
                    raise ValueError("Unexpected or changed loaded document")
                dependencies[key] = hashlib.sha256(content).hexdigest()
            if dependencies != manifest:
                raise ValueError("Loaded document inventory differs")
            facts = []
            for fact in model.facts:
                if fact.concept is None or fact.xValid < 4:
                    raise ValueError("Unresolved or invalid fact")
                if not fact.isNil and not isinstance(fact.xValue, Decimal):
                    raise ValueError("Expected exact decimal numeric value")
                source = ids[fact.id]
                locator = original.getroottree().getpath(source)
                parsed_locator = fact.getroottree().getpath(fact)
                namespaces = {k: v for k, v in source.nsmap.items() if k is not None}
                if (
                    locator != parsed_locator
                    or original.getroottree().xpath(locator, namespaces=namespaces) != [source]
                    or source.tag != fact.tag
                    or dict(source.attrib) != dict(fact.attrib)
                    or source.text != fact.text
                ):
                    raise ValueError("Original source occurrence does not round-trip")
                cells = [
                    e
                    for e in source.iterancestors()
                    if e.tag in {f"{{{XHTML}}}td", f"{{{XHTML}}}th"}
                ]
                if not cells or not cells[0].get("id"):
                    raise ValueError("Missing source cell identity")
                context = fact.context
                context_source = ids[fact.contextID]
                period = context_source.find(f"{{{INSTANCE}}}period")
                lexical_period = {etree.QName(e).localname: e.text for e in period}
                normalized_period = (
                    {"instant": context.instantDatetime.isoformat()}
                    if context.isInstantPeriod
                    else {
                        "start": context.startDatetime.isoformat(),
                        "end": context.endDatetime.isoformat(),
                    }
                )
                facts.append(
                    {
                        "id": fact.id,
                        "concept": expanded(fact.qname),
                        "source_xpath": locator,
                        "xpath_namespaces": namespaces,
                        "source_element_name": source.tag,
                        "source_cell_id": cells[0].get("id"),
                        "source_cell_xpath": original.getroottree().getpath(cells[0]),
                        "source_text": source.text,
                        "attributes": dict(source.attrib),
                        "value": None if fact.isNil else str(fact.xValue),
                        "nil": fact.isNil,
                        "validation_state": fact.xValid,
                        "context_id": fact.contextID,
                        "entity": list(context.entityIdentifier),
                        "reported_period": lexical_period,
                        "normalized_period": normalized_period,
                        "unit_id": fact.unitID,
                        "unit_measures": [
                            [expanded(q) for q in measures] for measures in fact.unit.measures
                        ],
                        "context_xpath": original.getroottree().getpath(context_source),
                        "unit_xpath": original.getroottree().getpath(ids[fact.unitID]),
                        "association": "original_source_cell_ancestry; rendered_visibility_not_verified",
                    }
                )
    if (
        any(p.read_bytes() != content for p, content in captured.items())
        or Path(manifest_path).read_bytes() != manifest_raw
    ):
        raise ValueError("Loaded source or dependency changed")
    return {
        "version": "synthetic-typed-values-v1",
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "loaded_document_sha256": dict(sorted(dependencies.items())),
        "diagnostics": diagnostics,
        "facts": sorted(facts, key=lambda f: f["id"]),
    }


def check(result):
    facts = {f["id"]: f for f in result["facts"]}
    concepts = {
        "assets": "Assets",
        "revenue": "Revenue",
        "eps": "EarningsPerShare",
        "missing": "MissingAmount",
        "zero": "ZeroAmount",
    }
    expected = {
        "assets": "-12000",
        "revenue": "1250000",
        "eps": "2.50",
        "missing": None,
        "zero": "0",
    }
    if {k: v["value"] for k, v in facts.items()} != expected:
        raise ValueError("Typed values differ from independently declared expectations")
    for identifier, fact in facts.items():
        if fact["concept"] != f"{{urn:synthetic:finance}}{concepts[identifier]}":
            raise ValueError("Resolved concept differs")
        if (
            fact["nil"] != (identifier == "missing")
            or fact["source_cell_id"] != f"cell-{identifier}"
        ):
            raise ValueError("Nil or source ancestry mismatch")
        if fact["entity"] != ["urn:example", "synthetic"]:
            raise ValueError("Entity mismatch")
        if identifier in {"revenue", "eps"}:
            expected_period = {"startDate": "2025-01-01", "endDate": "2025-12-31"}
            expected_normalized = {"start": "2025-01-01T00:00:00", "end": "2026-01-01T00:00:00"}
        else:
            expected_period = {"instant": "2025-12-31"}
            expected_normalized = {"instant": "2026-01-01T00:00:00"}
        if (
            fact["reported_period"] != expected_period
            or fact["normalized_period"] != expected_normalized
        ):
            raise ValueError("Period lexical/normalized mismatch")
        units = [
            ["{http://www.xbrl.org/2003/iso4217}USD"],
            ["{http://www.xbrl.org/2003/instance}shares"] if identifier == "eps" else [],
        ]
        if fact["unit_measures"] != units:
            raise ValueError("Resolved units differ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = extract(HERE / "valid-values.xhtml")
    check(result)
    result["driver_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
