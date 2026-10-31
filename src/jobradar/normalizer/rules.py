"""Pure normalization rules for ingest and dedupe (US-2.3). No I/O."""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

LEGAL_SUFFIXES: Final = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "ltd",
        "limited",
        "pvt",
        "private",
        "plc",
        "llp",
        "gmbh",
        "co",
        "corp",
        "corporation",
        "company",
        "fz",
        "fze",
        "fzco",
        "fzllc",
        "dmcc",
        "sa",
        "bv",
        "ag",
        "pte",
        "pty",
    }
)
_GENDER_MARKERS: Final = re.compile(r"\((?:m|w|f|d|x)(?:\s*/\s*(?:m|w|f|d|x))+\)", re.IGNORECASE)
_NON_WORD: Final = re.compile(r"[^\w\s]")
_SPACES: Final = re.compile(r"\s+")


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def _words(text: str) -> list[str]:
    # Dots are dropped (not spaced) so "L.L.C." and "Pvt." match "llc" and "pvt".
    return _SPACES.sub(" ", _NON_WORD.sub(" ", _fold(text).replace(".", ""))).strip().split()


def normalize_company(name: str) -> str:
    """Company name for matching: folded, punctuation and trailing legal suffixes removed."""
    words = _words(name)
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def normalize_title(title: str) -> str:
    """Job title for matching: folded, gender markers like (m/w/d) and punctuation removed."""
    return " ".join(_words(_GENDER_MARKERS.sub(" ", title)))


class LocationAliases(BaseModel):
    """`config/locations.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    countries: dict[str, list[str]]
    cities: dict[str, dict[str, list[str]]]


def load_location_aliases(path: Path) -> LocationAliases:
    """Load and validate the location alias file."""
    return LocationAliases.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True, slots=True)
class Location:
    """Country and city detected for a job (either may be unknown)."""

    country: str | None
    city: str | None


def _contains(haystack: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", haystack) is not None


def _find_city(text: str, aliases: LocationAliases, country: str | None) -> tuple[str, str] | None:
    for code, cities in aliases.cities.items():
        if country and code != country:
            continue
        for city, names in cities.items():
            if any(_contains(text, _fold(name)) for name in names):
                return code, city
    return None


def detect_location(
    location_raw: str | None,
    aliases: LocationAliases,
    *,
    country_hint: str | None = None,
    city_hint: str | None = None,
) -> Location:
    """Find the country (ISO code) and city of a job from its location text and source hints.

    Source-stated values win; otherwise known city names imply their country, then country
    names are matched. Unknown stays None — nothing is guessed.
    """
    text = _fold(" ".join(part for part in (location_raw, city_hint) if part))
    country = country_hint
    if country is None:
        country = next(
            (
                code
                for code, names in aliases.countries.items()
                if any(_contains(text, _fold(name)) for name in names)
            ),
            None,
        )
    found = _find_city(text, aliases, country)
    if found:
        return Location(country=country or found[0], city=found[1])
    return Location(country=country, city=city_hint.strip() if city_hint else None)


class LanguageEntry(BaseModel):
    """Phrases and common words of one language (`config/language_requirements.yaml`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    required_phrases: list[str]
    preferred_phrases: list[str]
    stopwords: list[str]
    title_words: list[str] = Field(default_factory=list)


class LanguageDetection(BaseModel):
    """Thresholds for telling which language a posting is written in."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_stopword_hits: int = Field(ge=1)
    min_share: float = Field(gt=0.5, le=1)


class LanguageRules(BaseModel):
    """`config/language_requirements.yaml`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detection: LanguageDetection
    languages: dict[str, LanguageEntry]


def load_language_rules(path: Path) -> LanguageRules:
    """Load and validate the language requirement phrases."""
    return LanguageRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True, slots=True)
class LanguageSignals:
    """What a posting says about languages: written in, required, merely preferred."""

    posting_language: str | None
    required: frozenset[str]
    preferred: frozenset[str]


_SENTENCE_END: Final = re.compile(r"[.!?;\n•·]+")  # sentence ends and bullets


def _phrase_in(words: str, phrases: list[str]) -> bool:
    return any(_contains(words, " ".join(_words(phrase))) for phrase in phrases)


def _title_language(title: str, rules: LanguageRules) -> str | None:
    words = set(_words(title))
    found = [
        code
        for code, entry in rules.languages.items()
        if words & {" ".join(_words(word)) for word in entry.title_words}
    ]
    return found[0] if len(found) == 1 else None


def _posting_language(tokens: list[str], rules: LanguageRules) -> str | None:
    hits = {
        code: sum(1 for token in tokens if token in set(entry.stopwords))
        for code, entry in rules.languages.items()
    }
    total = sum(hits.values())
    if total < rules.detection.min_stopword_hits:
        return None
    code, best = max(hits.items(), key=lambda item: item[1])
    return code if best / total >= rules.detection.min_share else None


def language_signals(title: str, description: str | None, rules: LanguageRules) -> LanguageSignals:
    """Languages a posting requires or prefers, and the language it is written in.

    Sentence by sentence: a sentence naming a language as a plus makes it preferred, otherwise a
    requirement phrase makes it required. A posting written in a language requires it too; with
    too little text to tell, a title word of exactly one language decides.
    Unknown stays unknown — nothing is guessed from the company or location.
    """
    text = f"{title}. {description or ''}"
    required: set[str] = set()
    preferred: set[str] = set()
    for sentence in _SENTENCE_END.split(text):
        words = " ".join(_words(sentence))
        if not words:
            continue
        for code, entry in rules.languages.items():
            if _phrase_in(words, entry.preferred_phrases):
                preferred.add(code)
            elif _phrase_in(words, entry.required_phrases):
                required.add(code)
    posting = _posting_language(_words(text), rules)
    if posting is None and len(_words(description or "")) < rules.detection.min_stopword_hits:
        posting = _title_language(title, rules)  # alert emails carry only the title
    if posting is not None:
        required.add(posting)
    return LanguageSignals(
        posting_language=posting,
        required=frozenset(required),
        preferred=frozenset(preferred - required),
    )


def _sha256(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def dedupe_hash(company: str, title: str, location: Location) -> bytes:
    """Hash of (normalized company, normalized title, country, city) — the dedupe key."""
    key = "|".join(
        (
            normalize_company(company),
            normalize_title(title),
            location.country or "",
            _fold(location.city or ""),
        )
    )
    return _sha256(key)


def content_hash(
    *, title: str, description: str | None, location_raw: str | None, apply_url: str | None
) -> bytes:
    """Hash of the job's content; a change means the posting was edited."""
    payload = json.dumps(
        [title, description or "", location_raw or "", apply_url or ""], ensure_ascii=False
    )
    return _sha256(payload)
