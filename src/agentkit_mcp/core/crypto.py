"""Cryptographic utilities for encrypting and decrypting sensitive credentials in Postgres storage."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from agentkit_mcp.core.config import settings


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte urlsafe base64 key from a secret string."""
    h = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(h)


def get_fernet() -> Fernet:
    """Get Fernet cipher instance using dynamically resolved environment secrets."""
    secret = (
        os.getenv("SECRET_KEY")
        or os.getenv("AGENTKIT_INTERNAL_TOKEN")
        or os.getenv("MCP_AUTH_TOKEN")
        or settings.POSTGRES_URL
    )
    if not secret:
        # Fail closed: there is no safe default key — a hardcoded fallback would let
        # anyone decrypt stored credentials. Require an explicit deployment secret.
        raise RuntimeError(
            "AgentKit storage encryption requires a secret: set SECRET_KEY "
            "(or AGENTKIT_INTERNAL_TOKEN / MCP_AUTH_TOKEN / POSTGRES_URL)"
        )
    key = _derive_key(secret)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string using Fernet symmetric encryption."""
    f = get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token string to plaintext."""
    f = get_fernet()
    pt = f.decrypt(token.encode("utf-8"))
    return pt.decode("utf-8")
