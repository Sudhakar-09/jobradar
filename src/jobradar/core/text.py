"""Turn untrusted HTML from job sources into plain text (stdlib only; no rendering, no scripts)."""

import html
import re
from html.parser import HTMLParser
from typing import Final

_BLOCK_TAGS: Final = frozenset(
    {"p", "div", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "section", "table"}
)  # separated by a blank line
_LINE_TAGS: Final = frozenset({"li", "br", "tr"})  # start a new line, no blank line
_SKIP_TAGS: Final = frozenset({"script", "style", "noscript", "template", "head"})
_SPACES: Final = re.compile(r"[ \t\f\v\r]+")
_BLANK_LINES: Final = re.compile(r"\n\s*\n+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs  # attributes (links, handlers) are never kept
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS or tag in _LINE_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(markup: str, *, escaped: bool = False) -> str:
    """Return the readable text of an HTML fragment.

    Args:
        markup: HTML from a job source (untrusted).
        escaped: The HTML itself is entity-escaped (Greenhouse ``content``) and must be
            unescaped once before parsing.

    Returns:
        Plain text with tags, scripts and styles removed, whitespace collapsed and paragraphs
        separated by a blank line.
    """
    extractor = _TextExtractor()
    extractor.feed(html.unescape(markup) if escaped else markup)
    extractor.close()
    lines = (_SPACES.sub(" ", line).strip() for line in "".join(extractor.parts).split("\n"))
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
