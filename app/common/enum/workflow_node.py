"""Node-type library / prop schema enums.

`NodePropGroup` classifies a prop as input (user-supplied), output (produced),
or readonly (system-set). `NodePropType` is its scalar type.
"""

from enum import Enum


class NodePropGroup(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    READONLY = "readonly"


class NodePropType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
