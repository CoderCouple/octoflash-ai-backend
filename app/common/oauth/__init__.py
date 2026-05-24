"""OAuth scaffolding shared by every publishing-target platform.

Public surface:

  * `PlatformConfig` — per-platform URL set + scope list + credentials accessor.
  * `PLATFORM_CONFIGS` — registry keyed by `TargetPlatform`.
  * `make_state` / `verify_state` — short-TTL signed token that binds the
    OAuth round-trip to (user_id, platform, optional pkce verifier).

The actual orchestration (build authorize URL, exchange code, fetch
userinfo) lives in `app.service.oauth_service.OAuthService`.
"""

from app.common.oauth.config import (
    PlatformConfig,
    PLATFORM_CONFIGS,
    NormalizedAccount,
    get_redirect_uri,
)
from app.common.oauth.state import make_state, verify_state, InvalidStateError

__all__ = [
    "PlatformConfig",
    "PLATFORM_CONFIGS",
    "NormalizedAccount",
    "get_redirect_uri",
    "make_state",
    "verify_state",
    "InvalidStateError",
]
