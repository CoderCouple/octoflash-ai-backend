"""Source = the user's INPUT library (channels they pull source material FROM).
Distinct from Target, which is publishing destinations.
"""

from enum import Enum
from urllib.parse import urlparse


class SourcePlatform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    X = "x"           # formerly Twitter; both x.com and twitter.com map here
    LINKEDIN = "linkedin"


class SourceVideoKind(str, Enum):
    SHORT = "short"
    LANDSCAPE = "landscape"


# Mapping from lowercased host (with leading `www.` stripped) → platform.
# Add domains here as new ingestion paths get wired up.
_PLATFORM_DOMAINS: dict[str, SourcePlatform] = {
    "youtube.com":   SourcePlatform.YOUTUBE,
    "youtu.be":      SourcePlatform.YOUTUBE,
    "m.youtube.com": SourcePlatform.YOUTUBE,
    "instagram.com": SourcePlatform.INSTAGRAM,
    "tiktok.com":    SourcePlatform.TIKTOK,
    "vm.tiktok.com": SourcePlatform.TIKTOK,
    "x.com":         SourcePlatform.X,
    "twitter.com":   SourcePlatform.X,
    "linkedin.com":  SourcePlatform.LINKEDIN,
}


def detect_platform(url: str) -> SourcePlatform | None:
    """Identify the platform from a URL's hostname.

    Returns None when the host isn't in our map — the caller should
    surface a clear error rather than guessing.
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return None
    if host.startswith("www."):
        host = host[4:]
    return _PLATFORM_DOMAINS.get(host)
