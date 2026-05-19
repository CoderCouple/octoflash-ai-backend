"""
Primitive registry — id → Primitive class.

Populated via the @register decorator at primitive-module import time.
The renderer dispatches steps by looking up `step.primitive` here.
"""

from __future__ import annotations

from typing import TypeVar

from app.templates.primitives.base import Primitive

PRIMITIVES: dict[str, type[Primitive]] = {}

P = TypeVar("P", bound=type[Primitive])


def register(cls: P) -> P:
    """Decorator — registers a Primitive subclass at import time."""
    if not getattr(cls, "PRIMITIVE_ID", None):
        raise TypeError(f"{cls.__name__} must define PRIMITIVE_ID")
    if cls.PRIMITIVE_ID in PRIMITIVES:
        raise ValueError(
            f"Duplicate primitive id: {cls.PRIMITIVE_ID!r} "
            f"({cls.__name__} vs {PRIMITIVES[cls.PRIMITIVE_ID].__name__})"
        )
    PRIMITIVES[cls.PRIMITIVE_ID] = cls
    return cls


def get_primitive(primitive_id: str) -> type[Primitive] | None:
    return PRIMITIVES.get(primitive_id)


def primitive_versions() -> dict[str, str]:
    """Snapshot of {primitive_id: version} for audit logging."""
    return {pid: cls.PRIMITIVE_VERSION for pid, cls in PRIMITIVES.items()}
