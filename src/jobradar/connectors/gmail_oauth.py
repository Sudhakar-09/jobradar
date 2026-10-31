"""Interactive Gmail consent (operator CLI only): opens Google's sign-in in the browser."""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


def run_consent_flow(client_file: Path, scope: str) -> str:  # pragma: no cover - interactive
    """Run Google's installed-app consent in the browser and return the refresh token.

    The local redirect listener runs on a random free port on 127.0.0.1 and stops afterwards.
    """
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes=[scope])
    credentials = flow.run_local_server(
        host="localhost", port=0, open_browser=True, prompt="consent", access_type="offline"
    )
    refresh_token = getattr(credentials, "refresh_token", None)
    if not isinstance(refresh_token, str) or not refresh_token:
        raise RuntimeError("Google returned no refresh token; remove the app's access and retry")
    return refresh_token
