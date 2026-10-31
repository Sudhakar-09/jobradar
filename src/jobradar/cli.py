"""Command-line interface (`jobradar ...`) for developers and the operator."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from jobradar.profile.loaders import load_profile
from jobradar.profile.text_parser import parse_resume_text


def _print_profile(profile: BaseModel) -> None:
    print(json.dumps(profile.model_dump(mode="json"), indent=2, ensure_ascii=False))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobradar")
    commands = parser.add_subparsers(dest="command", required=True)
    profile = commands.add_parser("profile", help="Inspect or parse a candidate profile")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)

    show = profile_commands.add_parser("show", help="Validate and display a profile YAML file")
    show.add_argument(
        "--profile",
        type=Path,
        default=Path("config/profile.example.yaml"),
        help="Profile YAML path (default: config/profile.example.yaml)",
    )

    parse_resume = profile_commands.add_parser(
        "parse-resume",
        help="Parse explicitly labeled fields from a plain-text resume",
    )
    parse_resume.add_argument("path", type=Path, help="UTF-8 plain-text resume path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = _build_parser().parse_args(argv)
    if args.command == "profile" and args.profile_command == "show":
        _print_profile(load_profile(args.profile))
    elif args.command == "profile" and args.profile_command == "parse-resume":
        text = args.path.read_text(encoding="utf-8")
        _print_profile(parse_resume_text(text))
    return 0
