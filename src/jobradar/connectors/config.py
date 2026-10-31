"""Load connector configuration files from ``settings.config_dir``."""

from functools import lru_cache
from pathlib import Path

import yaml

from jobradar.connectors.schemas import CompanyFile, ConnectorsFile
from jobradar.core.industries import require_known
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import SourcePolicyRegistry, load_source_policies


def _read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_connectors_file(path: Path) -> ConnectorsFile:
    """Load and validate `connectors.yaml`."""
    return ConnectorsFile.model_validate(_read_yaml(path))


def load_company_file(path: Path) -> CompanyFile:
    """Load and validate `companies.yaml`; (ats, slug) pairs unique, industries known."""
    company_file = CompanyFile.model_validate(_read_yaml(path))
    keys = [(entry.ats, entry.ats_slug.lower()) for entry in company_file.companies]
    duplicates = sorted({f"{ats}/{slug}" for ats, slug in keys if keys.count((ats, slug)) > 1})
    if duplicates:
        raise ValueError(f"duplicate companies in {path.name}: {duplicates}")
    require_known(
        (code for entry in company_file.companies for code in entry.industries), where=path.name
    )
    return company_file


@lru_cache(maxsize=1)
def policy_registry() -> SourcePolicyRegistry:
    """The process-wide source policy registry from `source_policies.yaml`."""
    return load_source_policies(get_settings().config_dir / "source_policies.yaml")


@lru_cache(maxsize=1)
def connectors_config() -> ConnectorsFile:
    """The process-wide connector endpoint configuration."""
    return load_connectors_file(get_settings().config_dir / "connectors.yaml")


def companies_path() -> Path:
    """Path of the curated company catalogue."""
    return get_settings().config_dir / "companies.yaml"
