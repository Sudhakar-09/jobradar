import pytest

from jobradar.core.text import html_to_text
from jobradar.normalizer.rules import (
    Location,
    content_hash,
    dedupe_hash,
    detect_location,
    load_location_aliases,
    normalize_company,
    normalize_title,
)
from tests.support.fake_http import ROOT

ALIASES = load_location_aliases(ROOT / "config" / "locations.yaml")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Example Logistics LLC", "example logistics"),
        ("Example Logistics, L.L.C.", "example logistics"),
        ("Sample Pay Pvt. Ltd.", "sample pay"),
        ("Démo Air FZ-LLC", "demo air"),  # FZ-LLC is a UAE legal form
        ("Company", "company"),
    ],
)
def test_normalize_company(name: str, expected: str) -> None:
    assert normalize_company(name) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Java Backend Engineer (m/w/d)", "senior java backend engineer"),
        ("Backend Developer – Java!", "backend developer java"),  # noqa: RUF001 -- en dash on purpose
        ("  JAVA   Engineer ", "java engineer"),
    ],
)
def test_normalize_title(title: str, expected: str) -> None:
    assert normalize_title(title) == expected


@pytest.mark.parametrize(
    ("raw", "country_hint", "city_hint", "expected"),
    [
        ("Dubai, United Arab Emirates", None, None, Location("AE", "Dubai")),
        ("Bangalore, India", None, None, Location("IN", "Bengaluru")),
        ("Remote - India", None, None, Location("IN", None)),
        ("Abu Dhabi", None, None, Location("AE", "Abu Dhabi")),
        ("Gurgaon", None, None, Location("IN", "Gurugram")),
        ("Hyderabad, Telangana, India", "IN", "Hyderabad", Location("IN", "Hyderabad")),
        ("Anywhere", None, None, Location(None, None)),
        (None, "AE", "Dubai", Location("AE", "Dubai")),
        ("Springfield", "US", "Springfield", Location("US", "Springfield")),
        ("Sharjah Media City", "AE", None, Location("AE", "Sharjah")),
        ("Rakuten office", None, None, Location(None, None)),  # "rak" only as a whole word
    ],
)
def test_detect_location(
    raw: str | None, country_hint: str | None, city_hint: str | None, expected: Location
) -> None:
    assert detect_location(raw, ALIASES, country_hint=country_hint, city_hint=city_hint) == expected


def test_same_job_from_two_sources_has_the_same_dedupe_hash() -> None:
    location = Location("AE", "Dubai")

    first = dedupe_hash("Example Logistics LLC", "Senior Java Backend Engineer", location)
    second = dedupe_hash("example logistics", "Senior Java Backend Engineer (m/f/d)", location)

    assert first == second
    assert first != dedupe_hash(
        "Example Logistics", "Senior Java Backend Engineer", Location("IN", "Pune")
    )


def test_content_hash_changes_when_the_posting_changes() -> None:
    base = {
        "title": "Engineer",
        "description": "Build APIs",
        "location_raw": "Dubai",
        "apply_url": "https://x.example/1",
    }

    assert content_hash(**base) == content_hash(**base)
    assert content_hash(**base) != content_hash(**{**base, "description": "Build APIs."})


def test_html_to_text_removes_scripts_and_keeps_paragraphs() -> None:
    markup = (
        "<h2>Role</h2><p>Build <b>APIs</b>.</p><script>steal()</script>"
        "<style>p{}</style><ul><li>Java</li><li>SQL</li></ul>"
    )

    assert html_to_text(markup) == "Role\n\nBuild APIs.\n\nJava\nSQL"


def test_html_to_text_unescapes_entity_encoded_markup() -> None:
    assert html_to_text("&lt;p&gt;Fish &amp;amp; chips&lt;/p&gt;", escaped=True) == "Fish & chips"
