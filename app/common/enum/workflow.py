from enum import Enum


class NodeKind(str, Enum):
    START = "start"
    SCENE = "scene"
    BRANCH = "branch"
    MERGE = "merge"
    END = "end"


class EdgeKind(str, Enum):
    DEFAULT = "default"
    BRANCH = "branch"
