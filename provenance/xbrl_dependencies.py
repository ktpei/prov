"""Local XML reference inventory for explicit XBRL dependency acquisition.

This module neither downloads documents nor claims a complete/valid DTS.
"""

import hashlib
from urllib.parse import urldefrag, urljoin, urlsplit
from xml.etree import ElementTree

XS = "http://www.w3.org/2001/XMLSchema"
LINK = "http://www.xbrl.org/2003/linkbase"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"
XHTML = "http://www.w3.org/1999/xhtml"


class _NoDTD(ElementTree.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("DTD is unsupported in dependency inventory")


def _http_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Dependency locations require absolute HTTP(S) URLs without credentials")
    return value


def inspect_xml_references(raw, *, canonical_url, delivery_url):
    """Preserve reference occurrences and independently resolve both source bases.

    Expanded element names and XML Base are respected. HTML base elements are
    rejected rather than silently applying browser semantics to an XML document.
    Returned URLs are candidates, not evidence of remote availability or identity.
    """
    _http_url(canonical_url)
    _http_url(delivery_url)
    root = ElementTree.fromstring(raw, parser=ElementTree.XMLParser(target=_NoDTD()))
    if root.find(f".//{{{XHTML}}}base") is not None:
        raise ValueError("HTML base is unsupported in XML dependency inventory")
    references = []

    def visit(element, canonical_base, delivery_base, path):
        xml_base = element.get(f"{{{XML}}}base")
        if xml_base is not None:
            canonical_base = _http_url(urljoin(canonical_base, xml_base))
            delivery_base = _http_url(urljoin(delivery_base, xml_base))
        kind = None
        if element.tag in {f"{{{XS}}}{name}" for name in ("import", "include", "redefine")}:
            kind = element.tag.removeprefix(f"{{{XS}}}")
            href = element.get("schemaLocation")
        elif element.tag in {
            f"{{{LINK}}}{name}"
            for name in ("schemaRef", "linkbaseRef", "roleRef", "arcroleRef", "loc")
        }:
            kind = element.tag.removeprefix(f"{{{LINK}}}")
            href = element.get(f"{{{XLINK}}}href")
        if kind:
            record = {"element_path": path, "kind": kind, "raw_reference": href}
            if kind == "import":
                record["expected_namespace"] = element.get("namespace")
            if href is None or not href.strip():
                record["status"] = "missing_location"
            else:
                canonical = _http_url(urljoin(canonical_base, href.strip()))
                delivery = _http_url(urljoin(delivery_base, href.strip()))
                canonical_document, canonical_fragment = urldefrag(canonical)
                delivery_document, delivery_fragment = urldefrag(delivery)
                record.update(
                    status="declared_reference",
                    canonical_url=canonical_document,
                    delivery_url=delivery_document,
                    canonical_fragment=canonical_fragment,
                    delivery_fragment=delivery_fragment,
                )
            references.append(record)
        for index, child in enumerate(element, 1):
            visit(child, canonical_base, delivery_base, f"{path}/{index}")

    visit(root, canonical_url, delivery_url, "/1")
    return {
        "version": "xbrl-dependency-reference-inventory-v1",
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_url": canonical_url,
        "delivery_url": delivery_url,
        "root_name": root.tag,
        "target_namespace": root.get("targetNamespace"),
        "references": references,
        "claim": "declared XML references only; DTS completeness and validity unverified",
    }
