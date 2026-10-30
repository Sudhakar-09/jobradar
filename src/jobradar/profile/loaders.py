from pathlib import Path

import yaml
from pydantic import BaseModel

from jobradar.profile.models import AnswerBank, Profile


def _load_yaml_model[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return model.model_validate(data)


def load_profile(path: Path) -> Profile:
    return _load_yaml_model(path, Profile)


def load_answer_bank(path: Path) -> AnswerBank:
    return _load_yaml_model(path, AnswerBank)
