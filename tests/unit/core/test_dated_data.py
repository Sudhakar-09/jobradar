from datetime import date
from pathlib import Path

import pytest
import structlog
import yaml

from jobradar.core.dated_data import DatedTable, load_dated_table
from jobradar.core.packs import load_market_pack

ROOT = Path(__file__).resolve().parents[3]
BLUE_CARD = ROOT / "config" / "market_data" / "germany" / "eu_blue_card.yaml"


def table_data() -> dict[str, object]:
    data = yaml.safe_load(BLUE_CARD.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_blue_card_thresholds_by_effective_date() -> None:
    table = load_dated_table(BLUE_CARD)

    assert table.values_on(date(2025, 6, 1)) == {"standard": 48300, "reduced": 43759.80}
    assert table.values_on(date(2026, 10, 31)) == {"standard": 50700, "reduced": 45934.20}
    assert table.values_on(date(2024, 12, 31)) is None
    assert (table.currency, table.period, table.basis) == ("EUR", "year", "gross_base")


def test_fresh_data_has_no_warnings() -> None:
    table = load_dated_table(BLUE_CARD)

    with structlog.testing.capture_logs() as logs:
        table.values_on(date(2026, 11, 1))

    assert table.stale_reasons(date(2026, 11, 1)) == []
    assert logs == []


def test_unverified_or_outdated_data_warns_and_is_never_extrapolated() -> None:
    table = load_dated_table(BLUE_CARD)

    with structlog.testing.capture_logs() as logs:
        values = table.values_on(date(2027, 2, 1))

    assert values is None  # 2027 not recorded yet: no guess from 2026
    reasons = table.stale_reasons(date(2027, 2, 1))
    assert any("more than 90 days" in reason for reason in reasons)
    assert any("no values recorded after 2026-12-31" in reason for reason in reasons)
    assert {log["event"] for log in logs} == {"dated_data.stale"}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {
                "entries": [
                    {"effective_from": "2026-01-01", "effective_to": "2025-01-01", "values": {}}
                ]
            },
            "before",
        ),
        (
            {
                "entries": [
                    {"effective_from": "2026-01-01", "effective_to": "2026-12-31", "values": {}},
                    {"effective_from": "2026-06-01", "effective_to": "2027-05-31", "values": {}},
                ]
            },
            "overlap",
        ),
        (
            {
                "entries": [
                    {
                        "effective_from": "2026-01-01",
                        "effective_to": "2026-12-31",
                        "values": {"other": 1},
                    }
                ]
            },
            "without notes",
        ),
    ],
)
def test_invalid_tables_are_rejected(change: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        DatedTable.model_validate({**table_data(), **change})


def test_germany_blue_card_route_points_at_the_table() -> None:
    germany = load_market_pack(ROOT / "packs" / "markets" / "germany.yaml")
    route = next(r for r in germany.visa_routes if r.name == "EU Blue Card")

    assert route.salary_thresholds == "germany/eu_blue_card.yaml"
    assert (ROOT / "config" / "market_data" / route.salary_thresholds).is_file()
