from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SalaryExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    maximum: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    persona: str | None = None
    seniority: str | None = None
    years_exp: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    skills: list[NonEmptyString] = Field(default_factory=list)
    target_markets: list[NonEmptyString] = Field(default_factory=list)
    target_roles: list[NonEmptyString] = Field(default_factory=list)
    locations: list[NonEmptyString] = Field(default_factory=list)
    salary_expectations: dict[NonEmptyString, SalaryExpectation] = Field(default_factory=dict)
    notice_period_days: int | None = Field(default=None, ge=0)
    visa_status: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    languages: list[NonEmptyString] = Field(default_factory=list)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_canonical: NonEmptyString
    question_variants: list[NonEmptyString] = Field(default_factory=list)
    answer: NonEmptyString
    scope: Literal["global", "market", "company"] = "global"
    scope_value: NonEmptyString | None = None


class AnswerBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[Answer] = Field(default_factory=list)
