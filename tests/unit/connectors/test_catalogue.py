import httpx
import pytest

from jobradar import connectors
from jobradar.connectors.schemas import CompanyEntry
from jobradar.core.source_policies import SourcePolicyRegistry
from tests.support.fake_http import Handler, fixture_json, polite_client, routes

pytestmark = pytest.mark.anyio
GREENHOUSE = "/v1/boards/examplelogistics/jobs"
LEVER = "/v0/postings/samplepay"
ASHBY = "/posting-api/job-board/demoair"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def boards() -> dict[str, object]:
    return {
        GREENHOUSE: fixture_json("connectors", "greenhouse", "board.json"),  # Dubai
        LEVER: fixture_json("connectors", "lever", "postings.json"),  # India only
        ASHBY: fixture_json("connectors", "ashby", "board.json"),  # Abu Dhabi
        "/v1/companies/emptyco/postings": {
            "offset": 0,
            "limit": 100,
            "totalFound": 0,
            "content": [],
        },
        "/v1/boards/broken/jobs": httpx.Response(400),
    }


class Recorder:
    def __init__(self, handler: Handler) -> None:
        self.handler = handler
        self.paths: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        return self.handler(request)

    def factory(self, policies: SourcePolicyRegistry) -> object:
        return polite_client(self, policies)


def entry(name: str, ats: str, slug: str) -> CompanyEntry:
    return CompanyEntry.model_validate(
        {"name": name, "ats": ats, "ats_slug": slug, "countries": ["AE"], "source": "test"}
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Careem Networks FZ-LLC", ["careemnetworks", "careem-networks", "careem"]),
        ("noon", ["noon"]),
        ("Checkout.com", ["checkoutcom"]),
        ("Émirates Café L.L.C.", ["emiratescafe", "emirates-cafe", "emirates"]),
        ("!!!", []),
    ],
)
def test_slug_guesses(name: str, expected: list[str]) -> None:
    assert connectors.slug_guesses(name) == expected


@pytest.mark.parametrize(
    ("url", "board"),
    [
        (
            "https://boards.greenhouse.io/examplelogistics/jobs/4001",
            ("greenhouse", "examplelogistics"),
        ),
        ("https://job-boards.greenhouse.io/acme/jobs/1", ("greenhouse", "acme")),
        ("https://jobs.lever.co/samplepay/7d1e", ("lever", "samplepay")),
        ("https://jobs.eu.lever.co/samplepay/7d1e", ("lever", "samplepay")),
        ("https://jobs.ashbyhq.com/demoair/b1", ("ashby", "demoair")),
        ("https://apply.workable.com/fictional-retail/j/ABC123/", ("workable", "fictional-retail")),
        ("https://jobs.smartrecruiters.com/SampleBank/744000", ("smartrecruiters", "SampleBank")),
        ("https://apply.workable.com/j/ABC123", None),
        ("https://boards.greenhouse.io/embed/job_app?for=acme", None),
        ("https://www.linkedin.com/jobs/view/3900000001/", None),
    ],
)
def test_detect_board_from_job_links(url: str, board: tuple[str, str] | None) -> None:
    assert connectors.detect_board(url) == board


async def test_verify_entries_reports_each_outcome() -> None:
    recorder = Recorder(routes(boards()))
    entries = [
        entry("Example Logistics", "greenhouse", "examplelogistics"),
        entry("Sample Pay", "lever", "samplepay"),
        entry("Demo Air", "ashby", "demoair"),
        entry("Gone Co", "workable", "goneco"),
        entry("Empty Co", "smartrecruiters", "emptyco"),
        entry("Broken Co", "greenhouse", "broken"),
    ]

    checks = await connectors.verify_entries(entries, client_factory=recorder.factory)  # type: ignore[arg-type]

    assert [(c.name, c.status, c.jobs_in_countries) for c in checks] == [
        ("Example Logistics", "verified", 1),
        ("Sample Pay", "no_postings", 0),
        ("Demo Air", "verified", 1),
        ("Gone Co", "not_found", 0),
        ("Empty Co", "not_found", 0),
        ("Broken Co", "error", 0),
    ]
    assert checks[0].jobs_total == 2
    assert checks[-1].error == "HTTP 400"
    assert len(recorder.paths) == len(entries)  # one request per board


async def test_verify_entries_can_count_another_country() -> None:
    recorder = Recorder(routes(boards()))

    checks = await connectors.verify_entries(
        [entry("Sample Pay", "lever", "samplepay")],
        countries=frozenset({"IN"}),
        client_factory=recorder.factory,  # type: ignore[arg-type]
    )

    assert checks[0].status == "verified"
    assert checks[0].jobs_in_countries == checks[0].jobs_total


async def test_probe_stops_at_the_first_board_with_jobs_in_the_country() -> None:
    recorder = Recorder(routes(boards()))

    found = await connectors.probe_companies(
        ["Demo Air"],
        countries=frozenset({"AE"}),
        client_factory=recorder.factory,  # type: ignore[arg-type]
    )

    check = found["Demo Air"]
    assert check is not None
    assert (check.ats, check.slug, check.status) == ("ashby", "demoair", "verified")
    assert recorder.paths[-1] == ASHBY  # nothing probed after the hit
    assert "/v1/boards/demoair/jobs" in recorder.paths  # greenhouse was tried first
    assert "/v1/boards/demo-air/jobs" in recorder.paths  # with every slug guess


async def test_probe_falls_back_to_a_board_without_local_jobs_or_none() -> None:
    recorder = Recorder(routes(boards()))

    found = await connectors.probe_companies(
        ["Sample Pay", "Nobody Here"],
        countries=frozenset({"AE"}),
        client_factory=recorder.factory,  # type: ignore[arg-type]
    )

    sample = found["Sample Pay"]
    assert sample is not None
    assert (sample.ats, sample.status) == ("lever", "no_postings")
    assert found["Nobody Here"] is None
