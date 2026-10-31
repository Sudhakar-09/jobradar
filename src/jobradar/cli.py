"""Command-line interface (`jobradar ...`) for developers and the operator."""

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from jobradar import connectors
from jobradar.core.aio import run
from jobradar.core.logging import configure_logging
from jobradar.core.settings import get_settings
from jobradar.profile.loaders import load_profile
from jobradar.profile.text_parser import parse_resume_text

Handler = Callable[[argparse.Namespace], int]


def _print_profile(profile: BaseModel) -> None:
    print(json.dumps(profile.model_dump(mode="json"), indent=2, ensure_ascii=False))


def _profile_show(args: argparse.Namespace) -> int:
    _print_profile(load_profile(args.profile))
    return 0


def _profile_parse_resume(args: argparse.Namespace) -> int:
    _print_profile(parse_resume_text(args.path.read_text(encoding="utf-8")))
    return 0


def _companies_sync(_args: argparse.Namespace) -> int:
    counts = run(connectors.sync_companies())
    print(f"Companies synced: {counts.created} new, {counts.updated} updated.")
    return 0


def _discover(args: argparse.Namespace) -> int:
    results = run(connectors.discover(source=args.source, company_id=args.company))
    if not results:
        print(
            "No company boards to run. Add companies to config/companies.yaml and run "
            "`jobradar companies sync`."
        )
        return 0
    print(f"{'source':<16}{'company':<28}{'status':<10}{'found':>6}{'new':>6}{'upd':>6}{'bad':>6}")
    for result in results:
        print(
            f"{result.connector:<16}{(result.company_name or '-')[:27]:<28}{result.status:<10}"
            f"{result.jobs_found:>6}{result.jobs_new:>6}{result.jobs_updated:>6}"
            f"{result.items_invalid:>6}"
        )
    totals = sum(r.jobs_found for r in results), sum(r.jobs_new for r in results)
    print(f"Total: {totals[0]} jobs found, {totals[1]} new, across {len(results)} runs.")
    all_failed = all(result.status == "failed" for result in results)
    return 1 if all_failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobradar")
    commands = parser.add_subparsers(dest="command", required=True)

    profile = commands.add_parser("profile", help="Inspect or parse a candidate profile")
    profile_commands = profile.add_subparsers(dest="subcommand", required=True)
    show = profile_commands.add_parser("show", help="Validate and display a profile YAML file")
    show.add_argument(
        "--profile",
        type=Path,
        default=Path("config/profile.example.yaml"),
        help="Profile YAML path (default: config/profile.example.yaml)",
    )
    show.set_defaults(handler=_profile_show)
    parse_resume = profile_commands.add_parser(
        "parse-resume", help="Parse explicitly labeled fields from a plain-text resume"
    )
    parse_resume.add_argument("path", type=Path, help="UTF-8 plain-text resume path")
    parse_resume.set_defaults(handler=_profile_parse_resume)

    companies = commands.add_parser("companies", help="Manage the company catalogue")
    company_commands = companies.add_subparsers(dest="subcommand", required=True)
    company_commands.add_parser(
        "sync", help="Load config/companies.yaml into the database"
    ).set_defaults(handler=_companies_sync)

    discover = commands.add_parser("discover", help="Fetch fresh jobs from company boards")
    discover.add_argument("--source", help="Only this connector (e.g. greenhouse)")
    discover.add_argument("--company", type=UUID, help="Only this company id")
    discover.set_defaults(handler=_discover)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = _build_parser().parse_args(argv)
    configure_logging(get_settings().log_level)
    handler: Handler = args.handler
    return handler(args)
