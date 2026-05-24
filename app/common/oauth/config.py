"""Per-platform OAuth configuration registry.

Each entry describes one platform's Authorization Code flow + how to parse
its userinfo response into the shape `TargetService.upsert_from_oauth` wants.

Adding a 6th platform = adding one PlatformConfig + bumping the
TargetPlatform enum + (optionally) a settings field for its client_id/secret.

Today's set: youtube, tiktok, instagram, linkedin, x.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from app.common.enum.target import TargetPlatform
from app.settings import settings


# Shape returned to TargetService for upsert. Every platform's userinfo
# response is normalized to this.
@dataclass
class NormalizedAccount:
    external_id: str             # the platform's stable account id
    handle: str | None           # @username if available
    display_name: str | None
    avatar_url: str | None


@dataclass
class PlatformConfig:
    platform: TargetPlatform
    authorize_url: str
    token_url: str
    scopes: list[str]
    # Some platforms (X) REQUIRE PKCE. Others (TikTok, LinkedIn, Google)
    # accept it but don't require it. We default ON when supported so the
    # state token doubles as a CSRF + integrity check.
    use_pkce: bool = False
    # Most platforms send `Authorization: Basic base64(id:secret)` for the
    # token exchange. A few (TikTok v2) want client_key + client_secret in
    # the form body. This switch picks the auth method per platform.
    token_auth_method: str = "basic"   # 'basic' | 'body'
    # Returns the (client_id, client_secret) tuple from settings — passing a
    # callable rather than baking strings means the registry stays static
    # while settings hot-reloads cleanly under uvicorn --reload.
    credentials: Callable[[], tuple[str, str]] = field(
        default=lambda: ("", ""),
    )
    # Async fetcher that pulls the connected-account profile using the
    # access_token returned from `token_url`, then normalizes it.
    fetch_account: Callable[[httpx.AsyncClient, str], "Any"] = field(
        default=lambda c, t: _not_implemented(),
    )
    # Some authorize endpoints need extra query params (Google offline +
    # consent prompt, X PKCE method, IG response_type).
    extra_authorize_params: dict[str, str] = field(default_factory=dict)


async def _not_implemented() -> NormalizedAccount:
    raise NotImplementedError("fetch_account is not configured for this platform")


# ─── per-platform account fetchers ──────────────────────────────────────────
# Each receives an authenticated httpx.AsyncClient + the access_token, makes
# one or two requests against the platform's userinfo endpoint, and returns
# a NormalizedAccount. Errors propagate to the controller as 502.

async def _fetch_youtube(client: httpx.AsyncClient, token: str) -> NormalizedAccount:
    """`channels.list?mine=true` returns the authenticated user's YouTube channel."""
    r = await client.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet,statistics", "mine": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    items = r.json().get("items") or []
    if not items:
        raise RuntimeError("Google returned no YouTube channel for this account.")
    ch = items[0]
    sn = ch.get("snippet") or {}
    return NormalizedAccount(
        external_id=ch.get("id") or "",
        handle=(sn.get("customUrl") or "").lstrip("@") or None,
        display_name=sn.get("title"),
        avatar_url=((sn.get("thumbnails") or {}).get("high") or {}).get("url"),
    )


async def _fetch_tiktok(client: httpx.AsyncClient, token: str) -> NormalizedAccount:
    r = await client.get(
        "https://open.tiktokapis.com/v2/user/info/",
        params={"fields": "open_id,union_id,avatar_url,display_name,username"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    user = (r.json().get("data") or {}).get("user") or {}
    return NormalizedAccount(
        external_id=user.get("open_id") or user.get("union_id") or "",
        handle=user.get("username"),
        display_name=user.get("display_name"),
        avatar_url=user.get("avatar_url"),
    )


async def _fetch_instagram(client: httpx.AsyncClient, token: str) -> NormalizedAccount:
    # Instagram OAuth goes through Facebook. The token authorizes a Facebook
    # user; we look up the user's pages, then the Instagram Business Account
    # linked to the first page. Multi-page accounts: surfacing a picker is
    # a follow-up.
    pages = await client.get(
        "https://graph.facebook.com/v18.0/me/accounts",
        params={"access_token": token, "fields": "id,name,instagram_business_account"},
    )
    pages.raise_for_status()
    data = pages.json().get("data") or []
    page = next((p for p in data if p.get("instagram_business_account")), None)
    if page is None:
        raise RuntimeError(
            "No Instagram Business account found on this Facebook user. "
            "Link an Instagram Business account to a Facebook Page first."
        )
    ig_id = page["instagram_business_account"]["id"]
    ig = await client.get(
        f"https://graph.facebook.com/v18.0/{ig_id}",
        params={"access_token": token, "fields": "id,username,name,profile_picture_url"},
    )
    ig.raise_for_status()
    info = ig.json()
    return NormalizedAccount(
        external_id=str(info.get("id")),
        handle=info.get("username"),
        display_name=info.get("name") or info.get("username"),
        avatar_url=info.get("profile_picture_url"),
    )


async def _fetch_linkedin(client: httpx.AsyncClient, token: str) -> NormalizedAccount:
    # OIDC userinfo (works for the modern `openid + profile + email` scope set
    # and the legacy `r_liteprofile`-based one if Connect is mixed). Returns
    # the member's URN; we strip the urn prefix so external_id is just the id.
    r = await client.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    data = r.json()
    return NormalizedAccount(
        external_id=str(data.get("sub") or "").removeprefix("urn:li:person:") or "",
        handle=None,                  # LinkedIn doesn't surface a public @handle
        display_name=data.get("name") or
                     (f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
                      or None),
        avatar_url=data.get("picture"),
    )


async def _fetch_x(client: httpx.AsyncClient, token: str) -> NormalizedAccount:
    r = await client.get(
        "https://api.twitter.com/2/users/me",
        params={"user.fields": "username,name,profile_image_url"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    user = (r.json().get("data") or {})
    return NormalizedAccount(
        external_id=user.get("id") or "",
        handle=user.get("username"),
        display_name=user.get("name"),
        avatar_url=user.get("profile_image_url"),
    )


# ─── registry ───────────────────────────────────────────────────────────────
# Reads settings lazily — settings.* references inside `credentials` are
# evaluated at call time, so a settings hot-reload under uvicorn --reload
# picks up new client_ids without re-importing.

PLATFORM_CONFIGS: dict[TargetPlatform, PlatformConfig] = {
    TargetPlatform.YOUTUBE: PlatformConfig(
        platform=TargetPlatform.YOUTUBE,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        use_pkce=False,
        token_auth_method="body",   # Google accepts both; body is simpler
        credentials=lambda: (
            settings.youtube_client_id,
            settings.youtube_client_secret,
        ),
        fetch_account=_fetch_youtube,
        # `access_type=offline` + `prompt=consent` forces Google to return a
        # refresh_token even when the user has already consented once.
        extra_authorize_params={"access_type": "offline", "prompt": "consent"},
    ),

    TargetPlatform.TIKTOK: PlatformConfig(
        platform=TargetPlatform.TIKTOK,
        authorize_url="https://www.tiktok.com/v2/auth/authorize/",
        token_url="https://open.tiktokapis.com/v2/oauth/token/",
        scopes=["user.info.basic", "video.publish", "video.upload"],
        use_pkce=True,
        token_auth_method="body",
        credentials=lambda: (
            settings.tiktok_client_key,
            settings.tiktok_client_secret,
        ),
        fetch_account=_fetch_tiktok,
        # TikTok docs spell the parameter "client_key" (not client_id). We
        # rename it in the OAuthService.build_authorize_url path below.
    ),

    TargetPlatform.INSTAGRAM: PlatformConfig(
        platform=TargetPlatform.INSTAGRAM,
        authorize_url="https://www.facebook.com/v18.0/dialog/oauth",
        token_url="https://graph.facebook.com/v18.0/oauth/access_token",
        scopes=[
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "pages_read_engagement",
        ],
        use_pkce=False,
        token_auth_method="body",
        # Meta calls them "app_id / app_secret" rather than client_id/secret —
        # the OAuth wire format still uses client_id, so the OAuthService
        # passes ig_app_id as the client_id query/body param.
        credentials=lambda: (
            settings.ig_app_id,
            settings.ig_app_secret,
        ),
        fetch_account=_fetch_instagram,
    ),

    TargetPlatform.LINKEDIN: PlatformConfig(
        platform=TargetPlatform.LINKEDIN,
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        # The OIDC scope set powers the v2/userinfo endpoint. `w_member_social`
        # is the publishing scope (post share + ugcPost).
        scopes=["openid", "profile", "email", "w_member_social"],
        use_pkce=False,
        token_auth_method="body",
        credentials=lambda: (
            settings.linkedin_client_id,
            settings.linkedin_client_secret,
        ),
        fetch_account=_fetch_linkedin,
    ),

    TargetPlatform.X: PlatformConfig(
        platform=TargetPlatform.X,
        authorize_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth/token",
        # `offline.access` for refresh tokens. `media.write` for video upload
        # via the v1.1 media endpoint (X still routes media uploads there).
        scopes=[
            "tweet.read",
            "tweet.write",
            "users.read",
            "media.write",
            "offline.access",
        ],
        use_pkce=True,                # X REQUIRES PKCE
        token_auth_method="basic",
        credentials=lambda: (
            settings.x_client_id,
            settings.x_client_secret,
        ),
        fetch_account=_fetch_x,
    ),
}


# Per-platform redirect_uri lookup. The platform's developer console must
# have the exact value registered (scheme + host + path). The OAuthService
# reads from here when building the authorize URL and posting the token
# exchange, so a single env-var change rolls out cleanly per platform.
def get_redirect_uri(platform: TargetPlatform) -> str:
    return {
        TargetPlatform.YOUTUBE:   settings.youtube_redirect_uri,
        TargetPlatform.TIKTOK:    settings.tiktok_redirect_uri,
        TargetPlatform.INSTAGRAM: settings.ig_redirect_uri,
        TargetPlatform.LINKEDIN:  settings.linkedin_redirect_uri,
        TargetPlatform.X:         settings.x_redirect_uri,
    }[platform]
