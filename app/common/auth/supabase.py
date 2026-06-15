"""Supabase Auth JWT verification.

Backend doesn't host login/signup — `@supabase/supabase-js` on the FE
does. Here we verify incoming Bearer tokens with the project's HS256
JWT secret + check the standard claims.

Supabase end-user tokens look like:

    {
      "iss":  "https://<ref>.supabase.co/auth/v1",
      "sub":  "<auth.users.id — UUID>",
      "aud":  "authenticated",
      "email": "user@example.com",
      "role": "authenticated",
      "exp":  ...,
      ...
    }

The `sub` is what we persist on `user.auth_sub` and key user lookups by
on every subsequent request.

HS256 with the shared secret is the simplest verification path. Supabase
recently shipped asymmetric (ES256 + JWKS) too; if we ever move to that
we'd swap _ALGORITHM + plumb a JWKS fetcher here. Caller surface stays
the same.
"""

import logging
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_ALGORITHM = "HS256"
_AUDIENCE = "authenticated"


async def decode_supabase_token(token: str) -> dict[str, Any]:
    """Decode + validate a Supabase JWT.

    Verifies HS256 signature, exp, issuer, and audience. Returns the
    decoded claims dict on success; raises HTTPException(401) on failure.
    """
    if not settings.supabase_jwt_secret:
        # Refuse fast rather than letting jwt.decode raise a generic
        # InvalidSignatureError that's harder to triage in logs.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_JWT_SECRET unset)",
        )

    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[_ALGORITHM],
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
