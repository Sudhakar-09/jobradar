from pathlib import Path

import pytest

from jobradar.normalizer.rules import language_signals, load_language_rules

ROOT = Path(__file__).resolve().parents[3]
RULES = load_language_rules(ROOT / "config" / "language_requirements.yaml")
ENGLISH_BODY = (
    "We are looking for an engineer who will join our team. You have experience with Java and "
    "Spring, and you are comfortable working with product teams on our platform."
)
GERMAN_BODY = (
    "Wir suchen dich für unser Team in München. Du entwickelst mit uns Services und bist sicher "
    "im Umgang mit Java, Spring und der Cloud. Du arbeitest mit der Fachabteilung zusammen."
)


@pytest.mark.parametrize(
    ("description", "required", "preferred"),
    [
        ("Fluent German is required.", {"de"}, set()),
        ("Business-fluent German (C1) is a must.", {"de"}, set()),
        ("Fluent German is a plus.", set(), {"de"}),
        ("German is nice to have. Fluent English required.", {"en"}, {"de"}),
        ("Sehr gute Deutsch- und Englischkenntnisse.", {"de", "en"}, set()),
        ("Fließende Deutschkenntnisse.", {"de"}, set()),
        ("Deutschkenntnisse sind von Vorteil.", set(), {"de"}),
        ("Kafka experience is a plus. Fluent German required.", {"de"}, set()),
        ("No German required.", set(), {"de"}),
        ("Java, Spring Boot, Kafka.", set(), set()),
    ],
)
def test_requirement_phrases(description: str, required: set[str], preferred: set[str]) -> None:
    signals = language_signals("Java Engineer", description, RULES)

    assert signals.required == required
    assert signals.preferred == preferred
    assert signals.posting_language is None  # too short to tell


def test_a_posting_written_in_german_requires_german() -> None:
    signals = language_signals("Backend Entwickler (m/w/d)", GERMAN_BODY, RULES)

    assert signals.posting_language == "de"
    assert signals.required == {"de"}


def test_an_english_posting_requires_english_and_a_german_plus_stays_preferred() -> None:
    signals = language_signals("Senior Java Developer", ENGLISH_BODY + " German is a plus.", RULES)

    assert signals.posting_language == "en"
    assert signals.required == {"en"}
    assert signals.preferred == {"de"}


def test_a_mixed_posting_has_no_detected_language() -> None:
    signals = language_signals("Java", ENGLISH_BODY + " " + GERMAN_BODY, RULES)

    assert signals.posting_language is None


@pytest.mark.parametrize(
    ("title", "language"),
    [
        ("Backend Entwickler (m/w/d)", "de"),
        ("Werkstudent Softwareentwicklung", "de"),
        ("Software Engineer (m/w/d)", None),  # the gender marker alone is not German
        ("Java Engineer", None),
    ],
)
def test_title_words_decide_when_there_is_no_description(title: str, language: str | None) -> None:
    signals = language_signals(title, None, RULES)

    assert signals.posting_language == language
    assert signals.required == ({language} if language else set())


def test_title_words_do_not_override_a_full_english_description() -> None:
    signals = language_signals("Backend Entwickler (m/w/d)", ENGLISH_BODY, RULES)

    assert signals.posting_language == "en"


def test_arabic_preferred_and_required() -> None:
    assert language_signals("Engineer", "Arabic is a plus.", RULES).preferred == {"ar"}
    assert language_signals("Engineer", "Fluent Arabic required.", RULES).required == {"ar"}
