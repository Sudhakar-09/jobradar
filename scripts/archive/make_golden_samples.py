"""Write the synthetic golden samples in tests/golden/<market>/ (US-2.9).

Kept for the record (CLAUDE.md rule 12); not run in CI. Run once from the repo root, then
`uv run pytest tests/golden --update-golden` and review the expected files by hand.

- ATS samples: board responses in each connector's format with fictional companies and jobs
  located in the market, covering the language cases (English, German-language, German
  required, German a plus; Arabic a plus in the UAE).
- Alert samples: the existing synthetic alert fixtures per board, and market-specific LinkedIn
  alerts derived from the anonymized real-layout fixture (fake jobs replaced per market).
"""

import json
import shutil
from email import policy
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "golden"
ALERTS = ROOT / "tests" / "fixtures" / "alerts"
EN_BODY = (
    "<p>We are looking for an engineer who will join our team and build Java services with "
    "Spring Boot and Kafka. You will work with product teams on our platform and you are "
    "comfortable in an international team where the company language is English.</p>"
)
DE_BODY = (
    "<p>Wir suchen dich für unser Team. Du entwickelst mit uns Services mit Java und Spring "
    "Boot und arbeitest mit der Fachabteilung zusammen. Wir bieten dir ein Team, in dem du "
    "Verantwortung übernimmst, und eine Kultur, die von Vertrauen geprägt ist.</p>"
)


def greenhouse(jobs: list[tuple[int, str, str, str]]) -> dict[str, object]:
    return {
        "jobs": [
            {
                "id": job_id,
                "title": title,
                "absolute_url": f"https://boards.greenhouse.io/golden/jobs/{job_id}",
                "location": {"name": location},
                "content": body.replace("<", "&lt;").replace(">", "&gt;"),
                "first_published": "2026-10-28T08:00:00Z",
            }
            for job_id, title, location, body in jobs
        ]
        + [{"id": 9999, "absolute_url": "https://boards.greenhouse.io/golden/jobs/9999"}],
        "meta": {"total": len(jobs) + 1},
    }


def lever(jobs: list[tuple[str, str, str, str, str]]) -> list[dict[str, object]]:
    return [
        {
            "id": job_id,
            "text": title,
            "hostedUrl": f"https://jobs.lever.co/golden/{job_id}",
            "categories": {"location": location},
            "createdAt": 1761638400000,
            "descriptionPlain": body,
            "country": country,
        }
        for job_id, title, location, body, country in jobs
    ]


ATS = {
    "india": {
        "greenhouse": greenhouse(
            [
                (5101, "Java Backend Engineer", "Bengaluru, Karnataka, India", EN_BODY),
                (5102, "Senior Software Engineer (Java)", "Pune (Hybrid)", EN_BODY),
                (5103, "Platform Engineer", "Hyderabad, India", EN_BODY + "<p>Fluent English required.</p>"),
            ]
        ),
    },
    "uae": {
        "greenhouse": greenhouse(
            [
                (5201, "Senior Java Backend Engineer", "Dubai, United Arab Emirates", EN_BODY),
                (5202, "Backend Engineer", "Abu Dhabi", EN_BODY + "<p>Arabic is a plus.</p>"),
                (5203, "Java Developer", "Dubai Internet City, Dubai", EN_BODY),
            ]
        ),
    },
    "germany": {
        "greenhouse": greenhouse(
            [
                (5301, "Senior Java Backend Engineer", "Berlin, Germany", EN_BODY),
                (5302, "Backend Entwickler Java (m/w/d)", "München", DE_BODY),
                (5303, "Java Engineer", "Hamburg, Germany", EN_BODY + "<p>Fluent German (C1) is required.</p>"),
                (5304, "Software Engineer (Java/Kotlin)", "Berlin (Hybrid)", EN_BODY + "<p>German is a plus.</p>"),
                (5305, "Java Developer", "Frankfurt am Main", EN_BODY + "<p>Sehr gute Deutsch- und Englischkenntnisse.</p>"),
            ]
        ),
        "lever": lever(
            [
                ("d0000000-0000-4000-8000-000000000001", "Backend Engineer (Java)", "Köln", EN_BODY, "DE"),
                ("d0000000-0000-4000-8000-000000000002", "Java Entwickler (w/m/d)", "Stuttgart", DE_BODY, "DE"),
            ]
        ),
    },
}

ALERT_COPIES = {
    "india": ["naukri", "instahyre", "foundit"],
    "uae": ["naukrigulf", "bayt", "gulftalent"],
}

LINKEDIN_JOBS = {
    "india": [
        ("Senior Java Backend Engineer", "Example Logistics", "Bengaluru, Karnataka, India (Hybrid)"),
        ("Java Developer", "Sample Pay", "Pune, Maharashtra, India (On-site)"),
        ("Backend Engineer (Java/Kotlin)", "Demo Air", "Hyderabad, Telangana, India (Remote)"),
        ("Software Engineer, Payments", "Fictional Retail", "Chennai, Tamil Nadu, India (Hybrid)"),
        ("Lead Java Engineer - Microservices", "Sample Bank", "Gurugram, Haryana, India (On-site)"),
        ("Platform Engineer (Java/Spring)", "Example Health", "Noida, Uttar Pradesh, India (Hybrid)"),
    ],
    "uae": [
        ("Senior Java Backend Engineer", "Example Logistics", "Dubai, United Arab Emirates (On-site)"),
        ("Java Developer", "Sample Bank", "Abu Dhabi, United Arab Emirates (Hybrid)"),
        ("Backend Engineer (Java/Kotlin)", "Demo Air", "Dubai (Hybrid)"),
        ("Software Engineer, Payments", "Fictional Retail", "Sharjah, United Arab Emirates (On-site)"),
        ("Lead Java Engineer - Microservices", "Sample Pay", "Dubai, United Arab Emirates (On-site)"),
        ("Platform Engineer (Java/Spring)", "Example Health", "Abu Dhabi (On-site)"),
    ],
    "germany": [
        ("Senior Java Backend Engineer", "Example Logistics", "Berlin, Germany (Hybrid)"),
        ("Backend Entwickler (m/w/d)", "Beispiel Versicherung", "München, Bayern, Deutschland (On-site)"),
        ("Java Engineer", "Sample Pay", "Hamburg, Germany (Remote)"),
        ("Software Engineer (m/w/d)", "Fictional Retail", "Frankfurt am Main, Hessen, Deutschland (Hybrid)"),
        ("Werkstudent Softwareentwicklung Java", "Sample Bank", "Köln, Germany (Hybrid)"),
        ("Platform Engineer (Java/Spring)", "Example Health", "Stuttgart, Germany (On-site)"),
    ],
}
FIXTURE_JOBS = [
    ("Senior Java Backend Engineer", "Example Logistics", "Dubai, United Arab Emirates (On-site)"),
    ("Java Developer", "Sample Pay", "Bengaluru, Karnataka, India (Hybrid)"),
    ("Backend Engineer (Java/Kotlin)", "Demo Air", "Abu Dhabi (Hybrid)"),
    ("Software Engineer, Payments", "Fictional Retail", "Pune, Maharashtra, India (Remote)"),
    ("Lead Java Engineer - Microservices", "Sample Bank", "Dubai (On-site)"),
    ("Platform Engineer (Java/Spring)", "Example Health", "Hyderabad (Hybrid)"),
]


def linkedin_for(market: str) -> bytes:
    """The real-layout LinkedIn fixture with its first three jobs replaced for the market."""
    message = BytesParser(policy=policy.default).parsebytes((ALERTS / "linkedin_card_links.eml").read_bytes())
    html_part = message.get_body(("html",))
    assert html_part is not None
    html = html_part.get_content()
    for (old_title, old_company, old_location), (title, company, location) in zip(
        FIXTURE_JOBS, LINKEDIN_JOBS[market], strict=True
    ):
        html = html.replace(f">{old_title}<", f">{title}<")
        html = html.replace(f"{old_company} · {old_location}", f"{company} · {location}")
    html_part.set_content(html, subtype="html")
    return message.as_bytes()


def main() -> None:
    for market, boards in ATS.items():
        for code, body in boards.items():
            path = GOLDEN / market / "ats" / f"{code}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for market, boards in ALERT_COPIES.items():
        for code in boards:
            target = GOLDEN / market / "alerts" / f"{code}.eml"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ALERTS / f"{code}.eml", target)
    for market in LINKEDIN_JOBS:
        target = GOLDEN / market / "alerts" / "linkedin.eml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(linkedin_for(market))


if __name__ == "__main__":
    main()
