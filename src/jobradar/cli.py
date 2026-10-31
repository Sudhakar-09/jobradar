"""Command-line interface (`jobradar ...`) for developers and the operator."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel

from jobradar import accounts, admin, connectors, privacy
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


def _countries(args: argparse.Namespace) -> frozenset[str] | None:
    return frozenset(c.upper() for c in args.country) if args.country else None


def _print_checks(checks: Sequence[connectors.CompanyCheck]) -> None:
    print(f"{'company':<30}{'board':<34}{'status':<13}{'jobs':>6}{'in country':>12}")
    for check in checks:
        note = f"  {check.error}" if check.error else ""
        print(
            f"{check.name[:29]:<30}{(check.ats + '/' + check.slug)[:33]:<34}{check.status:<13}"
            f"{check.jobs_total:>6}{check.jobs_in_countries:>12}{note}"
        )
    verified = sum(1 for check in checks if check.status == "verified")
    cached = sum(1 for check in checks if check.status == "cached")
    checked = len(checks) - cached
    print(f"{verified} of {checked} boards checked list jobs in the chosen countries.")
    if cached:
        print(f"{cached} boards were checked in the last 24 hours (use --force to recheck).")


def _companies_verify(args: argparse.Namespace) -> int:
    countries = _countries(args)
    if args.file is not None:
        entries = connectors.load_company_file(args.file).companies
        checks = run(connectors.verify_entries(entries, countries=countries))
    else:
        checks = run(connectors.verify_companies(countries=countries, force=args.force))
    _print_checks(checks)
    return 0


def _read_names(args: argparse.Namespace) -> list[str]:
    names = list(args.names)
    if args.names_file is not None:
        lines = args.names_file.read_text(encoding="utf-8").splitlines()
        names.extend(line.strip() for line in lines if line.strip() and not line.startswith("#"))
    return list(dict.fromkeys(names))


def _write_candidates(
    path: Path, found: dict[str, connectors.CompanyCheck | None], countries: frozenset[str]
) -> None:
    today = datetime.now(UTC).date().isoformat()
    where = "/".join(sorted(countries))
    entries = [
        connectors.CompanyEntry.model_validate(
            {
                "name": check.name,
                "ats": check.ats,
                "ats_slug": check.slug,
                "countries": sorted(countries),
                "source": f"ats probe {today}: {check.jobs_in_countries} postings in {where}",
            }
        )
        for check in found.values()
        if check is not None and check.status == "verified"
    ]
    document = {"companies": [entry.model_dump(exclude_none=True) for entry in entries]}
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(entries)} verified boards to {path} for review.")


def _companies_probe(args: argparse.Namespace) -> int:
    names = _read_names(args)
    if not names:
        raise ValidationFailedError("give company names or --names-file")
    countries = _countries(args) or frozenset({"AE"})
    found = run(connectors.probe_companies(names, countries=countries))
    _print_checks([check for check in found.values() if check is not None])
    missing = [name for name, check in found.items() if check is None]
    if missing:
        print("No board found for: " + ", ".join(missing))
    if args.write is not None:
        _write_candidates(args.write, found, countries)
    return 0


def _suggestions_list(args: argparse.Namespace) -> int:
    status = None if args.status == "all" else args.status
    scope = _require_owner().scope()
    suggestions = run(connectors.list_company_suggestions(scope, status=status))
    if not suggestions:
        print("No company suggestions.")
    for item in suggestions:
        board = f"{item.detected_ats}/{item.detected_slug}" if item.detected_ats else "-"
        print(
            f"{item.id}  {item.company_name[:30]:<31}{board[:30]:<31}"
            f"seen {item.evidence_count:>3}x  {item.status}"
        )
    return 0


def _suggestions_probe(args: argparse.Namespace) -> int:
    countries = _countries(args) or frozenset({"AE"})
    scope = _require_owner().scope()
    updated = run(connectors.probe_company_suggestions(scope, countries=countries))
    for item in updated:
        print(f"{item.id}  {item.company_name}: {item.detected_ats}/{item.detected_slug}")
    print(f"Boards found for {len(updated)} suggestions. Review them before accepting.")
    return 0


def _suggestions_decide(args: argparse.Namespace) -> int:
    accept = args.subcommand == "accept"
    board = (args.ats, args.slug) if accept and args.ats and args.slug else None
    company = run(
        connectors.decide_company_suggestion(
            _require_owner().scope(),
            args.id,
            accept=accept,
            countries=args.country if accept else (),
            board=board,
        )
    )
    if company is None:
        print("Suggestion rejected.")
        return 0
    print(f"Added to the catalogue: {company.name} ({company.ats}/{company.ats_slug}).")
    print("To keep it in the curated list, add it to config/companies.yaml.")
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


def _packs_check(args: argparse.Namespace) -> int:
    reports = admin.conformance_reports()
    for report in reports:
        print(f"{report.kind:<8} {report.code:<16} {'PASS' if report.passed else 'FAIL'}")
        for check in report.failures():
            print(f"    {check.check}: {check.detail}")
    if args.json is not None:
        document = [
            {
                "kind": r.kind,
                "code": r.code,
                "passed": r.passed,
                "checks": [
                    {"check": c.check, "passed": c.passed, "detail": c.detail} for c in r.checks
                ],
            }
            for r in reports
        ]
        args.json.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return 0


def _parse_flag_value(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationFailedError(
            f'flag value must be JSON (true, false, 3, "x"): {text}'
        ) from exc


def _flags_set(args: argparse.Namespace) -> int:
    flag = run(admin.set_global_flag(args.key, _parse_flag_value(args.value), reason=args.reason))
    print(f"{flag.key} = {json.dumps(flag.value)}")
    return 0


def _flags_list(_args: argparse.Namespace) -> int:
    flags = run(admin.list_global_flags())
    if not flags:
        print("No global flags set.")
    for flag in flags:
        print(f"{flag.key} = {json.dumps(flag.value)}")
    return 0


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


def _alerts_ingest(args: argparse.Namespace) -> int:
    scope = _require_owner().scope()
    if args.subcommand == "reprocess":
        results = run(connectors.reprocess_unparsed(scope))
        if not results:
            print("No unparsed alert emails to read again.")
    else:
        results = run(connectors.ingest_alerts(scope))
        if not results:
            print("No active alert inbox. Connect one with: jobradar inbox connect gmail")
    for result in results:
        note = f" - {result.error}" if result.error else ""
        print(
            f"{result.connector}: {result.status}, {result.jobs_found} jobs "
            f"({result.jobs_new} new){note}"
        )
    return 1 if results and all(r.status == "failed" for r in results) else 0


def _add_admin_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    packs = commands.add_parser("packs", help="Market, role and persona packs")
    pack_commands = packs.add_subparsers(dest="subcommand", required=True)
    check = pack_commands.add_parser("check", help="Run the pack conformance suite")
    check.add_argument("--json", type=Path, help="Also write the report to this JSON file")
    check.set_defaults(handler=_packs_check)

    flags = commands.add_parser("flags", help="Global feature flags (audited)")
    flag_commands = flags.add_subparsers(dest="subcommand", required=True)
    flag_commands.add_parser("list", help="Show global flags").set_defaults(handler=_flags_list)
    setter = flag_commands.add_parser(
        "set", help="Set a flag; market/role enable flags need passing conformance"
    )
    setter.add_argument("key", help="e.g. market.germany.enabled")
    setter.add_argument("value", help="JSON value, e.g. true")
    setter.add_argument("--reason", required=True, help="Why (kept in the audit log)")
    setter.set_defaults(handler=_flags_set)


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


def _add_company_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    companies = commands.add_parser("companies", help="Manage the company catalogue")
    company_commands = companies.add_subparsers(dest="subcommand", required=True)
    company_commands.add_parser(
        "sync", help="Load config/companies.yaml into the database"
    ).set_defaults(handler=_companies_sync)
    country_help = "ISO country code to count jobs in (repeatable)"

    verify = company_commands.add_parser("verify", help="Check that company boards exist and hire")
    verify.add_argument("--file", type=Path, help="Check this YAML file instead of the catalogue")
    verify.add_argument("--country", action="append", help=country_help)
    verify.add_argument("--force", action="store_true", help="Ignore boards checked today")
    verify.set_defaults(handler=_companies_verify)

    probe = company_commands.add_parser("probe", help="Find ATS boards for company names")
    probe.add_argument("names", nargs="*", help="Company names")
    probe.add_argument("--names-file", type=Path, help="One company name per line")
    probe.add_argument("--country", action="append", help=country_help + " (default AE)")
    probe.add_argument("--write", type=Path, help="Write verified boards to this YAML file")
    probe.set_defaults(handler=_companies_probe)
    _add_suggestion_commands(company_commands, country_help)


def _add_suggestion_commands(
    company_commands: argparse._SubParsersAction[argparse.ArgumentParser], country_help: str
) -> None:
    suggestions = company_commands.add_parser("suggestions", help="Employers seen in your alerts")
    suggestion_commands = suggestions.add_subparsers(dest="subcommand", required=True)
    listing = suggestion_commands.add_parser("list", help="Show suggestions")
    listing.add_argument(
        "--status", choices=["pending", "accepted", "rejected", "all"], default="pending"
    )
    listing.set_defaults(handler=_suggestions_list)
    probe_pending = suggestion_commands.add_parser("probe", help="Find boards for suggestions")
    probe_pending.add_argument("--country", action="append", help=country_help + " (default AE)")
    probe_pending.set_defaults(handler=_suggestions_probe)
    accept = suggestion_commands.add_parser("accept", help="Add a suggestion to the catalogue")
    accept.add_argument("id", type=UUID)
    accept.add_argument("--country", action="append", required=True, help=country_help)
    accept.add_argument("--ats", choices=list(connectors.ATS_ORDER), help="Correct the ATS")
    accept.add_argument("--slug", help="Correct the board slug")
    accept.set_defaults(handler=_suggestions_decide)
    reject = suggestion_commands.add_parser("reject", help="Never suggest this employer again")
    reject.add_argument("id", type=UUID)
    reject.set_defaults(handler=_suggestions_decide)


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
    alert_commands.add_parser(
        "reprocess", help="Read again the alert emails no parser could read (after a fix)"
    ).set_defaults(handler=_alerts_ingest)


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

    _add_company_commands(commands)

    discover = commands.add_parser("discover", help="Fetch fresh jobs from every source")
    discover.add_argument("--source", help="Only this connector (e.g. greenhouse, alerts)")
    discover.add_argument("--company", type=UUID, help="Only this company id")
    discover.set_defaults(handler=_discover)
    _add_account_commands(commands)
    _add_admin_commands(commands)
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
