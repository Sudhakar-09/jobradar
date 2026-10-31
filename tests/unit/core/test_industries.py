from pathlib import Path

import pytest
import yaml

from jobradar.connectors.config import load_company_file
from jobradar.core.industries import excluded_industries, industry_vocabulary, load_industries
from jobradar.profile.loaders import load_profile

ROOT = Path(__file__).resolve().parents[3]


def test_vocabulary_has_the_owner_examples() -> None:
    vocabulary = load_industries(ROOT / "config" / "industries.yaml")

    assert {"crypto", "gambling", "tobacco"} <= set(vocabulary.industries)
    assert vocabulary.unknown(["crypto", "cannabis", "betting"]) == ["betting", "cannabis"]


def test_a_tagged_company_is_excluded_and_an_untagged_one_never_is() -> None:
    assert excluded_industries(["crypto"], ["crypto", "gambling"]) == {"crypto"}
    assert excluded_industries(["crypto"], []) == frozenset()
    assert excluded_industries([], ["crypto", "gambling"]) == frozenset()


def test_profile_rejects_unknown_industry_codes(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump({"excluded_industries": ["crypto", "betting"]}), "utf-8")

    with pytest.raises(ValueError, match=r"unknown industries.*betting"):
        load_profile(path)

    path.write_text(yaml.safe_dump({"excluded_industries": ["crypto", "gambling"]}), "utf-8")
    assert load_profile(path).excluded_industries == ["crypto", "gambling"]


def test_company_file_rejects_unknown_industry_codes(tmp_path: Path) -> None:
    path = tmp_path / "companies.yaml"
    entry = {
        "name": "Example",
        "ats": "lever",
        "ats_slug": "example",
        "countries": ["AE"],
        "source": "test",
        "industries": ["casino"],
    }
    path.write_text(yaml.safe_dump({"companies": [entry]}), "utf-8")

    with pytest.raises(ValueError, match="unknown industries"):
        load_company_file(path)


def test_catalogue_tags_are_explicit_and_known() -> None:
    companies = load_company_file(ROOT / "config" / "companies.yaml").companies
    tagged = {c.name for c in companies if "crypto" in c.industries}

    assert {"Binance", "Bybit", "Crypto.com"} <= tagged
    assert "Careem" not in tagged
    assert not industry_vocabulary().unknown(code for c in companies for code in c.industries)
