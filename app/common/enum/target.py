"""Target = the user's OUTPUT destinations (accounts they post the final video TO).
Distinct from Source, which is the input library.
"""

from enum import Enum


class TargetPlatform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"


class TargetStatus(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
