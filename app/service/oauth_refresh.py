"""Token refresh helper — call before any platform-API request.

`load_fresh_token(credential, platform)` returns a valid `TokenBlob`,
refreshing via the platform's `token_url` if the stored access token has
expired (with a 60-second buffer). On refresh it re-encrypts the new blob
and persists it back to the Credential row.

Most platforms (Google, LinkedIn, TikTok, Meta, X) issue refresh tokens via
the same `grant_type=refresh_token` form. We post that, parse the response,
update the stored blob. If the refresh itself fails (most often: refresh
token revoked by the user), the caller gets `OAuthError` and the surrounding
publish flow surfaces it as a 401 → FE prompts a reconnect.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.common.enum.target import TargetPlatform
from app.common.oauth.config import PLATFORM_CONFIGS, PlatformConfig
from app.common.security.secret_crypto import decrypt, encrypt
from app.db.repository.credential_repository import CredentialRepository
from app.model.credential_model import Credential
from app.service.oauth_service import OAuthError, TokenBlob

log = logging.getLogger(__name__)

_REFRESH_BUFFER_SECONDS = 60


def read_blob(credential: Credential) -> TokenBlob:
    """Decrypt the credential row + parse the stored JSON into a TokenBlob.

    Credential `value` is Fernet-encrypted JSON written by
    `TargetService.upsert_from_oauth`. Plaintext (dev-mode) credential
    blobs are tolerated by `decrypt()`.
    """
    raw = decrypt(credential.value)
    data = json.loads(raw)
    expires_at_raw = data.get("expires_at")
    return TokenBlob(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=datetime.fromisoformat(expires_at_raw) if expires_at_raw else None,
        scope=data.get("scope"),
        token_type=data.get("token_type"),
        raw=data,
    )


async def load_fresh_token(
    *,
    credential: Credential,
    platform: TargetPlatform,
    credential_repo: CredentialRepository,
) -> TokenBlob:
    """Return a TokenBlob whose access_token is valid for at least 60 s.

    If `credential` already has time left, no network call is made. If the
    token is expired (or expires within the buffer), the platform's refresh
    endpoint is called; on success the new blob is re-encrypted and saved
    via `credential_repo.update`.
    """
    blob = read_blob(credential)
    if not _needs_refresh(blob):
        return blob

    if not blob.refresh_token:
        raise OAuthError(
            f"{platform.value} access token expired and no refresh_token "
            "is stored. Reconnect the target."
        )

    config = PLATFORM_CONFIGS.get(platform)
    if config is None:
        raise OAuthError(f"No OAuth config registered for platform {platform.value}")
    refreshed = await _refresh(blob.refresh_token, config)

    # The refresh response may or may not include a NEW refresh_token (Google
    # doesn't rotate; some do). Preserve the existing one when the platform
    # didn't return one — losing it would force the user to reconnect.
    new_refresh = refreshed.refresh_token or blob.refresh_token

    new_blob_dict = {
        "access_token":  refreshed.access_token,
        "refresh_token": new_refresh,
        "expires_at":    refreshed.expires_at.isoformat() if refreshed.expires_at else None,
        "scope":         refreshed.scope or blob.scope,
        "token_type":    refreshed.token_type or blob.token_type,
    }
    credential.value = encrypt(json.dumps(new_blob_dict))
    await credential_repo.update(credential)
    log.info(
        "oauth_refresh: refreshed %s token for credential=%s expires_at=%s",
        platform.value, credential.id, new_blob_dict["expires_at"],
    )
    refreshed.refresh_token = new_refresh
    return refreshed


# ── internals ──────────────────────────────────────────────────────────────

def _needs_refresh(blob: TokenBlob) -> bool:
    if blob.expires_at is None:
        # No expiry was stored — assume long-lived. Platforms with no expiry
        # (some LinkedIn flows) effectively skip refresh until a 401 forces
        # a reconnect.
        return False
    deadline = datetime.now(timezone.utc) + timedelta(seconds=_REFRESH_BUFFER_SECONDS)
    return blob.expires_at <= deadline


async def _refresh(refresh_token: str, config: PlatformConfig) -> TokenBlob:
    """Hit the platform's token endpoint with grant_type=refresh_token.

    Auth method (basic vs body) follows the same per-platform rules used
    on the initial code-exchange — see OAuthService._token_payload.
    """
    import base64

    client_id, client_secret = config.credentials()
    body: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    if config.platform == TargetPlatform.TIKTOK:
        body["client_key"] = client_id
        body["client_secret"] = client_secret
    elif config.token_auth_method == "basic":
        pair = f"{client_id}:{client_secret}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(pair).decode()
        if config.platform == TargetPlatform.X:
            body["client_id"] = client_id
    else:
        body["client_id"] = client_id
        body["client_secret"] = client_secret

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(config.token_url, data=body, headers=headers)
    if r.status_code >= 400:
        raise OAuthError(
            f"{config.platform.value} token refresh failed: "
            f"HTTP {r.status_code} {r.text[:200]}"
        )

    raw = r.json()
    if config.platform == TargetPlatform.TIKTOK and "data" in raw:
        data = raw["data"]
    else:
        data = raw

    expires_in = data.get("expires_in")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        if expires_in is not None else None
    )
    return TokenBlob(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=expires_at,
        scope=data.get("scope"),
        token_type=data.get("token_type"),
        raw=raw,
    )
