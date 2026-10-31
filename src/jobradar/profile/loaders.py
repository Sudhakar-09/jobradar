"""YAML loaders for the profile and the answer bank."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from jobradar.profile.models import AnswerBank, Profile


def _load_yaml_model[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")  # noqa: TRY004 -- bad file content, not a caller type error
    return model.model_validate(data)


def load_profile(path: Path) -> Profile:
    """Load and validate a profile YAML file."""
    return _load_yaml_model(path, Profile)


def load_answer_bank(path: Path) -> AnswerBank:
    """Load and validate an answer bank YAML file."""
    return _load_yaml_model(path, AnswerBank)
