"""Diagnostic kept for the record (CLAUDE.md rule 12; not run in CI, not linted).

Lists only the From addresses (no subjects or bodies) of messages from job-board domains in the
owner's connected Gmail over the last 10 days, to find the real alert sender addresses for
`config/alert_senders.yaml`. Used on 2026-11-06: it showed Naukri, Instahyre and Foundit alerts
were arriving from addresses the config did not list. Run from the repo root with the owner
account connected: uv run python scripts/archive/alert_sender_check.py
"""
from collections import Counter
from jobradar import accounts
from jobradar.connectors.config import policy_registry
from jobradar.connectors.gmail import GmailAlertInbox, load_oauth_client
from jobradar.connectors.repository import AlertInboxRepository
from jobradar.connectors.service.alerts import _oauth_client_path, _secret_box, gmail_settings
from jobradar.core.aio import run
from jobradar.core.db import user_session
from jobradar.core.http import PoliteClient
from jobradar.core.settings import get_settings
from jobradar.core.source_policies import AccessMode

DOMAINS = ["naukri.com", "naukrigulf.com", "bayt.com", "gulftalent.com", "instahyre.com",
           "foundit.in", "indeed.com", "stepstone.de", "xing.com", "linkedin.com"]

async def main():
    owner = await accounts.find_owner()
    async with user_session(owner.scope()) as s:
        inbox = (await AlertInboxRepository(s).active())[0]
        sealed = inbox.oauth_token_enc
    g = gmail_settings()
    async with PoliteClient(policy_registry(), get_settings()) as http:
        gm = GmailAlertInbox(http, g, load_oauth_client(_oauth_client_path()),
                             _secret_box().decrypt(sealed).decode(), [])
        token = await gm.access_token()
        q = "from:(" + " OR ".join(DOMAINS) + ") newer_than:10d"
        ids, page = [], None
        while len(ids) < 300:
            params = {"q": q, "maxResults": 100}
            if page: params["pageToken"] = page
            body = await gm._get(g.messages_url, token, params)
            ids += [m["id"] for m in body.get("messages", [])]
            page = body.get("nextPageToken")
            if not page: break
        senders = Counter()
        for mid in ids:
            body = await gm._get(g.message_url.format(id=mid), token,
                                 {"format": "metadata", "metadataHeaders": "From"})
            frm = next((h["value"] for h in body["payload"]["headers"] if h["name"].lower() == "from"), "?")
            addr = frm.split("<")[-1].rstrip(">").strip().lower()
            senders[addr] += 1
        for addr, n in senders.most_common():
            print(f"{n:>4}  {addr}")
run(main())
