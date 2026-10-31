from pathlib import Path
from typing import ClassVar

import pytest

from jobradar.connectors.config import load_company_file, load_connectors_file
from jobradar.connectors.health import evaluate_health
from jobradar.connectors.registry import check_connectors, discover_plugins
from jobradar.connectors.schemas import FetchContext, FetchResult
from jobradar.core.source_policies import AccessMode
from tests.support.fake_http import ROOT, registry

CONNECTORS = load_connectors_file(ROOT / "config" / "connectors.yaml")


def test_all_connector_plugins_are_registered() -> None:
    plugins = discover_plugins()

    assert set(plugins) == {
        "greenhouse",
        "lever",
        "ashby",
        "workable",
        "smartrecruiters",
        "adzuna",
        "remotive",
    }
    assert {code for code, plugin in plugins.items() if plugin.kind == "query"} == {
        "adzuna",
        "remotive",
    }


def test_repository_connectors_policies_and_config_are_consistent() -> None:
    assert check_connectors(discover_plugins(), registry(), CONNECTORS) == []


def test_connector_on_a_one_tap_host_is_reported() -> None:
    class Scraper:
        code: ClassVar[str] = "greenhouse"
        mode: ClassVar[AccessMode] = AccessMode.ATS_FEED
        hosts: ClassVar[tuple[str, ...]] = ("www.linkedin.com",)

        async def fetch(self, ctx: FetchContext) -> FetchResult:
            raise NotImplementedError

    problems = check_connectors({"greenhouse": Scraper()}, registry(), CONNECTORS)

    assert any("www.linkedin.com does not allow ats_feed" in p for p in problems)
    assert any("list_url host boards-api.greenhouse.io" in p for p in problems)


@pytest.mark.parametrize(
    ("found", "invalid", "average", "expected"),
    [
        (10, 0, None, "ok"),
        (10, 1, None, "partial"),
        (8, 2, None, "degraded"),  # 20 % invalid: schema drift
        (0, 0, 12.0, "degraded"),  # usually busy, now empty
        (0, 0, 2.0, "ok"),  # usually quiet: zero is normal
        (1, 0, 4.0, "ok"),  # quiet sources never trigger drop alerts
        (3, 0, 12.0, "degraded"),  # > 70 % drop
        (4, 0, 12.0, "ok"),  # exactly a third is not a drop
        (0, 0, None, "ok"),
    ],
)
def test_health_rules(found: int, invalid: int, average: float | None, expected: str) -> None:
    assert evaluate_health(found, invalid, average) == expected


def test_company_file_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "companies.yaml"
    entry = (
        "  - {name: A, ats: lever, ats_slug: Same, countries: [AE], source: owner}\n"
        "  - {name: B, ats: lever, ats_slug: same, countries: [AE], source: owner}\n"
    )
    path.write_text("companies:\n" + entry, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate companies"):
        load_company_file(path)


def test_company_file_requires_a_country(tmp_path: Path) -> None:
    path = tmp_path / "companies.yaml"
    path.write_text(
        "companies:\n  - {name: A, ats: lever, ats_slug: a, countries: [], source: owner}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least 1"):
        load_company_file(path)


def test_repository_company_file_is_valid() -> None:
    load_company_file(ROOT / "config" / "companies.yaml")
