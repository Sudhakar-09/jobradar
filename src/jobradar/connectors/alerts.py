"""Job-alert email parsers (US-2.5): turn alert emails into raw jobs without fetching anything.

Each board is a configured `LinkCardParser` (`config/alert_senders.yaml`): job links are found by
URL pattern (after unwrapping tracking redirects), and the job card around each link supplies the
title, company and location. Parsing is pure; email bodies are never stored or logged.
"""

import re
from email.utils import parseaddr
from pathlib import Path
from typing import Final, Literal
from urllib.parse import parse_qs, unquote, urlsplit

import yaml
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from jobradar.connectors.schemas import InboundMessage, RawJob

MAX_CARD_DEPTH: Final = 5  # how far up from a job link to look for the job card
REDIRECT_PARAMS: Final = ("url", "u", "redirect", "redirect_url", "target", "dest", "q")
NOISE_LINES: Final = frozenset(
    {
        "apply",
        "apply now",
        "easy apply",
        "view job",
        "view jobs",
        "view details",
        "see job",
        "see all jobs",
        "actively recruiting",
        "promoted",
        "new",
        "save",
        "be an early applicant",
        "quick apply",
        "recommended",
        "featured",
    }
)
_SEPARATORS: Final = re.compile(r"\s+[·|•\u2013-]\s+")  # middle dot, bar, bullet, en dash, hyphen
_COMPANY_AND_LOCATION: Final = 2  # parts of a "Company · City" line


CardLine = Literal["company", "location", "skip"]


def _default_card_lines() -> list[CardLine]:
    return ["company", "location"]


class ParserConfig(BaseModel):
    """One board in `config/alert_senders.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    markets: list[str]
    sender_addresses: list[str] = Field(min_length=1)
    sender_domains: list[str] = Field(min_length=1)
    job_url: str
    canonical_url: str
    # Order of the text lines under a job title in this board's cards; "skip" ignores a line.
    card_lines: list[CardLine] = Field(default_factory=_default_card_lines)


class AlertSendersFile(BaseModel):
    """`config/alert_senders.yaml`."""

    model_config = ConfigDict(extra="forbid")

    parsers: dict[str, ParserConfig]


def load_alert_senders(path: Path) -> AlertSendersFile:
    """Load and validate the alert sender configuration; every pattern needs an ``id`` group."""
    senders = AlertSendersFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    for code, config in senders.parsers.items():
        if "id" not in re.compile(config.job_url).groupindex:
            raise ValueError(f"{code}: job_url needs a named group 'id'")
    return senders


def sender_domain(sender: str) -> str:
    """Domain of a From header, lower-cased ('' if there is none)."""
    address = parseaddr(sender)[1]
    return address.rpartition("@")[2].lower() if "@" in address else ""


def unwrap_tracking(href: str) -> str:
    """Follow tracking redirects that carry the real link in a query parameter (one level)."""
    query = parse_qs(urlsplit(href).query)
    for name in REDIRECT_PARAMS:
        for value in query.get(name, []):
            candidate = unquote(value)
            parts = urlsplit(candidate)
            if parts.scheme == "https" and parts.netloc:
                return candidate
    return href


def _is_noise(line: str) -> bool:
    return line.casefold().strip(" .:!") in NOISE_LINES or len(line) <= 1


class LinkCardParser:
    """Parses one board's alert emails by job link pattern and surrounding card text."""

    def __init__(self, code: str, config: ParserConfig) -> None:
        """Compile the board's job URL pattern."""
        self.code = code
        self.source = f"alert:{code}"
        self.config = config
        self._pattern = re.compile(config.job_url)
        self._domains = tuple(domain.lower() for domain in config.sender_domains)

    def matches(self, message: InboundMessage) -> bool:
        """Whether the message comes from one of this board's sender domains."""
        domain = sender_domain(message.sender)
        return any(domain == d or domain.endswith(f".{d}") for d in self._domains)

    def parse(self, message: InboundMessage) -> tuple[list[RawJob], int]:
        """Return the jobs in an alert email and the number of job links that could not be used."""
        if message.html:
            soup = BeautifulSoup(message.html, "html.parser")
            for hidden in soup(["script", "style", "head", "title"]):
                hidden.decompose()
            return self._parse_links(soup)
        return [], 0

    def _canonical(self, href: str) -> tuple[str, str] | None:
        match = self._pattern.match(unwrap_tracking(href.strip()))
        if match is None:
            return None
        groups = {key: value or "" for key, value in match.groupdict().items()}
        return groups["id"], self.config.canonical_url.format(**groups)

    def _parse_links(self, soup: BeautifulSoup) -> tuple[list[RawJob], int]:
        cards: dict[str, tuple[str, Tag]] = {}
        for anchor in soup.find_all("a", href=True):
            found = self._canonical(str(anchor["href"]))
            if found is None:
                continue
            job_id, url = found
            title = anchor.get_text(" ", strip=True)
            if job_id not in cards or (title and not cards[job_id][1].get_text(strip=True)):
                cards[job_id] = (url, anchor)
        jobs: list[RawJob] = []
        invalid = 0
        for job_id, (url, anchor) in cards.items():
            job = self._job_from_card(job_id, url, anchor)
            if job is None:
                invalid += 1
            else:
                jobs.append(job)
        return jobs, invalid

    def _job_from_card(self, job_id: str, url: str, anchor: Tag) -> RawJob | None:
        title = anchor.get_text(" ", strip=True)
        details = _card_lines(anchor, title)
        company, location = _company_and_location(details, self.config.card_lines)
        try:
            link = HttpUrl(url)
            return RawJob(
                source=self.source,
                source_job_id=job_id,
                company_name=company or "",
                title=title,
                url=link,
                apply_url=link,
                location_raw=location,
                raw={"parser": self.code, "id": job_id},
            )
        except ValidationError:
            return None


def _card_lines(anchor: Tag, title: str) -> list[str]:
    """Text lines of the smallest enclosing block that has more than the title in it."""
    node: Tag = anchor
    for _ in range(MAX_CARD_DEPTH):
        parent = node.parent
        if not isinstance(parent, Tag):
            break
        node = parent
        lines = [line for line in node.stripped_strings if not _is_noise(line)]
        if title in lines:
            after = lines[lines.index(title) + 1 :]
            if after:
                return after
    return []


def _company_and_location(lines: list[str], roles: list[CardLine]) -> tuple[str | None, str | None]:
    """Company and location from the lines after the title.

    A first line like "Company · City" holds both; otherwise lines map to ``roles`` in order.
    """
    if not lines:
        return None, None
    first = _SEPARATORS.split(lines[0], maxsplit=1)
    if len(first) == _COMPANY_AND_LOCATION:
        return first[0].strip(), first[1].strip()
    by_role = dict(zip(roles, lines, strict=False))
    return by_role.get("company"), by_role.get("location")


def build_parsers(senders: AlertSendersFile) -> list[LinkCardParser]:
    """One parser per configured board, in file order."""
    return [LinkCardParser(code, config) for code, config in senders.parsers.items()]


def pick_parser(parsers: list[LinkCardParser], message: InboundMessage) -> LinkCardParser | None:
    """The first parser whose sender domains match the message, if any."""
    return next((parser for parser in parsers if parser.matches(message)), None)
