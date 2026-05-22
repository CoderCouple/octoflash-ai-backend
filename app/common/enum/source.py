"""Source = the user's INPUT library (channels they pull source material FROM).
Distinct from Target, which is publishing destinations.
"""

from enum import Enum


class SourcePlatform(str, Enum):
    YOUTUBE = "youtube"


class SourceVideoKind(str, Enum):
    SHORT = "short"
    LANDSCAPE = "landscape"
