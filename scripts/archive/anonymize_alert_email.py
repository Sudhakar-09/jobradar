"""Turn a real job-alert email into a synthetic test fixture with the same HTML layout.

Kept for the record (CLAUDE.md rule 12); not run in CI. Used in Phase 2 to build
tests/fixtures/alerts/linkedin_card_links.eml from the owner's real LinkedIn alert.

    uv run python scripts/archive/anonymize_alert_email.py <board> <in.eml> <out.eml> <owner-email>

What it does, without printing any of the email's content:
- keeps the HTML structure (tags, styles, layout) so the parser meets the real format;
- replaces every text node; job cards get fake titles, companies, locations and job IDs;
- rewrites every link to a clean URL with no tracking parameters; images point nowhere real;
- writes fresh headers (fixed date, example.org recipient);
- then checks that the owner's email, name, original job IDs, titles, companies and link tokens
  do not appear in the output, and prints only pass/fail.
"""

import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from jobradar.connectors.alerts import unwrap_tracking
from jobradar.connectors.mime import parse_mime
from jobradar.connectors.service.alerts import configured_parsers

FAKE_JOBS = [
    ("Senior Java Backend Engineer", "Example Logistics", "Dubai, United Arab Emirates (On-site)"),
    ("Java Developer", "Sample Pay", "Bengaluru, Karnataka, India (Hybrid)"),
    ("Backend Engineer (Java/Kotlin)", "Demo Air", "Abu Dhabi (Hybrid)"),
    ("Software Engineer, Payments", "Fictional Retail", "Pune, Maharashtra, India (Remote)"),
    ("Lead Java Engineer - Microservices", "Sample Bank", "Dubai (On-site)"),
    ("Platform Engineer (Java/Spring)", "Example Health", "Hyderabad (Hybrid)"),
]
SAFE_ATTRS = {"style", "class", "width", "height", "align", "valign", "border", "role", "dir",
              "cellpadding", "cellspacing", "bgcolor", "colspan", "rowspan", "lang"}
FIRST_FAKE_ID = 4100000001
SEPARATOR = re.compile(r"\s+([·|•–-])\s+")


def text_nodes(tag: Tag) -> list[NavigableString]:
    return [s for s in tag.find_all(string=True) if not isinstance(s, Comment) and s.strip()]


def clean_link(href: str) -> str:
    parts = urlsplit(unwrap_tracking(href))
    segments = [s for s in parts.path.split("/") if s][:2]
    host = parts.hostname or "www.linkedin.com"
    return f"https://{host}/{'/'.join(segments)}/" if segments else f"https://{host}/"


def main(board: str, source: Path, target: Path, owner_email: str) -> int:
    raw = source.read_bytes()
    message = parse_mime(raw, "sample", received_fallback=datetime.now(UTC))
    parser = next(p for p in configured_parsers() if p.code == board)
    originals, _ = parser.parse(message)
    soup = BeautifulSoup(message.html or "", "html.parser")
    separator = "·"
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    anchors_by_job: dict[str, list[Tag]] = defaultdict(list)
    for anchor in soup.find_all("a", href=True):
        found = parser._canonical(str(anchor["href"]))  # noqa: SLF001 -- one-off tool
        if found:
            anchors_by_job[found[0]].append(anchor)
    fake_ids = {job_id: str(FIRST_FAKE_ID + n) for n, job_id in enumerate(anchors_by_job)}
    handled: set[int] = set()
    for n, (job_id, anchors) in enumerate(anchors_by_job.items()):
        title, company, location = FAKE_JOBS[n % len(FAKE_JOBS)]
        for anchor in anchors:
            anchor["href"] = f"https://www.linkedin.com/comm/jobs/view/{fake_ids[job_id]}/"
            nodes = text_nodes(anchor)
            if len(nodes) > 1:
                found = SEPARATOR.search(str(nodes[1]))
                separator = found.group(1) if found else separator
            values = [title, f"{company} {separator} {location}", "Easy Apply"]
            for i, node in enumerate(nodes):
                node.replace_with(values[i] if i < len(values) else "Actively recruiting")
            handled.update(id(t) for t in anchor.find_all(string=True))

    for node in soup.find_all(string=True):
        if id(node) not in handled and not isinstance(node, Comment) and node.strip():
            if node.parent is not None and node.parent.name == "style":
                continue
            node.replace_with("Example text")
    for tag in soup.find_all(True):
        href = tag.get("href")
        for attr in list(tag.attrs):
            if attr not in SAFE_ATTRS and attr != "href":
                del tag[attr]
        if tag.name == "a" and href and "/jobs/view/" not in str(tag.get("href")):
            tag["href"] = clean_link(str(href))
        if tag.name == "a" and "/in/" in str(tag.get("href", "")):
            tag["href"] = "https://www.linkedin.com/comm/in/example-member/"
        if tag.name == "img":
            tag["src"] = "https://static.example.invalid/image.png"
            tag["alt"] = ""

    html = str(soup)
    out = EmailMessage()
    out["From"] = "LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>"
    out["To"] = "owner@example.org"
    out["Subject"] = "Senior Java Backend Engineer at Example Logistics"
    out["Date"] = format_datetime(datetime(2026, 10, 31, 6, 0, tzinfo=UTC))
    out["Message-ID"] = "<synthetic-linkedin-card-links@example.org>"
    out.set_content("Example text\n")
    out.add_alternative(html, subtype="html")
    target.write_bytes(out.as_bytes())

    data = target.read_text(encoding="utf-8", errors="replace").casefold()
    local = owner_email.split("@")[0].casefold()
    checks = {
        "owner email absent": owner_email.casefold() not in data,
        "owner name absent": not any(p in data for p in re.split(r"[._-]", local) if len(p) > 3),
        "original job ids absent": not any(job.source_job_id in data for job in originals),
        "original titles absent": not any(job.title.casefold() in data for job in originals),
        "original companies absent": not any(
            job.company_name.casefold() in data for job in originals
        ),
        "no tracking parameters": "trackingid" not in data and "refid" not in data,
    }
    reparsed, invalid = parser.parse(parse_mime(target.read_bytes(), "x", received_fallback=datetime.now(UTC)))
    checks["fixture parses to the same number of jobs"] = len(reparsed) == len(originals)
    checks["no invalid jobs"] = invalid == 0
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]))
