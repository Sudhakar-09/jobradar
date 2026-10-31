"""Command-line interface (`jobradar ...`) for developers and the operator."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from jobradar import accounts, connectors, privacy
from jobradar.connectors.gmail_oauth import run_consent_flow
from jobradar.core.aio import run
from jobradar.core.crypto import generate_key
from jobradar.core.errors import JobRadarError, ValidationFailedError
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


async def _discover_everything(
    source: str | None, company: UUID | None
) -> connectors.DiscoveryReport:
    """Company boards and aggregators, plus the owner's alert inbox (Stage 1)."""
    report = connectors.DiscoveryReport(runs=[], skipped=[])
    if source != "alerts":
        report = await connectors.discover(source=source, company_id=company)
    if source in (None, "alerts") and company is None:
        owner = await accounts.find_owner()
        if owner is None:
            report.skipped.append(connectors.Skipped("alerts", "no owner account yet"))
            return report
        try:
            report.runs.extend(await connectors.ingest_alerts(owner.scope()))
        except ValidationFailedError as exc:
            report.skipped.append(connectors.Skipped("alerts", str(exc)))
    return report


def _discover(args: argparse.Namespace) -> int:
    report = run(_discover_everything(args.source, args.company))
    for skipped in report.skipped:
        print(f"Skipped {skipped.connector}: {skipped.reason}")
    results = report.runs
    if not results:
        print(
            "No sources ran. Add companies to config/companies.yaml and run "
            "`jobradar companies sync`, or configure an aggregator."
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


def _users_bootstrap_owner(args: argparse.Namespace) -> int:
    owner = run(accounts.bootstrap_owner(args.email, timezone=args.timezone))
    print(f"Owner account created: {owner.user_id}")
    return 0


def _keys_generate(_args: argparse.Namespace) -> int:
    print("Add this line to .env (keep it secret; losing it means reconnecting inboxes):")
    print(f"TOKEN_ENCRYPTION_KEY={generate_key()}")
    return 0


def _require_owner() -> accounts.OwnerAccount:
    owner = run(accounts.find_owner())
    if owner is None:
        raise ValidationFailedError(
            "no owner account yet: run jobradar users bootstrap-owner --email you@example.org"
        )
    return owner


def _inbox_connect(_args: argparse.Namespace) -> int:
    settings = get_settings()
    owner = _require_owner()
    client_file = settings.google_oauth_client_file
    if client_file is None or not client_file.is_file():
        raise ValidationFailedError("set GOOGLE_OAUTH_CLIENT_FILE in .env to the client JSON path")
    if settings.token_encryption_key is None:
        raise ValidationFailedError("set TOKEN_ENCRYPTION_KEY in .env (jobradar keys generate)")
    text = privacy.consent_text("gmail_alerts")
    print(text.text)
    if input("Type yes to agree and open Google's sign-in: ").strip().lower() != "yes":
        print("Not connected.")
        return 1
    scope = owner.scope()
    gmail = connectors.gmail_settings()
    run(privacy.grant_consent(scope, text, technical_scope=[gmail.scope]))
    refresh_token = run_consent_flow(client_file, gmail.scope)
    inbox_id = run(connectors.connect_gmail_inbox(scope, refresh_token=refresh_token))
    print(f"Gmail connected (inbox {inbox_id}). Next: uv run jobradar alerts ingest")
    return 0


def _inbox_list(_args: argparse.Namespace) -> int:
    inboxes = run(connectors.list_inboxes(_require_owner().scope()))
    if not inboxes:
        print("No inboxes connected.")
    for inbox in inboxes:
        synced = inbox.last_synced_at.isoformat() if inbox.last_synced_at else "never"
        print(f"{inbox.id}  {inbox.kind:<10}{inbox.status:<17}last synced: {synced}")
    return 0


def _inbox_disconnect(args: argparse.Namespace) -> int:
    run(connectors.disconnect_inbox(_require_owner().scope(), args.id))
    print("Disconnected: access revoked, token deleted, consent ended.")
    return 0


def _alerts_ingest(_args: argparse.Namespace) -> int:
    results = run(connectors.ingest_alerts(_require_owner().scope()))
    if not results:
        print("No active alert inbox. Connect one with: jobradar inbox connect gmail")
    for result in results:
        note = f" - {result.error}" if result.error else ""
        print(
            f"{result.connector}: {result.status}, {result.jobs_found} jobs "
            f"({result.jobs_new} new){note}"
        )
    return 1 if results and all(r.status == "failed" for r in results) else 0


def _add_account_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    users = commands.add_parser("users", help="Manage accounts")
    user_commands = users.add_subparsers(dest="subcommand", required=True)
    bootstrap = user_commands.add_parser("bootstrap-owner", help="Create the owner account")
    bootstrap.add_argument("--email", required=True)
    bootstrap.add_argument("--timezone", default="Asia/Kolkata")
    bootstrap.set_defaults(handler=_users_bootstrap_owner)

    keys = commands.add_parser("keys", help="Encryption keys")
    key_commands = keys.add_subparsers(dest="subcommand", required=True)
    key_commands.add_parser("generate", help="Print a new TOKEN_ENCRYPTION_KEY").set_defaults(
        handler=_keys_generate
    )


def _add_inbox_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    inbox = commands.add_parser("inbox", help="Job-alert inbox (Gmail, read-only)")
    inbox_commands = inbox.add_subparsers(dest="subcommand", required=True)
    connect = inbox_commands.add_parser("connect", help="Connect Gmail after your consent")
    connect.add_argument("kind", choices=["gmail"])
    connect.set_defaults(handler=_inbox_connect)
    inbox_commands.add_parser("list", help="Show connected inboxes").set_defaults(
        handler=_inbox_list
    )
    disconnect = inbox_commands.add_parser("disconnect", help="Revoke access and delete the token")
    disconnect.add_argument("--id", type=UUID, required=True)
    disconnect.set_defaults(handler=_inbox_disconnect)

    alerts = commands.add_parser("alerts", help="Job-alert emails")
    alert_commands = alerts.add_subparsers(dest="subcommand", required=True)
    alert_commands.add_parser("ingest", help="Read new alert emails now").set_defaults(
        handler=_alerts_ingest
    )


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

    discover = commands.add_parser("discover", help="Fetch fresh jobs from every source")
    discover.add_argument("--source", help="Only this connector (e.g. greenhouse, alerts)")
    discover.add_argument("--company", type=UUID, help="Only this company id")
    discover.set_defaults(handler=_discover)
    _add_account_commands(commands)
    _add_inbox_commands(commands)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = _build_parser().parse_args(argv)
    configure_logging(get_settings().log_level)
    handler: Handler = args.handler
    try:
        return handler(args)
    except JobRadarError as exc:
        print(f"Error: {exc}")
        return 2
