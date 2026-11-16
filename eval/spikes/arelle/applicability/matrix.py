"""Fixed offline dimension-default/applicability matrix, not a fact exporter."""

import argparse
import errno
import hashlib
import importlib.metadata
import json
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMESPACE = "urn:synthetic:applicability"
DIM = "http://xbrl.org/int/dim/arcrole/"
CASES = (
    "omitted_default",
    "north",
    "explicit_default",
    "unusable_south",
    "undefined_member",
    "north_in_scenario",
    "extra_segment_axis",
    "missing_default",
    "default_outside_domain",
    "scenario_without_default",
    "declared_outside_domain",
    "extra_scenario_axis",
    "residual_segment",
    "residual_scenario",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def expanded(qname):
    return f"{{{qname.namespaceURI}}}{qname.localName}"


def reference_href(href):
    path, separator, fragment = href.partition("#")
    return Path(path).name + separator + fragment


def run_case(name):
    import arelle
    from arelle.api.Session import Session
    from arelle.RuntimeOptions import RuntimeOptions
    from lxml import etree

    if importlib.metadata.version("arelle-release") != "2.47.5":
        raise ValueError("Arelle 2.47.5 required")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("OS network denial required")
    baseline = {
        n: (HERE / n).read_bytes() for n in ("omitted.xhtml", "taxonomy.xsd", "definition.xml")
    }
    manifest_raw = (HERE / "manifest.json").read_bytes()
    expected = json.loads(manifest_raw)
    cache = Path(arelle.__file__).parent / "resources/cache/http/www.xbrl.org"
    standard = {
        uri: cache / uri.removeprefix("http://www.xbrl.org/")
        for uri in expected
        if uri.startswith("http:")
    }
    bound = baseline | {uri: path.read_bytes() for uri, path in standard.items()}
    if {key: sha(raw) for key, raw in bound.items()} != expected:
        raise ValueError("Baseline or bundled dependency hash differs")
    driver_raw = Path(__file__).read_bytes()
    parser = etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False)
    root = etree.fromstring(baseline["omitted.xhtml"], parser)
    links = etree.fromstring(baseline["definition.xml"], parser)
    ns = {"x": "http://www.xbrl.org/2003/instance", "l": "http://www.xbrl.org/2003/linkbase"}
    context = root.find(".//x:context", ns)
    members = {
        "north": [("RegionAxis", "North")],
        "declared_outside_domain": [("RegionAxis", "East")],
        "extra_scenario_axis": [("ExtraAxis", "North")],
        "explicit_default": [("RegionAxis", "AllRegions")],
        "unusable_south": [("RegionAxis", "South")],
        "undefined_member": [("RegionAxis", "Undeclared")],
        "north_in_scenario": [("RegionAxis", "North")],
        "scenario_without_default": [("RegionAxis", "North")],
        "extra_segment_axis": [("RegionAxis", "North"), ("ExtraAxis", "North")],
    }.get(name, [])
    if members:
        location = (
            "scenario"
            if name in {"north_in_scenario", "scenario_without_default", "extra_scenario_axis"}
            else "segment"
        )
        container = etree.Element(f"{{{ns['x']}}}{location}")
        for axis, member in members:
            element = etree.SubElement(container, "{http://xbrl.org/2006/xbrldi}explicitMember")
            element.set("dimension", "s:" + axis)
            element.text = "s:" + member
        (context if location == "scenario" else context.find("x:entity", ns)).append(container)
    if name in {"residual_segment", "residual_scenario"}:
        location = name.removeprefix("residual_")
        container = etree.Element(f"{{{ns['x']}}}{location}")
        etree.SubElement(container, f"{{{NAMESPACE}}}Basis").text = "budget"
        (context if location == "scenario" else context.find("x:entity", ns)).append(container)
    for arc in list(links.findall(".//l:definitionArc", ns)):
        role = arc.get("{http://www.w3.org/1999/xlink}arcrole")
        target = arc.get("{http://www.w3.org/1999/xlink}to")
        if (
            name in {"missing_default", "scenario_without_default"}
            and role == DIM + "dimension-default"
        ) or (
            name == "default_outside_domain" and role == DIM + "domain-member" and target == "all"
        ):
            arc.getparent().remove(arc)
    candidate = {
        "omitted.xhtml": etree.tostring(root),
        "taxonomy.xsd": baseline["taxonomy.xsd"],
        "definition.xml": etree.tostring(links),
    }
    candidate_hashes = {key: sha(raw) for key, raw in candidate.items()} | {
        uri: sha(bound[uri]) for uri in standard
    }
    with tempfile.TemporaryDirectory() as work:
        work = Path(work).resolve()
        for filename, raw in candidate.items():
            (work / filename).write_bytes(raw)
        paths = {key: work / key for key in candidate} | standard
        with Session() as session:
            success = session.run(
                RuntimeOptions(
                    entrypointFile=str(work / "omitted.xhtml"),
                    internetConnectivity="offline",
                    disablePersistentConfig=True,
                    cacheDirectory=str(work / "cache"),
                    keepOpen=True,
                    validate=True,
                    requireInlineXbrl=True,
                    skipDTS=False,
                    formulaAction="none",
                    logFile="logToStructuredMessage",
                )
            )
            models = session.get_models()
            if len(models) != 1:
                raise ValueError("Expected one model")
            model = models[0]
            diagnostics = sorted(
                {
                    (m["levelname"], m["messageCode"])
                    for m in session.get_log_messages()
                    if m["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
                }
            )
            loaded = {}
            for uri, document in model.urlDocs.items():
                path = Path(document.filepath).resolve()
                key = path.name if path.parent == work else uri
                if key not in paths or path != paths[key].resolve():
                    raise ValueError("Unexpected loaded dependency")
                loaded[key] = sha(path.read_bytes())
            if loaded != candidate_hashes:
                raise ValueError("Loaded inventory/hash differs")
            context = model.contexts["scope"]
            result = {
                "case": name,
                "baseline_document_sha256": expected,
                "driver_sha256": sha(driver_raw),
                "manifest_sha256": sha(manifest_raw),
                "api_success": success,
                "accepted": bool(
                    success
                    and not model.errors
                    and not any(level in {"ERROR", "CRITICAL"} for level, _ in diagnostics)
                ),
                "diagnostics": diagnostics,
                "model_errors": sorted(model.errors),
                "candidate_document_sha256": dict(sorted(candidate_hashes.items())),
                "reported_dimensions": {
                    expanded(q): expanded(d.memberQname) for q, d in context.qnameDims.items()
                },
                "reported_locations": {
                    expanded(q): d.contextElement for q, d in context.qnameDims.items()
                },
                "taxonomy_defaults": {
                    expanded(q): expanded(member)
                    for q, member in model.qnameDimensionDefaults.items()
                },
                "fact_count": len(model.facts),
                "facts": [
                    {
                        "id": f.id,
                        "context_id": f.contextID,
                        "concept": expanded(f.qname),
                        "value": str(f.xValue),
                        "schema_validation_state": f.xValid,
                    }
                    for f in model.facts
                ],
                "diagnostic_references": [
                    {
                        "code": m["messageCode"],
                        "references": [
                            {
                                "href": reference_href(ref.get("href", "")),
                                "source_line": ref.get("sourceLine"),
                            }
                            for ref in m.get("refs", [])
                        ],
                    }
                    for m in session.get_log_messages()
                    if m["levelname"] in {"WARNING", "ERROR", "CRITICAL"}
                ],
            }
        if any(sha(path.read_bytes()) != candidate_hashes[key] for key, path in paths.items()):
            raise ValueError("Loaded source changed")
    if any((HERE / key).read_bytes() != raw for key, raw in baseline.items()):
        raise ValueError("Baseline changed")
    if (HERE / "manifest.json").read_bytes() != manifest_raw or Path(
        __file__
    ).read_bytes() != driver_raw:
        raise ValueError("Driver or manifest changed")
    return result


def matrix():
    import arelle

    cache = Path(arelle.__file__).parent / "resources/cache/http/www.xbrl.org"
    manifest_raw = (HERE / "manifest.json").read_bytes()
    expected = json.loads(manifest_raw)
    paths = {
        key: cache / key.removeprefix("http://www.xbrl.org/")
        if key.startswith("http:")
        else HERE / key
        for key in expected
    }
    captured = {path: path.read_bytes() for path in paths.values()}
    if {key: sha(captured[path]) for key, path in paths.items()} != expected:
        raise ValueError("Parent baseline inventory differs")
    driver = Path(__file__).resolve()
    captured[driver] = driver.read_bytes()
    captured[HERE / "manifest.json"] = manifest_raw
    driver_hash = sha(captured[driver])
    manifest_hash = sha(manifest_raw)
    results = []
    for case in CASES:
        process = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--case", case],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        result = json.loads(process.stdout)
        if (
            result["baseline_document_sha256"] != expected
            or result["driver_sha256"] != driver_hash
            or result["manifest_sha256"] != manifest_hash
        ):
            raise ValueError("Child revision differs from parent snapshot")
        results.append(result)
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Matrix inputs changed across child runs")
    return {
        "version": "synthetic-dimensional-applicability-v1",
        "arelle_version": importlib.metadata.version("arelle-release"),
        "driver_sha256": driver_hash,
        "manifest_sha256": manifest_hash,
        "cases": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--case", choices=CASES)
    args = parser.parse_args()
    if args.case:
        print(json.dumps(run_case(args.case)))
    elif args.output:
        result = matrix()
        with args.output.open("x") as handle:
            handle.write(json.dumps(result, indent=2) + "\n")
    else:
        parser.error("Specify output or --case")
