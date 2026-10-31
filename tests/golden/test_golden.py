"""Golden datasets per market (PRD §8a.3, US-2.9 AC1).

`tests/golden/<market>/ats/<connector>.json` is a board response in that connector's format and
`tests/golden/<market>/alerts/<parser>.eml` an alert email; next to each, `*.expected.json` holds
the expected parsed and normalized output. Any difference fails. After an intended change, run
`uv run pytest tests/golden --update-golden` and review the diff of the expected files.
All samples are synthetic or anonymized.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from jobradar import normalizer
from jobradar.connectors.alerts import pick_parser
from jobradar.connectors.mime import parse_mime
from jobradar.connectors.registry import discover_plugins
from jobradar.connectors.schemas import CompanyRef, FetchContext, RawJob
from jobradar.connectors.service.alerts import configured_parsers
from jobradar.core.packs.conformance import GOLDEN_EXPECTED_SUFFIX
from jobradar.normalizer.rules import detect_location
from jobradar.normalizer.service import location_aliases
from tests.support.fake_http import ROOT, polite_client

pytestmark = [pytest.mark.anyio, pytest.mark.golden]
GOLDEN = Path(__file__).resolve().parent
SETTINGS = __import__("jobradar.connectors.config", fromlist=["x"]).load_connectors_file(
    ROOT / "config" / "connectors.yaml"
)
RECEIVED = datetime(2026, 10, 31, 6, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def samples(kind: str, suffix: str) -> list[Path]:
    found = GOLDEN.glob(f"*/{kind}/*{suffix}")
    return sorted(p for p in found if not p.name.endswith(GOLDEN_EXPECTED_SUFFIX))


def normalized(job: RawJob) -> dict[str, object]:
    location = detect_location(
        job.location_raw, location_aliases(), country_hint=job.country_code, city_hint=job.city
    )
    signals = normalizer.job_language_signals(job)
    return {
        "source_job_id": job.source_job_id,
        "title": job.title,
        "company": job.company_name,
        "location_raw": job.location_raw,
        "country": location.country,
        "city": location.city,
        "url": str(job.url),
        "posting_language": signals.posting_language,
        "required_languages": sorted(signals.required),
        "preferred_languages": sorted(signals.preferred),
    }


def compare(sample: Path, actual: dict[str, object], update: bool) -> None:
    expected_path = sample.with_name(sample.stem + GOLDEN_EXPECTED_SUFFIX)
    rendered = json.dumps(actual, indent=2, ensure_ascii=False) + "\n"
    if update:
        expected_path.write_text(rendered, encoding="utf-8")
    assert expected_path.is_file(), f"missing {expected_path.name}; run with --update-golden"
    assert json.loads(expected_path.read_text(encoding="utf-8")) == json.loads(rendered)


BOARDS = {path: json.loads(path.read_text(encoding="utf-8")) for path in samples("ats", ".json")}


@pytest.mark.parametrize("sample", samples("ats", ".json"), ids=lambda p: f"{p.parts[-3]}/{p.stem}")
async def test_ats_board_sample(sample: Path, request: pytest.FixtureRequest) -> None:
    code = sample.stem
    body = BOARDS[sample]
    company = CompanyRef(UUID(int=1), "Golden Company", code, "golden")

    async with polite_client(lambda _request: httpx.Response(200, json=body)) as http:
        ctx = FetchContext(http=http, settings=SETTINGS.connectors[code], company=company)
        result = await discover_plugins()[code].fetch(ctx)

    actual = {"items_invalid": result.items_invalid, "jobs": [normalized(j) for j in result.jobs]}
    compare(sample, actual, request.config.getoption("--update-golden"))


@pytest.mark.parametrize(
    "sample", samples("alerts", ".eml"), ids=lambda p: f"{p.parts[-3]}/{p.stem}"
)
def test_alert_email_sample(sample: Path, request: pytest.FixtureRequest) -> None:
    message = parse_mime(sample.read_bytes(), f"golden-{sample.stem}", received_fallback=RECEIVED)
    parser = pick_parser(list(configured_parsers()), message)
    assert parser is not None, "no parser matches the sample's sender"
    assert parser.code == sample.stem, "golden alert files are named after their parser"

    jobs, invalid = parser.parse(message)

    actual = {"items_invalid": invalid, "jobs": [normalized(j) for j in jobs]}
    compare(sample, actual, request.config.getoption("--update-golden"))
