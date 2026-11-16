"""Chat-specific tools: workbook reads, cell citations, and edit proposals.

Extends the base Sources without changing it. Proposals are recorded for human
approval; nothing here writes a file.
"""

import math
import re

from provenance.model import INSTRUCTIONS
from provenance.sources import TOOL_SCHEMAS, Sources, function
from provenance.web.workbook import format_address, parse_range

READ_LIMIT = 200
CONTEXT_LIMIT = 400
PROPOSAL_LIMIT = 10
TEXT_LIMIT = 500
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_NUMBERISH = re.compile(
    r"[\s$€£¥(+-]*\d[\d,.\s]*[)%]?\s*(k|m|mm|bn|b|million|billion|thousand)?\s*", re.IGNORECASE
)


def _balanced(formula):
    depth, quoted = 0, False
    for char in formula:
        if char == '"':
            quoted = not quoted
        elif not quoted and char == "(":
            depth += 1
        elif not quoted and char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not quoted


CHAT_ADDENDUM = """
Conversation and workbook rules for this chat:
- The user message may begin with a research context block and earlier turns. Earlier answers are not evidence: re-read any source lines you cite in this turn. Carried locators show where to read.
- If a workbook is attached, read_workbook_range returns cells from that immutable snapshot. Cite cells with source_id "workbook:<snapshot_id>", locator "Sheet!B5" or "Sheet!A1:C3", and a quote equal to a cell's displayed value or formula. Cells listed in the context block count as read.
- Workbook inputs are analyst assumptions unless the workbook says otherwise; never present them as reported facts.
- Use propose_cell_edit only when the user asks for changes or clearly asks whether an input should be updated. Each proposal needs a short rationale and citations to evidence you already read. Proposals are not applied: never say the workbook was changed; say the analyst can review and approve them.
"""

CHAT_INSTRUCTIONS = INSTRUCTIONS + CHAT_ADDENDUM

_CITATION = {
    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "locator": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["source_id", "locator", "quote"],
    "additionalProperties": False,
}

WORKBOOK_TOOL_SCHEMAS = [
    function(
        "read_workbook_range",
        "Read up to 200 cells from the attached workbook snapshot. Returns displayed values "
        "and formulas. Cite cells as source_id workbook:<snapshot_id>, locator Sheet!A1.",
        {
            "sheet": {"type": "string"},
            "range": {"type": "string", "description": "A1 or A1:C10"},
        },
    ),
    function(
        "propose_cell_edit",
        "Propose (never apply) a change to one workbook cell for the analyst to approve. "
        "Citations must point to evidence already returned by read_source or read_workbook_range.",
        {
            "sheet": {"type": "string"},
            "cell": {"type": "string", "description": "One cell, e.g. B7"},
            "new_content": {
                "type": ["number", "string"],
                "description": "New value, or a formula starting with =",
            },
            "rationale": {"type": "string", "maxLength": TEXT_LIMIT},
            "citations": {"type": "array", "minItems": 1, "items": _CITATION},
        },
    ),
]


def _split_locator(locator):
    sheet, separator, rng = locator.rpartition("!")
    if not separator or not sheet:
        raise ValueError("Workbook locator must look like Sheet!B5 or Sheet!A1:C3")
    if len(sheet) > 1 and sheet[0] == sheet[-1] == "'":
        sheet = sheet[1:-1]
    return sheet, rng


def _normalize(text):
    return " ".join(text.split())


def _content(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("new_content must be a number, text, or a formula starting with =")
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("new_content must be finite")
        return value
    text = value.strip()
    if not text or len(text) > TEXT_LIMIT:
        raise ValueError(f"new_content must contain 1–{TEXT_LIMIT} characters")
    plain = text.replace(",", "")
    if _NUMBER.fullmatch(plain):
        number = float(plain)
        return int(number) if number.is_integer() and "." not in plain else number
    if text.startswith("="):
        if len(text) < 2 or not _balanced(text):
            raise ValueError("Formula has unbalanced parentheses or quotes")
        return text
    if _NUMBERISH.fullmatch(text):
        raise ValueError("Write numbers plainly in the cell's units, e.g. 1661.5, not $1,661.5M")
    return text


class ChatSources(Sources):
    def __init__(self, directory, *, snapshot=None, preread_range=None, **kwargs):
        super().__init__(directory, **kwargs)
        self.snapshot = snapshot
        self.proposals = []
        self.preread = set()
        if snapshot and preread_range:
            sheet, rng = preread_range
            self.preread = {
                f"{sheet}!{cell['address']}" for cell in snapshot.cells(sheet, rng, CONTEXT_LIMIT)
            }
        self.tool_schemas = TOOL_SCHEMAS + WORKBOOK_TOOL_SCHEMAS if snapshot else TOOL_SCHEMAS

    @property
    def workbook_id(self):
        return f"workbook:{self.snapshot.snapshot_id}" if self.snapshot else None

    def call(self, name, args, timeout):
        if name not in ("read_workbook_range", "propose_cell_edit"):
            return super().call(name, args, timeout)
        try:
            if not self.snapshot:
                raise ValueError("No workbook is attached to this conversation")
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            if name == "read_workbook_range" and set(args) == {"sheet", "range"}:
                return self._read_workbook(args["sheet"], args["range"])
            fields = {"sheet", "cell", "new_content", "rationale", "citations"}
            if name == "propose_cell_edit" and set(args) == fields:
                return self._propose(args)
            raise ValueError("Unknown tool or invalid argument fields")
        except ValueError as exc:
            return {"error": str(exc)}

    def _read_workbook(self, sheet, rng):
        if not isinstance(sheet, str) or not isinstance(rng, str):
            raise ValueError("sheet and range must be strings")
        cells = self.snapshot.cells(sheet, rng, READ_LIMIT)
        self.seen.setdefault(self.workbook_id, set()).update(
            f"{sheet}!{cell['address']}" for cell in cells
        )
        return {
            "snapshot_id": self.snapshot.snapshot_id,
            "source_id": self.workbook_id,
            "filename": self.snapshot.filename,
            "sheet": sheet,
            "range": rng,
            "cells": cells,
            "note": "Immutable uploaded snapshot. Inputs are analyst values unless labeled.",
        }

    def _propose(self, args):
        sheet, cell = args["sheet"], args["cell"]
        if not isinstance(sheet, str) or not isinstance(cell, str):
            raise ValueError("sheet and cell must be strings")
        row, col, row2, col2 = parse_range(cell)
        if (row, col) != (row2, col2):
            raise ValueError("propose_cell_edit targets exactly one cell")
        if row > 10000 or col > 200:
            raise ValueError("Cell is outside the supported workbook area")
        old = self.snapshot.cell(sheet, row, col)
        rationale = args["rationale"]
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > TEXT_LIMIT:
            raise ValueError(f"rationale must contain 1–{TEXT_LIMIT} characters")
        content = _content(args["new_content"])
        citations = args["citations"]
        if not isinstance(citations, list) or not citations:
            raise ValueError("Each proposal needs at least one citation to read evidence")
        for citation in citations:
            self.check_citation(citation)
        address = format_address(row, col)
        existing = next(
            (p for p in self.proposals if (p["sheet"], p["cell"]) == (sheet, address)), None
        )
        if existing is None and len(self.proposals) >= PROPOSAL_LIMIT:
            raise ValueError(f"Proposal limit ({PROPOSAL_LIMIT} per turn) reached")
        proposal = {
            "proposal_id": existing["proposal_id"] if existing else f"P{len(self.proposals) + 1}",
            "sheet": sheet,
            "cell": address,
            "new_content": content,
            "rationale": rationale.strip(),
            "citations": citations,
            "old_display": old["display"],
            "old_formula": old["formula"],
        }
        if existing:
            self.proposals[self.proposals.index(existing)] = proposal
        else:
            self.proposals.append(proposal)
        return {
            "proposal_id": proposal["proposal_id"],
            "status": "pending_human_approval",
            "cell": f"{sheet}!{address}",
            "old_display": old["display"],
            "note": "Nothing was written. The analyst reviews and approves proposals separately.",
        }

    def check_citation(self, citation):
        source_id = citation.get("source_id") if isinstance(citation, dict) else None
        if not (isinstance(source_id, str) and source_id.startswith("workbook:")):
            return super().check_citation(citation)
        if set(citation) != {"source_id", "locator", "quote"}:
            raise ValueError("Citation requires source_id, locator, quote")
        locator, quote = citation["locator"], citation["quote"]
        if not isinstance(locator, str) or not isinstance(quote, str) or not quote.strip():
            raise ValueError("Citation fields must be nonempty strings")
        if not self.snapshot or source_id != self.workbook_id:
            raise ValueError("Citation refers to an unknown workbook snapshot")
        sheet, rng = _split_locator(locator)
        cells = self.snapshot.cells(sheet, rng, READ_LIMIT)
        read = self.seen.get(self.workbook_id, set()) | self.preread
        if any(f"{sheet}!{cell['address']}" not in read for cell in cells):
            raise ValueError("Citation refers to unread workbook cells")
        wanted = _normalize(quote)
        if not any(
            wanted
            in {
                _normalize(cell["display"]),
                _normalize(cell["value"]),
                _normalize(cell["formula"] or ""),
            }
            for cell in cells
        ):
            raise ValueError(
                "Workbook quote must equal one cited cell's displayed value, raw value, or formula"
            )


def _claim_line(claim):
    locators = ", ".join(
        f"{c.get('source_id')} {c.get('locator')}" for c in claim.get("citations", [])
    )
    return (
        f"{claim.get('key')} = {claim.get('value')} {claim.get('unit')} "
        f"({claim.get('period')}) [{locators}]"
    )


def compose_question(question, *, corpus_label, cutoff, history, snapshot, context):
    """Build the user message: explicit research context, carried turns, then the question."""
    lines = [
        "Research context (set by the analyst; not evidence):",
        f"- Evidence set: {corpus_label}; information cutoff {cutoff}.",
    ]
    if snapshot:
        sheets = ", ".join(
            f"{s['name']} ({s['max_row']} rows x {s['max_col']} cols)" for s in snapshot.sheets
        )
        lines.append(
            f'- Workbook attached: workbook:{snapshot.snapshot_id} ("{snapshot.filename}"); '
            f"sheets: {sheets}."
        )
        if context:
            sheet, rng = context["sheet"], context["range"]
            lines.append(f"- Selected range {sheet}!{rng} (these cells count as read):")
            for cell in snapshot.cells(sheet, rng, CONTEXT_LIMIT):
                if not cell["display"] and not cell["formula"]:
                    continue
                formula = f" [formula {cell['formula']}]" if cell["formula"] else ""
                lines.append(f"  {sheet}!{cell['address']} = {cell['display']}{formula}")
    carried = history[-3:]
    if carried:
        lines += ["", "Earlier in this conversation (not evidence; re-read sources before citing):"]
        for number, turn in enumerate(carried, 1):
            lines.append(f"Q{number}: {turn['question']}")
            answer = turn.get("answer")
            if not answer:
                lines.append(f"A{number} ({turn.get('status')}): no validated answer.")
                continue
            lines.append(f"A{number} ({turn.get('status')}): {answer.get('answer', '')}")
            for claim in answer.get("claims", []):
                lines.append(f"  Claim: {_claim_line(claim)}")
    lines += ["", f"Current question: {question}"]
    return "\n".join(lines)
