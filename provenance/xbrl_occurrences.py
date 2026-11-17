"""Original Inline XBRL occurrence locations; no value or visibility inference."""

import hashlib
import json
import re
from html.parser import HTMLParser
from xml.parsers import expat

from provenance.table_structure import _is_explicitly_hidden

IX = "http://www.xbrl.org/2013/inlineXBRL"
XHTML = "http://www.w3.org/1999/xhtml"
FACT_TAGS = {f"{{{IX}}}{name}" for name in ("nonFraction", "nonNumeric", "fraction")}
CONTINUATION = f"{{{IX}}}continuation"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _expanded(name):
    return "{" + name if "}" in name else name


class _Starts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.records = []

    def handle_starttag(self, tag, attrs):
        self.records.append((self.getpos(), self.get_starttag_text(), dict(attrs).get("id")))

    handle_startendtag = handle_starttag


def _source_nodes(raw):
    text = raw.decode("utf-8", errors="strict")
    scanner = _Starts()
    scanner.feed(text)
    scanner.close()
    lines = [0] + [match.end() for match in re.finditer("\n", text)]
    starts = []
    prior_character = prior_byte = 0
    for position, markup, identifier in scanner.records:
        character = lines[position[0] - 1] + position[1]
        byte = prior_byte + len(text[prior_character:character].encode("utf-8"))
        starts.append((byte, position, markup, identifier))
        prior_character, prior_byte = character, byte
    nodes, stack, namespaces = [], [], []
    parser = expat.ParserCreate(namespace_separator="}")

    def declaration(version, encoding, standalone):
        if encoding and encoding.lower() not in {"utf-8", "ascii", "us-ascii"}:
            raise ValueError("Only UTF-8/ASCII XML input is supported")

    def reject_dtd(*args):
        raise ValueError("DTD unsupported in occurrence inventory")

    def start(name, attributes):
        index = len(nodes)
        if index >= len(starts) or starts[index][0] != parser.CurrentByteIndex:
            raise ValueError("XML/HTML start-event positions disagree")
        byte, position, markup, html_id = starts[index]
        namespace_map = (
            dict(stack[-1]["namespaces"])
            if stack
            else {"xml": "http://www.w3.org/XML/1998/namespace"}
        )
        namespace_map.update(namespaces)
        namespaces.clear()
        lexical = re.match(r"<([^\s/>]+)", markup).group(1)
        prefix, separator, local = lexical.partition(":")
        expanded = f"{{{namespace_map.get(prefix if separator else '', '')}}}{local if separator else prefix}"
        tag = _expanded(name)
        if expanded == "{}" + lexical:
            expanded = lexical
        attributes = {_expanded(key): value for key, value in attributes.items()}
        if expanded != tag or html_id != attributes.get("id"):
            raise ValueError("XML/HTML element identity disagrees")
        geometry = {"table", "tr", "td", "th", "thead", "tbody", "tfoot"}
        local_tag = tag.removeprefix(f"{{{XHTML}}}")
        if lexical.lower() in geometry or local_tag in geometry:
            if lexical not in geometry or tag != f"{{{XHTML}}}{lexical}":
                raise ValueError("Unsupported namespace/case/prefix for HTML geometry")
            parent_tag = stack[-1]["tag"] if stack else None
            if lexical in {"td", "th"} and parent_tag != f"{{{XHTML}}}tr":
                raise ValueError("Cell parent is not a row; ambiguous HTML ancestry")
            if lexical == "tr" and parent_tag not in {
                f"{{{XHTML}}}{name}" for name in ("table", "thead", "tbody", "tfoot")
            }:
                raise ValueError("Row parent has ambiguous HTML ancestry")
            if lexical in {"thead", "tbody", "tfoot"} and parent_tag != f"{{{XHTML}}}table":
                raise ValueError("Row-group parent has ambiguous HTML ancestry")
            same_table = []
            for ancestor in reversed(stack):
                if ancestor["tag"] == f"{{{XHTML}}}table":
                    break
                same_table.append(ancestor["tag"])
            if (
                lexical == "table"
                and any(a["tag"] == f"{{{XHTML}}}table" for a in stack)
                and not any(t in {f"{{{XHTML}}}td", f"{{{XHTML}}}th"} for t in same_table)
            ):
                raise ValueError("Nested table has no containing cell")
        if tag == f"{{{XHTML}}}template":
            raise ValueError("Template semantics unsupported in occurrence inventory")
        parent = stack[-1] if stack else None
        child_index = len(parent["children"]) + 1 if parent else 1
        node = {
            "tag": tag,
            "attributes": attributes,
            "namespaces": namespace_map,
            "parent": parent,
            "children": [],
            "start": byte,
            "start_end": byte + len(markup.encode("utf-8")),
            "self_closing": markup.rstrip().endswith("/>"),
            "location": {"line": position[0], "column": position[1]},
            "path": (parent["path"] if parent else "") + "/" + str(child_index),
        }
        if parent is not None:
            parent["children"].append(node)
        nodes.append(node)
        stack.append(node)

    def end(name):
        node = stack.pop()
        node["end"] = (
            node["start_end"]
            if node["self_closing"]
            else raw.index(b">", parser.CurrentByteIndex) + 1
        )
        if node["end"] < node["start_end"]:
            raise ValueError("Invalid source element range")

    parser.XmlDeclHandler = declaration
    parser.StartDoctypeDeclHandler = reject_dtd
    parser.StartNamespaceDeclHandler = lambda prefix, uri: namespaces.append(
        (prefix or "", uri or "")
    )
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(raw, True)
    if len(nodes) != len(starts) or stack:
        raise ValueError("XML/HTML event inventory differs")
    raw_text = {
        f"{{{XHTML}}}{name}"
        for name in (
            "script",
            "style",
            "title",
            "textarea",
            "xmp",
            "iframe",
            "noembed",
            "noframes",
            "noscript",
            "plaintext",
        )
    }
    if any(node["tag"] in raw_text and node["children"] for node in nodes):
        raise ValueError("Element content in an unsupported HTML raw-text context")
    if any(
        node["tag"] == f"{{{IX}}}tuple"
        or node["tag"].startswith("{http://www.xbrl.org/2008/inlineXBRL}")
        for node in nodes
    ):
        raise ValueError("Unsupported Inline XBRL tuple or namespace version")
    return nodes


def occurrence_sidecar(raw, table_sidecar_raw):
    """Account for source facts and continuations without accepting financial values."""
    table_sidecar = json.loads(table_sidecar_raw)
    if table_sidecar["version"] not in {"native-html-tables-v2", "native-html-tables-v3"}:
        raise ValueError("Unsupported table sidecar version")
    if table_sidecar["original_sha256"] != _sha(raw):
        raise ValueError("Original/table-sidecar hash mismatch")
    nodes = _source_nodes(raw)
    by_id = {}
    for node in nodes:
        identifier = node["attributes"].get("id")
        if identifier is not None:
            if not identifier or identifier in by_id:
                raise ValueError("Empty or duplicate source ID")
            by_id[identifier] = node
    tables, cells = {}, {}
    table_ids, cell_ids = set(), set()

    def key(location):
        return location["line"], location["column"]

    for table in table_sidecar["tables"]:
        location = key(table["original_location"])
        if location in tables or table["id"] in table_ids:
            raise ValueError("Ambiguous table position")
        tables[location] = table["id"]
        table_ids.add(table["id"])
        for row in table["rows"]:
            for cell in row["cells"]:
                position = key(cell["original_location"])
                if position in cells or cell["id"] in cell_ids:
                    raise ValueError("Ambiguous cell position")
                cells[position] = (table["id"], cell["id"])
                cell_ids.add(cell["id"])

    def ancestors(node):
        result = []
        parent = node["parent"]
        while parent is not None:
            result.append(parent)
            parent = parent["parent"]
        return result

    def locator(node):
        return {
            "element_path": node["path"],
            "start_location": node["location"],
            "byte_start": node["start"],
            "byte_end": node["end"],
            "source_bytes_sha256": _sha(raw[node["start"] : node["end"]]),
        }

    def source_record(node):
        chain = ancestors(node)
        cell = next(
            (parent for parent in chain if parent["tag"] in {f"{{{XHTML}}}td", f"{{{XHTML}}}th"}),
            None,
        )
        table = next((parent for parent in chain if parent["tag"] == f"{{{XHTML}}}table"), None)
        hidden = [
            parent
            for parent in [node, *chain]
            if parent["tag"] == f"{{{IX}}}hidden"
            or _is_explicitly_hidden(parent["attributes"].items())
        ]
        mapping = None
        if cell is not None and table is not None:
            match = cells.get(key(cell["location"]))
            table_id = tables.get(key(table["location"]))
            if match and table_id != match[0]:
                raise ValueError("Nearest table/cell mapping disagrees")
            if match:
                mapping = {"table_id": match[0], "cell_id": match[1]}
        disposition = (
            "explicitly_hidden"
            if hidden
            else (
                "cell_mapped"
                if mapping
                else "cell_unmapped"
                if cell is not None
                else "table_without_cell"
                if table is not None
                else "outside_table"
            )
        )
        return {
            "id": node["attributes"].get("id"),
            "expanded_element_name": node["tag"],
            **locator(node),
            "ancestor_fact_ids": [
                p["attributes"].get("id") for p in chain if p["tag"] in FACT_TAGS
            ],
            "ancestor_continuation_ids": [
                p["attributes"].get("id") for p in chain if p["tag"] == CONTINUATION
            ],
            "explicit_hiding_evidence": [
                {
                    "tag": p["tag"],
                    "element_path": p["path"],
                    "attributes": {
                        k: v for k, v in p["attributes"].items() if k in {"hidden", "style"}
                    },
                }
                for p in hidden
            ],
            "ix_hidden": any(p["tag"] == f"{{{IX}}}hidden" for p in [node, *chain]),
            "nearest_cell": locator(cell) if cell is not None else None,
            "nearest_table": locator(table) if table is not None else None,
            "table_mapping": mapping,
            "source_disposition": disposition,
            "continued_at": node["attributes"].get("continuedAt"),
        }

    incoming = {}
    for node in nodes:
        target = node["attributes"].get("continuedAt")
        if target is not None and node["tag"].startswith(f"{{{IX}}}"):
            if node["tag"] not in {f"{{{IX}}}nonNumeric", CONTINUATION} or not target.strip():
                raise ValueError("continuedAt on unsupported Inline XBRL source or empty target")
        if target and node["tag"] in {f"{{{IX}}}nonNumeric", CONTINUATION}:
            if target in incoming:
                raise ValueError("Shared continuation target")
            incoming[target] = node
    facts, continuations = [], []
    for node in nodes:
        if node["tag"] not in FACT_TAGS | {CONTINUATION}:
            continue
        if not node["attributes"].get("id"):
            raise ValueError("Fact and continuation source IDs required")
        record = source_record(node)
        target = node["attributes"].get("continuedAt")
        fragments, seen = [], {record["id"]}
        chain_nodes = [node]
        while target:
            if target in seen or target not in by_id or by_id[target]["tag"] != CONTINUATION:
                raise ValueError("Missing, cyclic or non-continuation target")
            seen.add(target)
            fragment = by_id[target]
            for prior in chain_nodes:
                if (
                    prior["start"] <= fragment["start"] < prior["end"]
                    or fragment["start"] <= prior["start"] < fragment["end"]
                ):
                    raise ValueError("Nested members of continuation chain")
            chain_nodes.append(fragment)
            fragments.append({"id": target, **locator(fragment)})
            target = fragment["attributes"].get("continuedAt")
        record["continuation_fragments"] = fragments
        if node["tag"] in FACT_TAGS:
            name = node["attributes"].get("name", "")
            prefix, separator, local = name.partition(":")
            namespace = node["namespaces"].get(prefix if separator else "")
            if not name or namespace is None or ":" in local or any(c.isspace() for c in name):
                raise ValueError("Unresolved reported concept QName")
            record.update(
                reported_concept=name,
                expanded_concept=f"{{{namespace}}}{local if separator else prefix}",
                context_ref=node["attributes"].get("contextRef"),
                unit_ref=node["attributes"].get("unitRef"),
            )
            facts.append(record)
        else:
            record["referenced_by"] = incoming.get(record["id"], {}).get("attributes", {}).get("id")
            record["continuation_issues"] = [] if record["id"] in incoming else ["orphan"]
            if record["ix_hidden"]:
                record["continuation_issues"].append("inside_ix_hidden")
            continuations.append(record)
    return {
        "version": "inline-xbrl-source-occurrences-v1",
        "original_sha256": _sha(raw),
        "table_sidecar_sha256": _sha(table_sidecar_raw),
        "table_sidecar_version": table_sidecar["version"],
        "aligned_element_count": len(nodes),
        "facts": facts,
        "continuations": continuations,
        "limitations": [
            "Original source positions and byte ranges, not rendered visibility.",
            "Concept namespace expansion does not validate taxonomy or values.",
            "Physical ancestry and continuedAt assembly are separate relations.",
            "No-cell text blocks may contain tables; descendant cells are not assigned as nearest ancestors.",
            "Only explicit hiding is recorded; external styles and browser layout remain unresolved.",
        ],
    }


def main():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("tables", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw, table_raw = args.original.read_bytes(), args.tables.read_bytes()
    result = occurrence_sidecar(raw, table_raw)
    if args.original.read_bytes() != raw or args.tables.read_bytes() != table_raw:
        raise ValueError("Source inputs changed")
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
