"""Supabase Auth JWT verification — asymmetric (JWKS).

Backend doesn't host login/signup — `@supabase/supabase-js` on the FE
does. Here we verify incoming Bearer tokens against the project's
public JWKS endpoint.

Newer Supabase projects sign tokens with ECC (P-256, alg=ES256) or
RSA (alg=RS256) by default. Public keys are served at:

    {SUPABASE_URL}/auth/v1/.well-known/jwks.json

We cache that JSON for an hour and force-refresh on a `kid` miss —
same pattern the prior Cognito verifier used, ported across.

End-user tokens look like:

    {
      "iss":  "https://<ref>.supabase.co/auth/v1",
      "sub":  "<auth.users.id — UUID>",
      "aud":  "authenticated",
      "email": "user@example.com",
      "role": "authenticated",
      "exp":  ...,
      ...
    }

The `sub` is what we persist on `user.auth_sub`.

Legacy HS256 mode (a single shared `JWT_SECRET`) is no longer
supported here — flip the project to asymmetric in Supabase dashboard
→ Project Settings → JWT Keys, or pin this back to HS256 by reverting
to the previous version of this file.
"""

import logging
import time
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_AUDIENCE = "authenticated"

# JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0
_JWKS_CACHE_TTL = 3600  # 1 hour


def _jwks_url() -> str:
    """The URL Supabase publishes the current + standby public keys at.
    Derived from SUPABASE_URL so a project move (rare) only requires the
    one env var update."""
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the Supabase JWKS."""
    global _jwks_cache, _jwks_cache_expiry

    now = time.monotonic()
    if _jwks_cache and now < _jwks_cache_expiry:
        return _jwks_cache

    url = _jwks_url()
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_expiry = now + _JWKS_CACHE_TTL

    logger.info("Refreshed Supabase JWKS from %s", url)
    return _jwks_cache


def _find_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _force_jwks_refresh() -> None:
    global _jwks_cache_expiry
    _jwks_cache_expiry = 0


def _public_key_from_jwk(jwk: dict[str, Any]):
    """Build a PyJWT-compatible public key from the JWK's `kty`. Supabase
    rotates between ECC (kty=EC) and RSA (kty=RSA) per project config."""
    kty = jwk.get("kty")
    if kty == "EC":
        return jwt.algorithms.ECAlgorithm.from_jwk(jwk)
    if kty == "RSA":
        return jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unsupported JWK kty: {kty}",
    )


async def decode_supabase_token(token: str) -> dict[str, Any]:
    """Decode + validate a Supabase JWT against the project's JWKS.

    Verifies the asymmetric signature (ES256 / RS256), exp, issuer, and
    audience. Returns the decoded claims dict on success; raises
    HTTPException(401) on failure.
    """
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_URL unset)",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg")
    if not kid or not alg:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing kid / alg",
        )

    jwks = await _get_jwks()
    jwk_data = _find_key(jwks, kid)
    if not jwk_data:
        # kid rotation — force-refresh JWKS once and retry.
        _force_jwks_refresh()
        jwks = await _get_jwks()
        jwk_data = _find_key(jwks, kid)
        if not jwk_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signing key not found",
            )

    public_key = _public_key_from_jwk(jwk_data)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            issuer=settings.supabase_issuer,
            audience=_AUDIENCE,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    return claims


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — requires a valid Supabase JWT. Returns claims dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await decode_supabase_token(credentials.credentials)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any] | None:
    """FastAPI dependency — returns claims dict if valid JWT present, else None."""
    if credentials is None:
        return None
    try:
        return await decode_supabase_token(credentials.credentials)
    except HTTPException:
        return None
