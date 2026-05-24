"""OAuthService — orchestrates the Authorization Code (+ PKCE) flow for all
publishing-target platforms.

Two entry points used by controllers:

  * `build_authorize_url(platform, user_id) → (url, state)` — what the FE
    redirects the browser to when "Connect <Platform>" is clicked.

  * `complete(platform, code, state) → (NormalizedAccount, TokenBlob)` —
    called by the callback endpoint. Exchanges `code` for tokens, fetches
    the connected-account profile, returns both so TargetService can upsert.

PKCE: when `config.use_pkce` is True we generate a 32-byte random verifier
on the way out and stash it inside the signed state token. On the way back
the verifier is recovered from state and posted to the token endpoint.

Per-platform quirks isolated to `_token_payload()`:
  * TikTok uses `client_key` rather than `client_id` in token body
  * Most platforms accept `client_id` in form body when `token_auth_method='body'`
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.common.enum.target import TargetPlatform
from app.common.exceptions import EntityNotFoundError
from app.common.oauth.config import (
    NormalizedAccount,
    PLATFORM_CONFIGS,
    PlatformConfig,
    get_redirect_uri,
)
from app.common.oauth.state import make_state, verify_state
from app.settings import settings

log = logging.getLogger(__name__)


@dataclass
class TokenBlob:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scope: str | None
    token_type: str | None
    raw: dict[str, Any]               # full response for forward-compat


class OAuthError(Exception):
    """Raised when an OAuth step fails in a way the controller should surface
    as a non-500 (typically 502 to the FE since the failing call is outbound)."""


class OAuthNotConfiguredError(OAuthError):
    """Platform's client_id / client_secret is empty in settings."""


class OAuthService:
    # ── public ────────────────────────────────────────────────────────────

    def build_authorize_url(
        self, *, platform: TargetPlatform, user_id: str,
    ) -> tuple[str, str]:
        """Return (authorize_url, state).

        Raises OAuthNotConfiguredError when the platform's settings are blank.
        """
        config = _config_or_500(platform)
        client_id, _ = config.credentials()
        if not client_id:
            raise OAuthNotConfiguredError(
                f"{platform.value!r} OAuth not configured — set the client_id / "
                f"client_secret env vars (see app/settings.py)."
            )

        code_verifier: str | None = None
        params: dict[str, str] = {
            "response_type": "code",
            "client_id": client_id if platform != TargetPlatform.TIKTOK else "",
            "redirect_uri": _redirect_uri(platform),
            "scope": " ".join(config.scopes),
        }
        if platform == TargetPlatform.TIKTOK:
            # TikTok rejects empty client_id but wants `client_key` instead.
            params.pop("client_id", None)
            params["client_key"] = client_id

        if config.use_pkce:
            code_verifier = _gen_verifier()
            params["code_challenge"] = _challenge(code_verifier)
            params["code_challenge_method"] = "S256"

        params.update(config.extra_authorize_params)

        state = make_state(
            user_id=user_id, platform=platform, code_verifier=code_verifier,
        )
        params["state"] = state

        url = f"{config.authorize_url}?{urlencode(params, safe='/:')}"
        log.info(
            "OAuthService.build_authorize_url: platform=%s user=%s pkce=%s",
            platform.value, user_id, config.use_pkce,
        )
        return url, state

    async def complete(
        self, *, platform: TargetPlatform, code: str, state: str,
    ) -> tuple[NormalizedAccount, TokenBlob, str]:
        """Run code → tokens → userinfo. Returns (account, tokens, user_id)."""
        decoded = verify_state(state)
        if decoded.platform != platform:
            raise OAuthError(
                f"State platform mismatch: state says {decoded.platform.value}, "
                f"path says {platform.value}"
            )

        config = _config_or_500(platform)
        token_blob = await self._exchange_code(
            config=config,
            code=code,
            code_verifier=decoded.code_verifier,
        )

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                account: NormalizedAccount = await config.fetch_account(
                    client, token_blob.access_token,
                )
            except httpx.HTTPError as e:
                log.warning(
                    "OAuthService.complete: userinfo fetch failed for %s: %s",
                    platform.value, e,
                )
                raise OAuthError(
                    f"{platform.value} userinfo fetch failed: {e}"
                ) from e
        if not account.external_id:
            raise OAuthError(
                f"{platform.value} returned a token but no usable account id."
            )
        return account, token_blob, decoded.user_id

    # ── internals ─────────────────────────────────────────────────────────

    async def _exchange_code(
        self, *, config: PlatformConfig, code: str, code_verifier: str | None,
    ) -> TokenBlob:
        client_id, client_secret = config.credentials()
        if not client_id or not client_secret:
            raise OAuthNotConfiguredError(
                f"{config.platform.value!r} OAuth credentials missing."
            )

        body, headers = self._token_payload(
            config=config,
            code=code,
            code_verifier=code_verifier,
            client_id=client_id,
            client_secret=client_secret,
        )

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(config.token_url, data=body, headers=headers)
        if r.status_code >= 400:
            log.warning(
                "OAuthService._exchange_code: %s token endpoint returned %s: %s",
                config.platform.value, r.status_code, r.text[:500],
            )
            raise OAuthError(
                f"{config.platform.value} token exchange failed: "
                f"HTTP {r.status_code} {r.text[:200]}"
            )

        # TikTok wraps the token under .data for v2; everything else returns flat.
        body_json = r.json()
        if config.platform == TargetPlatform.TIKTOK and "data" in body_json:
            data = body_json["data"]
        else:
            data = body_json

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
            raw=body_json,
        )

    @staticmethod
    def _token_payload(
        *,
        config: PlatformConfig,
        code: str,
        code_verifier: str | None,
        client_id: str,
        client_secret: str,
    ) -> tuple[dict[str, str], dict[str, str]]:
        body: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(config.platform),
        }
        if code_verifier and config.use_pkce:
            body["code_verifier"] = code_verifier

        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if config.platform == TargetPlatform.TIKTOK:
            # TikTok wants client_key (not client_id) + client_secret in the body.
            body["client_key"] = client_id
            body["client_secret"] = client_secret
        elif config.token_auth_method == "basic":
            # `Authorization: Basic base64(id:secret)` — Bearer auth on token endpoint.
            pair = f"{client_id}:{client_secret}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(pair).decode()
            # X still requires client_id in the body even with Basic auth.
            if config.platform == TargetPlatform.X:
                body["client_id"] = client_id
        else:
            body["client_id"] = client_id
            body["client_secret"] = client_secret
        return body, headers


# ─── helpers ───────────────────────────────────────────────────────────────

def _config_or_500(platform: TargetPlatform) -> PlatformConfig:
    config = PLATFORM_CONFIGS.get(platform)
    if config is None:
        raise EntityNotFoundError("PlatformConfig", platform.value)
    return config


def _redirect_uri(platform: TargetPlatform) -> str:
    return get_redirect_uri(platform)


def _gen_verifier() -> str:
    """RFC 7636 §4.1 — 43–128 chars, URL-safe."""
    return secrets.token_urlsafe(64)[:128]


def _challenge(verifier: str) -> str:
    """RFC 7636 §4.2 — BASE64URL-NOPAD(SHA256(verifier))."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
