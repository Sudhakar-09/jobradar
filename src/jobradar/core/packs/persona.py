"""Persona pack schema: strategy defaults per job-seeker situation (PRD §4.3)."""

import math
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from jobradar.core.packs.common import NonEmptyString, PackModel, Slug

CHANNEL_WEIGHT_TOLERANCE: Final = 1e-6


class PersonaPack(PackModel):
    """Persona configuration: channel weights, volume, tailoring and follow-up defaults."""

    code: Slug
    description: NonEmptyString
    channel_weights: dict[Slug, float]
    daily_volume_range: tuple[int, int]
    tailoring_depth: Literal["light", "medium", "deep"]
    resume_strategy: NonEmptyString
    onboarding_steps: list[Slug]
    followup_days: list[int] = Field(min_length=1)
    default_llm_top_n: int = Field(ge=1, le=50)
    default_min_fit_score: int = Field(ge=0, le=100)
    tips: list[NonEmptyString]

    @model_validator(mode="after")
    def _check_persona(self) -> Self:
        if any(weight < 0 for weight in self.channel_weights.values()):
            raise ValueError("channel weights must be non-negative")
        if not math.isclose(
            sum(self.channel_weights.values()), 1.0, abs_tol=CHANNEL_WEIGHT_TOLERANCE
        ):
            raise ValueError("channel weights must sum to 1")
        low, high = self.daily_volume_range
        if not 0 <= low <= high:
            raise ValueError("daily_volume_range must be (min, max) with 0 <= min <= max")
        if self.followup_days != sorted(set(self.followup_days)) or self.followup_days[0] < 1:
            raise ValueError("followup_days must be increasing positive day counts")
        return self
