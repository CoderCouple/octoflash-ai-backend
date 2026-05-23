"""Public OAuth callback handler — mounted at root, no JWT.

OAuth providers redirect the browser back to `/oauth/callback/{platform}`
after consent. The bearer token isn't carried in that redirect, so this
router lives outside the JWT-protected `/api/v1` tree.

State is the only auth that ties the callback back to the user — it's a
signed JWT we minted on the way out (`app.common.oauth.state.make_state`).

Success path:
  exchange code → fetch userinfo → upsert Target + Credential
  → 302 to `{frontend_url}/targets?connected=<target_id>`

Failure path:
  → 302 to `{frontend_url}/targets?error=<short_code>&detail=<urlencoded_message>`

Both paths redirect (instead of JSON) so the user lands somewhere usable
on the FE rather than seeing a raw API response in the address bar.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enum.target import TargetPlatform
from app.common.oauth.state import InvalidStateError
from app.db.session import get_db
from app.service.oauth_service import OAuthError, OAuthService
from app.service.target_service import TargetService
from app.settings import settings

router = APIRouter(prefix="/oauth", tags=["OAuth"], include_in_schema=False)

log = logging.getLogger(__name__)


def _redirect_to_fe(*, target_id: str | None = None, error: str | None = None,
                   detail: str | None = None) -> RedirectResponse:
    """Bounce the browser back to the FE with the outcome encoded in query
    params. Status 303 so the address bar doesn't show the API host on
    subsequent navigation."""
    params: dict[str, str] = {}
    if target_id:
        params["connected"] = target_id
    if error:
        params["error"] = error
    if detail:
        params["detail"] = detail
    qs = ("?" + urlencode(params)) if params else ""
    return RedirectResponse(
        url=f"{settings.frontend_url.rstrip('/')}/targets{qs}",
        status_code=303,
    )


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: TargetPlatform,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Public OAuth redirect target. See module docstring."""
    # Provider denied / user canceled → bounce to FE with the platform's error.
    if error:
        log.info(
            "oauth_callback: platform=%s provider-error=%s desc=%s",
            platform.value, error, error_description,
        )
        return _redirect_to_fe(error=error, detail=error_description)

    if not code or not state:
        return _redirect_to_fe(
            error="missing_code_or_state",
            detail="Provider didn't return both `code` and `state`.",
        )

    oauth = OAuthService()
    try:
        account, tokens, user_id = await oauth.complete(
            platform=platform, code=code, state=state,
        )
    except InvalidStateError as e:
        return _redirect_to_fe(error="invalid_state", detail=str(e))
    except OAuthError as e:
        return _redirect_to_fe(error="oauth_failed", detail=str(e))
    except Exception as e:  # noqa: BLE001 — last-ditch safety net
        log.exception("oauth_callback: unexpected failure for %s", platform.value)
        return _redirect_to_fe(error="internal", detail=str(e))

    target = await TargetService(db).upsert_from_oauth(
        user_id=user_id,
        platform=platform,
        account=account,
        tokens=tokens,
    )
    return _redirect_to_fe(target_id=target.id)
