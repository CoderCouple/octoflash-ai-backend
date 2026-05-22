"""Cognito JWT verification.

Backend doesn't host login/signup — Cognito Hosted UI does. Here we only
verify incoming Bearer tokens against the User Pool's JWKS, cache the keys
for an hour, and force-refresh on a `kid` miss (handles key rotation).
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

# JWKS cache
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0
_JWKS_CACHE_TTL = 3600  # 1 hour


async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the Cognito JWKS (JSON Web Key Set)."""
    global _jwks_cache, _jwks_cache_expiry

    now = time.monotonic()
    if _jwks_cache and now < _jwks_cache_expiry:
        return _jwks_cache

    url = settings.cognito_jwks_url
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_expiry = now + _JWKS_CACHE_TTL

    logger.info("Refreshed Cognito JWKS from %s", url)
    return _jwks_cache


def _find_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key
    return None


def _force_jwks_refresh() -> None:
    global _jwks_cache_expiry
    _jwks_cache_expiry = 0


async def decode_cognito_token(token: str) -> dict[str, Any]:
    """Decode + validate a Cognito JWT.

    Verifies RS256 signature, exp, issuer, and audience (app client id).
    Returns the decoded claims dict on success; raises HTTPException(401) on failure.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        ) from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing key ID",
        )

    jwks = await _get_jwks()
    jwk_data = _find_key(jwks, kid)
    if not jwk_data:
        _force_jwks_refresh()
        jwks = await _get_jwks()
        jwk_data = _find_key(jwks, kid)
        if not jwk_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signing key not found",
            )

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk_data)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.cognito_issuer,
            audience=settings.cognito_app_client_id,
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
    """FastAPI dependency — requires a valid Cognito JWT. Returns claims dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await decode_cognito_token(credentials.credentials)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any] | None:
    """FastAPI dependency — returns claims dict if valid JWT present, else None."""
    if credentials is None:
        return None
    try:
        return await decode_cognito_token(credentials.credentials)
    except HTTPException:
        return None
