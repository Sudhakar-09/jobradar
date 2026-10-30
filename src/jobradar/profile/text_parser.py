"""Conservative structured extraction from explicitly labeled resume text."""

import re

from jobradar.profile.models import Profile

_FIELD_NAMES = {
    "name": "name",
    "full name": "name",
    "persona": "persona",
    "seniority": "seniority",
    "years experience": "years_exp",
    "years of experience": "years_exp",
    "skills": "skills",
    "target markets": "target_markets",
    "target roles": "target_roles",
    "locations": "locations",
    "notice period days": "notice_period_days",
    "languages": "languages",
}
_LIST_FIELDS = {"skills", "target_markets", "target_roles", "locations", "languages"}


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]


def _parse_years(value: str) -> float:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)?\s*", value, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Unable to parse explicit years of experience: {value!r}")
    return float(match.group(1))


def _parse_notice_period(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+)\s*(?:days?)?\s*", value, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Unable to parse explicit notice period in days: {value!r}")
    return int(match.group(1))


def parse_resume_text(text: str) -> Profile:
    """Extract explicitly labeled profile fields without inferring missing facts."""
    if not text.strip():
        raise ValueError("Resume text must not be empty")

    fields: dict[str, object] = {}
    for line in text.splitlines():
        label, separator, value = line.partition(":")
        if not separator:
            continue
        field_name = _FIELD_NAMES.get(label.strip().casefold())
        if field_name is None:
            continue
        if field_name in fields:
            raise ValueError(f"Resume contains the field more than once: {label.strip()}")
        value = value.strip()
        if field_name in _LIST_FIELDS:
            fields[field_name] = _parse_list(value)
        elif field_name == "years_exp":
            fields[field_name] = _parse_years(value)
        elif field_name == "notice_period_days":
            fields[field_name] = _parse_notice_period(value)
        else:
            fields[field_name] = value
    return Profile.model_validate(fields)
