"""Symmetric encryption + masking for credential vault values.

Production wiring uses Fernet (AES-128-CBC + HMAC) keyed by
`settings.credential_encryption_key` — a base64-encoded 32-byte key.
Generate one with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

When the key is empty (dev default) values round-trip in plain text and a
warning is logged on first use. We still gate read paths through `mask()` so
the API never returns raw secrets to the UI regardless of storage mode.

Stored blobs are prefixed so we can tell encrypted vs. plaintext rows apart
during a future key rotation — `enc:v1:<fernet-token>` vs. `plain:<value>`.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.settings import settings

_log = logging.getLogger(__name__)

_ENC_PREFIX = "enc:v1:"
_PLAIN_PREFIX = "plain:"

_warned = False


@lru_cache(maxsize=1)
def _fernet() -> Fernet | None:
    key = (settings.credential_encryption_key or "").strip()
    if not key:
        return None
    return Fernet(key.encode())


def _warn_if_unset() -> None:
    global _warned
    if _warned:
        return
    if _fernet() is None:
        _log.warning(
            "CREDENTIAL_ENCRYPTION_KEY is unset — credential values will be "
            "stored in plaintext. Set a Fernet key in production."
        )
    _warned = True


def encrypt(value: str) -> str:
    """Encrypt a raw secret for storage. Returns a prefixed blob."""
    _warn_if_unset()
    fernet = _fernet()
    if fernet is None:
        return f"{_PLAIN_PREFIX}{value}"
    token = fernet.encrypt(value.encode()).decode()
    return f"{_ENC_PREFIX}{token}"


def decrypt(blob: str) -> str:
    """Reverse `encrypt`. Tolerates legacy plain rows + handles prefix
    transitions during a future key rotation."""
    if blob.startswith(_ENC_PREFIX):
        fernet = _fernet()
        if fernet is None:
            raise RuntimeError(
                "Credential blob is encrypted but CREDENTIAL_ENCRYPTION_KEY is unset"
            )
        try:
            return fernet.decrypt(blob[len(_ENC_PREFIX) :].encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("Could not decrypt credential — wrong key?") from exc
    if blob.startswith(_PLAIN_PREFIX):
        return blob[len(_PLAIN_PREFIX) :]
    # Legacy rows written before prefix scheme — assume plain.
    return blob


def mask(value: str) -> str:
    """Render a secret for UI display — keeps last 4 chars, prefix length up
    to 3, rest as bullets. Empty / short inputs become a generic placeholder
    so we don't accidentally reveal that a secret is short."""
    if not value:
        return ""
    if len(value) <= 6:
        return "••••••"
    head = value[:3]
    tail = value[-4:]
    return f"{head}{'•' * 8}{tail}"
