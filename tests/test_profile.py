import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from jobradar.cli import main
from jobradar.profile.loaders import load_answer_bank, load_profile
from jobradar.profile.models import Profile
from jobradar.profile.text_parser import parse_resume_text

ROOT = Path(__file__).resolve().parents[1]


def test_load_example_profile() -> None:
    profile = load_profile(ROOT / "config" / "profile.example.yaml")

    assert profile == Profile()


def test_load_answer_bank(tmp_path: Path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "answers": [
                    {
                        "question_canonical": "Why this role?",
                        "question_variants": ["Why are you interested?"],
                        "answer": "A verified, user-provided answer.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    answer_bank = load_answer_bank(path)

    assert answer_bank.answers[0].scope == "global"
    assert answer_bank.answers[0].answer == "A verified, user-provided answer."


def test_profile_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text("name: Example\nunknown: value\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_profile(path)


def test_profile_loader_requires_yaml_mapping(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mapping"):
        load_profile(path)


def test_resume_parser_extracts_only_explicitly_labeled_fields() -> None:
    profile = parse_resume_text(
        "Jordan Example\n"
        "Name: Jordan Example\n"
        "Years of Experience: 4.5 years\n"
        "Skills: Python, SQL; PostgreSQL\n"
        "Target Roles: Software Engineer\n"
        "Worked on a team of 10.\n"
    )

    assert profile.name == "Jordan Example"
    assert profile.years_exp == 4.5
    assert profile.skills == ["Python", "SQL", "PostgreSQL"]
    assert profile.target_roles == ["Software Engineer"]
    assert profile.locations == []


def test_resume_parser_rejects_ambiguous_explicit_value() -> None:
    with pytest.raises(ValueError, match="years of experience"):
        parse_resume_text("Years of Experience: several years")


def test_resume_parser_rejects_duplicate_fields() -> None:
    with pytest.raises(ValueError, match="more than once"):
        parse_resume_text("Name: One\nFull Name: Two")


def test_profile_show_cli_prints_validated_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["profile", "show"])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["target_markets"] == []
    assert output["skills"] == []


def test_profile_parse_resume_cli_reads_plain_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    resume = tmp_path / "resume.txt"
    resume.write_text("Name: Jordan Example\nSkills: Python, SQL\n", encoding="utf-8")

    result = main(["profile", "parse-resume", str(resume)])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["name"] == "Jordan Example"
    assert output["skills"] == ["Python", "SQL"]
