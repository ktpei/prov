"""Experimental typed records from a validated Arelle model and original-source sidecar."""

import hashlib
import re
from datetime import datetime, timedelta
from decimal import Decimal

INSTANCE = "http://www.xbrl.org/2003/instance"
ENUM2 = "http://xbrl.org/2020/extensible-enumerations-2.0"


def expanded(qname):
    return f"{{{qname.namespaceURI}}}{qname.localName}"


def checked_boundary(text, end_of_day):
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})(T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?", text
    )
    if match is None:
        raise ValueError("Unsupported lexical context boundary")
    date, time, zone = match.groups()
    result = datetime.fromisoformat(date + (time or "T00:00:00") + (zone or ""))
    if time is None and end_of_day:
        result += timedelta(days=1)
    return result.isoformat()


def typed_value(value, *, nil=False, enumeration_set=False):
    """Preserve parsed values; source lexicals remain separate authoritative evidence."""
    if nil:
        if value is not None:
            raise ValueError("Nil fact has a non-null typed value")
        return {"kind": "nil", "value": None}
    if isinstance(value, bool):
        return {"kind": "boolean", "value": value}
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite numeric value unsupported")
        return {"kind": "decimal", "value": str(value)}
    if isinstance(value, int):
        return {"kind": "integer", "value": str(value)}
    if isinstance(value, str):
        return {"kind": "string", "value": value}
    if isinstance(value, datetime):
        offset = value.utcoffset()
        return {
            "kind": "date_time",
            "date_only": bool(getattr(value, "dateOnly", False)),
            **{
                part: getattr(value, part)
                for part in ("year", "month", "day", "hour", "minute", "second", "microsecond")
            },
            "timezone_offset_seconds": None if offset is None else int(offset.total_seconds()),
        }
    if value is None:
        raise ValueError("Non-nil null typed value unsupported")
    from arelle.ModelValue import QName, gMonthDay, gYear

    if isinstance(value, QName):
        return {"kind": "qname", "namespace_uri": value.namespaceURI, "local_name": value.localName}
    if isinstance(value, list):
        if not enumeration_set or not all(isinstance(member, QName) for member in value):
            raise ValueError("Only schema-confirmed enumeration-set lists are supported")
        return {
            "kind": "enumeration_set",
            "members": [typed_value(member) for member in value],
            "order": "observed_order_preserved; schema_declares_set_semantics",
        }
    if isinstance(value, (gMonthDay, gYear)):
        offset = value.tzinfo.utcoffset(None) if value.tzinfo is not None else None
        parts = (
            {"year": str(value.year)}
            if isinstance(value, gYear)
            else {"month": value.month, "day": value.day}
        )
        return {
            "kind": type(value).__name__,
            **parts,
            "timezone_offset_seconds": None if offset is None else int(offset.total_seconds()),
        }
    raise ValueError(f"Unsupported typed value class: {type(value).__name__}")


def verified_occurrences(raw, occurrences, table_sidecar_raw):
    """Rebuild geometry; never trust supplied spans, hashes, ancestry or cell joins."""
    from provenance.xbrl_occurrences import occurrence_sidecar

    rebuilt = occurrence_sidecar(raw, table_sidecar_raw)
    supplied = {key: occurrences.get(key) for key in rebuilt}
    supplied["facts"] = [
        {
            key: value
            for key, value in fact.items()
            if key not in {"runtime_schema_validation_state", "runtime_source_identity_match"}
        }
        for fact in occurrences["facts"]
    ]
    if supplied != rebuilt:
        raise ValueError("Source occurrence geometry differs from original")
    return rebuilt


def build_fact_sidecar(model, raw, occurrences, document_hashes, table_sidecar_raw):
    """Serialize one already validated model; validation errors reject the export."""
    from arelle import XbrlConst
    from arelle.ModelValue import qname
    from arelle.ValidateDuplicateFacts import getDuplicateFactSets
    from lxml import etree

    occurrences = verified_occurrences(raw, occurrences, table_sidecar_raw)
    original_hash = hashlib.sha256(raw).hexdigest()
    if (
        model.errors
        or document_hashes.get(model.modelDocument.uri) != original_hash
        or occurrences["original_sha256"] != original_hash
    ):
        raise ValueError("Invalid model or original source binding")
    original = etree.fromstring(
        raw, etree.XMLParser(recover=False, no_network=True, resolve_entities=False, load_dtd=False)
    )
    if original.getroottree().docinfo.doctype:
        raise ValueError("DTD unsupported")
    source_ids = {element.get("id"): element for element in original.iter() if element.get("id")}
    if len(source_ids) != sum(bool(element.get("id")) for element in original.iter()):
        raise ValueError("Duplicate original IDs")

    def source_locator(element, include_xml=False):
        path = element.getroottree().getpath(element)
        namespaces = {key: value for key, value in element.nsmap.items() if key}
        matches = original.getroottree().xpath(path, namespaces=namespaces)
        canonical = etree.tostring(element, method="c14n")
        if len(matches) != 1 or etree.tostring(matches[0], method="c14n") != canonical:
            raise ValueError("Parsed source element does not match original")
        result = {
            "xpath": path,
            "xpath_namespaces": namespaces,
            "canonical_xml_sha256": hashlib.sha256(canonical).hexdigest(),
        }
        if include_xml:
            result["canonical_xml"] = canonical.decode()
        return result

    contexts = {}
    for identifier, context in sorted(model.contexts.items()):
        period_node = source_ids[identifier].find(f"{{{INSTANCE}}}period")
        reported = {etree.QName(element).localname: element.text for element in period_node}
        if context.isInstantPeriod:
            expected = {"instant": checked_boundary(reported["instant"], True)}
            normalized = {"instant": context.instantDatetime.isoformat()}
        elif context.isStartEndPeriod:
            expected = {
                "start": checked_boundary(reported["startDate"], False),
                "end": checked_boundary(reported["endDate"], True),
            }
            normalized = {
                "start": context.startDatetime.isoformat(),
                "end": context.endDatetime.isoformat(),
            }
        elif context.isForeverPeriod:
            expected = normalized = {"forever": True}
        else:
            raise ValueError("Unsupported context period")
        if normalized != expected:
            raise ValueError(
                "Normalized context boundary differs from original lexical expectation"
            )
        dimensions = []
        for axis, dimension in sorted(
            context.qnameDims.items(), key=lambda pair: expanded(pair[0])
        ):
            record = {
                "axis": expanded(axis),
                "container": dimension.contextElement,
                "kind": "explicit" if dimension.isExplicit else "typed",
                "source": source_locator(dimension),
            }
            if dimension.isExplicit:
                record["member"] = expanded(dimension.memberQname)
            else:
                member = dimension.typedMember
                record["typed_member_name"] = member.tag
                record["typed_member_source"] = source_locator(member, include_xml=True)
                record["identity_claim"] = (
                    "original_XML_preserved; no custom semantic equality asserted"
                )
            dimensions.append(record)
        contexts[identifier] = {
            "entity": {
                "scheme": context.entityIdentifier[0],
                "identifier": context.entityIdentifier[1],
            },
            "reported_period": reported,
            "normalized_period": normalized,
            "boundary_verified": True,
            "reported_dimensions": dimensions,
            "source": source_locator(context),
            "non_dimensional_content": {
                location: [
                    source_locator(element, include_xml=True)
                    for element in context.nonDimValues(location)
                ]
                for location in ("segment", "scenario")
            },
        }
    units = {
        identifier: {
            "numerator": [expanded(measure) for measure in unit.measures[0]],
            "denominator": [expanded(measure) for measure in unit.measures[1]],
            "source": source_locator(unit),
        }
        for identifier, unit in sorted(model.units.items())
    }
    defaults = {}
    relationships = model.relationshipSet(XbrlConst.dimensionDefault).modelRelationships
    for axis, member in sorted(
        model.qnameDimensionDefaults.items(), key=lambda pair: expanded(pair[0])
    ):
        support = []
        for relationship in relationships:
            if (
                relationship.fromModelObject.qname != axis
                or relationship.toModelObject.qname != member
            ):
                continue
            arc = relationship.arcElement
            uri = arc.modelDocument.uri
            if uri not in document_hashes:
                raise ValueError("Default relationship document is unbound")
            support.append(
                {
                    "arcrole": relationship.arcrole,
                    "linkrole": relationship.linkrole,
                    "document_uri": uri,
                    "document_sha256": document_hashes[uri],
                    "arc_xpath": arc.getroottree().getpath(arc),
                    "arc_source_line": arc.sourceline,
                    "arc_canonical_xml_sha256": hashlib.sha256(
                        etree.tostring(arc, method="c14n")
                    ).hexdigest(),
                }
            )
        if not support:
            raise ValueError("Default member has no bound effective relationship")
        defaults[expanded(axis)] = {
            "member": expanded(member),
            "supporting_relationships": sorted(
                support,
                key=lambda item: (item["document_uri"], item["arc_xpath"], item["linkrole"]),
            ),
        }
    duplicate_groups = sorted(
        [
            {
                "occurrences": sorted(fact.id for fact in group.facts),
                "complete": group.areAllComplete,
                "consistent": group.areAllConsistent,
                "inconsistent": group.areAnyInconsistent,
            }
            for group in getDuplicateFactSets(model.facts, includeSingles=False)
        ],
        key=lambda group: group["occurrences"],
    )
    conflicts = {
        identifier
        for group in duplicate_groups
        if group["inconsistent"]
        for identifier in group["occurrences"]
    }
    locations = {fact["id"]: fact for fact in occurrences["facts"]}
    if len(locations) != len(occurrences["facts"]) or sorted(locations) != sorted(
        fact.id for fact in model.facts
    ):
        raise ValueError("Runtime/source occurrence inventory differs")
    facts = []
    for fact in sorted(model.facts, key=lambda fact: fact.id):
        if fact.concept is None or fact.xValid < 4:
            raise ValueError("Unresolved or invalid fact")
        location = locations[fact.id]
        source = source_locator(fact)
        if (
            location["expanded_concept"] != expanded(fact.qname)
            or location["context_ref"] != fact.contextID
            or location["unit_ref"] != fact.unitID
        ):
            raise ValueError("Fact/source reference binding differs")
        value = typed_value(
            fact.xValue,
            nil=fact.isNil,
            enumeration_set=fact.concept.instanceOfType(qname(ENUM2, "enumerationSetItemType")),
        )
        facts.append(
            {
                "id": fact.id,
                "concept": expanded(fact.qname),
                "resolved_type": expanded(fact.concept.typeQname),
                "base_xsd_type": fact.concept.baseXsdType,
                "arelle_value_class": type(fact.xValue).__name__,
                "value": value,
                "nil": fact.isNil,
                "numeric": fact.isNumeric,
                "validation_state": fact.xValid,
                "context_id": fact.contextID,
                "unit_id": fact.unitID,
                "reported_attributes": dict(source_ids[fact.id].attrib),
                "assembled_pretransform_text": fact.rawValue,
                "source_identity": source,
                "source_occurrence": location,
                "disposition": "quarantined_inconsistent_duplicate"
                if fact.id in conflicts
                else "schema_valid_source_bound",
                "financial_correctness": "unverified",
                "rendered_visibility": "unverified",
            }
        )
    if model.errors:
        raise ValueError("Model errors emerged during serialization")
    return {
        "version": "experimental-typed-xbrl-facts-v1",
        "original_sha256": original_hash,
        "canonical_url": model.modelDocument.uri,
        "facts": facts,
        "contexts": contexts,
        "units": units,
        "taxonomy_defaults": defaults,
        "duplicate_groups": duplicate_groups,
        "continuations": occurrences["continuations"],
        "normalization_note": "Typed numeric values already include sign/scale; do not rescale. Date-only context end/instant boundaries advance one day, while date-only fact values do not.",
        "default_scope_note": "Taxonomy defaults and reported dimensions are separate; no per-fact effective-default or consolidated-scope claim.",
        "lexical_note": "assembled_pretransform_text is Arelle assembly/whitespace/escape processing, not original source bytes. Parsed temporal precision is limited by the runtime; source fragments remain authoritative.",
    }
