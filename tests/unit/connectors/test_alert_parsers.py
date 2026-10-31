from datetime import UTC, datetime
from pathlib import Path

import pytest

from jobradar.connectors.alerts import (
    LinkCardParser,
    build_parsers,
    load_alert_senders,
    pick_parser,
    sender_domain,
    unwrap_tracking,
)
from jobradar.connectors.mime import parse_mime
from jobradar.connectors.schemas import InboundMessage
from jobradar.core.source_policies import AccessMode
from tests.support.alerts import load_message
from tests.support.fake_http import ROOT, registry

SENDERS = load_alert_senders(ROOT / "config" / "alert_senders.yaml")
PARSERS = build_parsers(SENDERS)

EXPECTED = {
    "linkedin": [
        (
            "3900000001",
            "Senior Java Backend Engineer",
            "Example Logistics",
            "Dubai, United Arab Emirates",
            "https://www.linkedin.com/jobs/view/3900000001/",
        ),
        (
            "3900000002",
            "Backend Developer (Java)",
            "Sample Pay",
            "Bengaluru, Karnataka, India",
            "https://www.linkedin.com/jobs/view/3900000002/",
        ),
    ],
    "naukrigulf": [
        (
            "311020000123",
            "Java Developer",
            "Sample Bank",
            "Dubai - UAE",
            "https://www.naukrigulf.com/java-developer-in-dubai-uae-in-sample-bank-3-to-6-years-n-cd-1000001-jid-311020000123",
        ),
        (
            "311020000456",
            "Senior Backend Engineer",
            "Demo Air",
            "Abu Dhabi, UAE",
            "https://www.naukrigulf.com/senior-backend-engineer-in-abu-dhabi-uae-in-demo-air-5-to-8-years-n-cd-1000002-jid-311020000456",
        ),
    ],
    "bayt": [
        (
            "5012345",
            "Backend Java Engineer",
            "Fictional Retail",
            "Dubai, United Arab Emirates",
            "https://www.bayt.com/en/uae/jobs/backend-java-engineer-5012345/",
        ),
        (
            "5012399",
            "Java Team Lead",
            "Example Logistics",
            "Sharjah, United Arab Emirates",
            "https://www.bayt.com/en/uae/jobs/java-team-lead-5012399/",
        ),
    ],
    "gulftalent": [
        (
            "412345",
            "Senior Software Engineer - Java",
            "Sample Bank",
            "Dubai, UAE",
            "https://www.gulftalent.com/uae/jobs/senior-software-engineer-java-412345",
        ),
    ],
    "naukri": [
        (
            "311026001234",
            "Java Backend Developer",
            "Sample Pay",
            "Pune",
            "https://www.naukri.com/job-listings-java-backend-developer-sample-pay-pune-3-to-6-years-311026001234",
        ),
        (
            "311026005678",
            "Senior Java Engineer",
            "Example Logistics",
            "Hyderabad",
            "https://www.naukri.com/job-listings-senior-java-engineer-example-logistics-hyderabad-5-to-9-years-311026005678",
        ),
    ],
    "instahyre": [
        (
            "284512",
            "Java Backend Engineer",
            "Sample Pay",
            "Bangalore",
            "https://www.instahyre.com/job-284512-java-backend-engineer-at-sample-pay-bangalore/",
        ),
    ],
    "foundit": [
        (
            "31012345",
            "Java Developer",
            "Fictional Retail",
            "Hyderabad / Secunderabad, Telangana",
            "https://www.foundit.in/job/java-developer-fictional-retail-hyderabad-31012345",
        ),
    ],
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_board_parser_extracts_jobs_from_its_alert(name: str) -> None:
    message = load_message(name)
    parser = pick_parser(PARSERS, message)

    assert parser is not None
    assert parser.code == name
    jobs, invalid = parser.parse(message)
    assert invalid == 0
    assert [
        (j.source_job_id, j.title, j.company_name, j.location_raw, str(j.url)) for j in jobs
    ] == EXPECTED[name]
    assert all(job.source == f"alert:{name}" for job in jobs)
    assert all(job.apply_url == job.url for job in jobs)
    assert all("tracking" not in str(job.url) and "utm_" not in str(job.url) for job in jobs)


def test_every_parser_has_a_fixture() -> None:
    assert set(SENDERS.parsers) == set(EXPECTED)


def test_alert_links_are_on_hosts_that_allow_alert_email() -> None:
    for name, expected in EXPECTED.items():
        host = expected[0][4].split("/")[2]
        assert registry().is_allowed(host, AccessMode.ALERT_EMAIL), name
        assert registry().policy_for(host).modes == {AccessMode.ALERT_EMAIL, AccessMode.ONE_TAP}, (
            name
        )


def test_alert_without_job_links_yields_nothing() -> None:
    message = load_message("linkedin_no_jobs")
    parser = pick_parser(PARSERS, message)

    assert parser is not None
    assert parser.parse(message) == ([], 0)


def test_unknown_sender_has_no_parser() -> None:
    message = InboundMessage(
        provider_message_id="x",
        sender="News <news@example.org>",
        received_at=datetime.now(UTC),
        html="<a href='https://www.linkedin.com/jobs/view/1234567/'>Job</a>",
    )

    assert pick_parser(PARSERS, message) is None


def test_lookalike_sender_domain_is_not_trusted() -> None:
    message = InboundMessage(
        provider_message_id="x",
        sender="jobs@linkedin.com.evil.example",
        received_at=datetime.now(UTC),
    )

    assert pick_parser(PARSERS, message) is None


def test_card_without_company_is_counted_invalid() -> None:
    message = InboundMessage(
        provider_message_id="x",
        sender="jobalerts-noreply@linkedin.com",
        received_at=datetime.now(UTC),
        html="<div><a href='https://www.linkedin.com/jobs/view/3900000009/'>Lonely title</a></div>",
    )
    parser = pick_parser(PARSERS, message)

    assert parser is not None
    assert parser.parse(message) == ([], 1)


def test_plain_text_only_email_yields_nothing() -> None:
    message = InboundMessage(
        provider_message_id="x",
        sender="jobalert@naukri.com",
        received_at=datetime.now(UTC),
        text="Java Developer https://www.naukri.com/job-listings-java-dev-x-123456789012",
    )
    parser = pick_parser(PARSERS, message)

    assert parser is not None
    assert parser.parse(message) == ([], 0)


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("https://t.example/r?url=https%3A%2F%2Fwww.bayt.com%2Fx", "https://www.bayt.com/x"),
        ("https://t.example/r?u=https%3A%2F%2Fa.example%2F1&x=2", "https://a.example/1"),
        (
            "https://t.example/r?url=http%3A%2F%2Fplain.example",
            "https://t.example/r?url=http%3A%2F%2Fplain.example",
        ),
        ("https://www.bayt.com/en/uae/jobs/x-1/", "https://www.bayt.com/en/uae/jobs/x-1/"),
    ],
)
def test_unwrap_tracking(href: str, expected: str) -> None:
    assert unwrap_tracking(href) == expected


@pytest.mark.parametrize(
    ("sender", "domain"),
    [
        ("LinkedIn <jobalerts-noreply@linkedin.com>", "linkedin.com"),
        ("jobs@Mail.Naukri.com", "mail.naukri.com"),
        ("no address", ""),
    ],
)
def test_sender_domain(sender: str, domain: str) -> None:
    assert sender_domain(sender) == domain


def test_subdomain_senders_match_their_board() -> None:
    parser = next(p for p in PARSERS if p.code == "naukri")
    message = InboundMessage(
        provider_message_id="x", sender="jobs@mail.naukri.com", received_at=datetime.now(UTC)
    )

    assert parser.matches(message)


def test_job_url_patterns_need_an_id_group(tmp_path: Path) -> None:
    path = tmp_path / "alert_senders.yaml"
    path.write_text(
        "parsers:\n  x:\n    name: X\n    markets: [uae]\n    sender_addresses: [a@x.example]\n"
        "    sender_domains: [x.example]\n    job_url: '^https://x.example/job/\\d+'\n"
        "    canonical_url: 'https://x.example/job'\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="named group 'id'"):
        load_alert_senders(path)


def test_mime_parsing_reads_headers_and_both_bodies() -> None:
    message = load_message("linkedin")

    assert message.sender == "LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>"
    assert message.received_at == datetime(2026, 10, 29, 7, 30, tzinfo=UTC)
    assert message.subject.startswith('"Java Backend Engineer"')
    assert message.html is not None
    assert "<table>" in message.html
    assert message.text is not None


def test_mime_parsing_without_date_uses_fallback() -> None:
    raw = b"From: a@naukri.com\r\nSubject: x\r\nContent-Type: text/plain\r\n\r\nhello"
    fallback = datetime(2026, 1, 1, tzinfo=UTC)

    message = parse_mime(raw, "id-1", received_fallback=fallback)

    assert message.received_at == fallback
    assert message.html is None
    assert message.text is not None


def test_parser_class_is_reusable_for_new_boards() -> None:
    config = SENDERS.parsers["bayt"].model_copy(update={"sender_domains": ["bayt.example"]})
    parser = LinkCardParser("bayt_test", config)

    assert parser.source == "alert:bayt_test"
