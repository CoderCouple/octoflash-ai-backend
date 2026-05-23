"""Signed state token for the OAuth round-trip.

The `state` query param has two jobs:

  1. **CSRF** — bind the callback back to the user who started the flow.
  2. **PKCE carry** — for platforms that require PKCE (X) we generate
     `code_verifier` on the way out and need it again on the way in.
     Stashing it in `state` saves us a session store.

Implemented as a short-TTL JWT. Signed with `settings.oauth_state_secret`
(falls back to `credential_encryption_key` so dev works without two keys).
TTL is 10 minutes — enough for a human to consent, not enough for a stolen
URL to be useful.

Format:
    state = jwt.encode({
        "uid":  user_id,
        "plt":  platform.value,
        "cv":   code_verifier or None,
        "exp":  now + 600s,
        "iat":  now,
    })
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt

from app.common.enum.target import TargetPlatform
from app.settings import settings


class InvalidStateError(Exception):
    """Raised when a callback's `state` doesn't decode / verify / match."""


@dataclass
class OAuthState:
    user_id: str
    platform: TargetPlatform
    code_verifier: str | None


_ALG = "HS256"
_TTL_SECONDS = 600


def _key() -> str:
    raw = settings.oauth_state_secret or settings.credential_encryption_key
    if not raw:
        # Dev fallback — deterministic per-process so tests work, but
        # a deploy without either key is essentially unauthenticated.
        return "octoflash-dev-oauth-state-fallback"
    return raw


def make_state(
    *,
    user_id: str,
    platform: TargetPlatform,
    code_verifier: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "uid": user_id,
        "plt": platform.value,
        "cv":  code_verifier,
        "iat": now,
        "exp": now + _TTL_SECONDS,
    }
    return jwt.encode(payload, _key(), algorithm=_ALG)


def verify_state(token: str) -> OAuthState:
    try:
        payload = jwt.decode(token, _key(), algorithms=[_ALG])
    except jwt.ExpiredSignatureError as e:
        raise InvalidStateError("OAuth state expired — restart the connect flow.") from e
    except jwt.InvalidTokenError as e:
        raise InvalidStateError(f"OAuth state invalid: {e}") from e
    try:
        platform = TargetPlatform(payload["plt"])
    except (KeyError, ValueError) as e:
        raise InvalidStateError(f"OAuth state carries unknown platform: {e}") from e
    user_id = payload.get("uid")
    if not user_id:
        raise InvalidStateError("OAuth state missing user_id")
    return OAuthState(
        user_id=user_id,
        platform=platform,
        code_verifier=payload.get("cv"),
    )
