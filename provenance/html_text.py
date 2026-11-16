"""Versioned native HTML text extraction with conservative explicit visibility.

This is not a browser or a computed-CSS implementation. Ambiguous hidden markup
fails closed; existing corpora and the legacy extractor are not rewritten.
"""

import re
from html.parser import HTMLParser

from provenance.table_structure import BLOCK_TAGS, SUPPRESSED_TAGS, VOID_TAGS, _is_explicitly_hidden

VERSION = "native-html-text-v2"


class DocumentHTMLV2(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.lines = []
        self.locations = []
        self.parts = []
        self.section = "Document"
        self.heading = False

    def flush(self):
        text = " ".join("".join(self.parts).split())
        self.parts = []
        if text:
            if self.heading:
                self.section = text[:300]
            self.lines.append(text)
            self.locations.append({"section": self.section})

    def _in_row(self):
        return any(tag == "tr" and not hidden for tag, hidden in self.stack)

    def _end_visible(self, tag):
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.heading = False
        elif tag in {"tr", "table"}:
            self.flush()
        elif tag in BLOCK_TAGS:
            if self.heading or self._in_row():
                self.parts.append(" ")
            else:
                self.flush()

    def _pop_from(self, index):
        while len(self.stack) > index:
            tag, hidden = self.stack[-1]
            if not hidden:
                self._end_visible(tag)
            self.stack.pop()

    def _implicit_table_end(self, tags):
        # A nested table cannot implicitly close its parent's cell or row.
        for index in range(len(self.stack) - 1, -1, -1):
            tag, _ = self.stack[index]
            if tag == "table":
                return
            if tag in tags:
                if any(
                    hidden and name not in {"td", "th", "tr"}
                    for name, hidden in self.stack[index + 1 :]
                ):
                    raise ValueError("Table closure crosses unfinished suppressed HTML")
                self._pop_from(index)
                return

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self._implicit_table_end({"td", "th"})
        elif tag == "tr":
            self._implicit_table_end({"tr"})
        hidden = (
            bool(self.stack and self.stack[-1][1])
            or tag in SUPPRESSED_TAGS | {"template"}
            or _is_explicitly_hidden(attrs)
        )
        if not hidden:
            if re.fullmatch(r"h[1-6]", tag):
                self.flush()
                self.heading = True
            elif tag in {"tr", "table"}:
                self.flush()
            elif tag in {"td", "th"}:
                if self.parts:
                    self.parts.append(" | ")
            elif tag in BLOCK_TAGS or tag == "br":
                if self.heading or self._in_row():
                    self.parts.append(" ")
                else:
                    self.flush()
        if tag not in VOID_TAGS:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag == "tr":
            self._implicit_table_end({"td", "th"})
        elif tag == "table":
            self._implicit_table_end({"tr"})
        indices = [index for index, (name, _) in enumerate(self.stack) if name == tag]
        if not indices:
            if self.stack and self.stack[-1][1]:
                raise ValueError("Unmatched closing tag inside suppressed HTML")
            return
        index = indices[-1]
        if any(hidden for _, hidden in self.stack[index + 1 :]):
            raise ValueError("Closing tag crosses unfinished suppressed HTML")
        self._pop_from(index)

    def handle_startendtag(self, tag, attrs):
        hidden = (
            bool(self.stack and self.stack[-1][1])
            or tag in SUPPRESSED_TAGS | {"template"}
            or _is_explicitly_hidden(attrs)
        )
        if tag not in VOID_TAGS and ":" not in tag and tag not in {"td", "th"} and hidden:
            raise ValueError("Ambiguous hidden self-closing HTML element")
        # HTML non-void self-closing slashes do not end the element. XML names do.
        self.handle_starttag(tag, attrs)
        if ":" in tag:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(data)

    def close(self):
        super().close()
        if any(hidden for _, hidden in self.stack):
            raise ValueError("Unfinished suppressed HTML")
        self._pop_from(0)
        self.flush()
