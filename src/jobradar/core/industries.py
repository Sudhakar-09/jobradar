"""Industry vocabulary (`config/industries.yaml`) for user exclusions and company tags.

Matching blocks a job when its company is explicitly tagged with an industry the user excludes.
An untagged company is never guessed into an industry, so it is never excluded.
"""

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints

from jobradar.core.settings import get_settings

IndustryCode = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]


class Industry(BaseModel):
    """One industry a user may exclude."""

    model_config = ConfigDict(extra="forbid")

    label: str
    description: str


class IndustryVocabulary(BaseModel):
    """`config/industries.yaml`."""

    model_config = ConfigDict(extra="forbid")

    industries: dict[IndustryCode, Industry]

    def unknown(self, codes: Iterable[str]) -> list[str]:
        """Codes that are not in the vocabulary, sorted."""
        return sorted(set(codes) - set(self.industries))


def load_industries(path: Path) -> IndustryVocabulary:
    """Load and validate an industry vocabulary file."""
    return IndustryVocabulary.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def industry_vocabulary() -> IndustryVocabulary:
    """The process-wide industry vocabulary."""
    return load_industries(get_settings().config_dir / "industries.yaml")


def require_known(codes: Iterable[str], *, where: str) -> None:
    """Raise ValueError naming ``where`` if any code is not in the vocabulary."""
    unknown = industry_vocabulary().unknown(codes)
    if unknown:
        raise ValueError(f"unknown industries in {where}: {unknown} (see config/industries.yaml)")


def excluded_industries(
    company_industries: Iterable[str], excluded: Iterable[str]
) -> frozenset[str]:
    """The company's industries that the user excludes (empty: the job stays eligible)."""
    return frozenset(company_industries) & frozenset(excluded)
