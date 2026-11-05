"""Short-lived browser session tokens for the web facade.

The static internal token is a service-to-service credential and must never be
shipped inside the frontend bundle. Browsers exchange it once at
``POST /api/v1/auth/login`` for an HMAC-signed, expiring session token instead.

Token format: ``<base64url(expiry_unix)>.<base64url(hmac_sha256)>`` — signed
with a key derived from the deployment's internal token, so no extra secret
needs to be provisioned. Verification is constant-time and expiry-checked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

DEFAULT_TTL_S = 12 * 60 * 60


def _anchor() -> str:
    return (
        os.getenv("AGENTKIT_INTERNAL_TOKEN")
        or os.getenv("INTERNAL_TOKEN")
        or os.getenv("OMNIINTEL_INTERNAL_TOKEN")
        or ""
    ).strip()


def _signing_key() -> bytes | None:
    anchor = _anchor()
    if not anchor:
        return None
    return hashlib.sha256(b"agentkit-session-v1:" + anchor.encode()).digest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload: str, key: bytes) -> str:
    return _b64e(hmac.new(key, payload.encode(), hashlib.sha256).digest())


def issue_session_token(ttl_s: int | None = None) -> tuple[str, int]:
    """Return ``(token, ttl_seconds)``. Raises RuntimeError when no signing
    anchor is configured (i.e. internal-token auth is not provisioned)."""
    key = _signing_key()
    if key is None:
        raise RuntimeError("session tokens unavailable: no internal token configured")
    ttl = ttl_s if ttl_s is not None else int(os.getenv("AGENTKIT_SESSION_TTL_S", str(DEFAULT_TTL_S)))
    payload = _b64e(str(int(time.time()) + ttl).encode())
    return f"{payload}.{_sign(payload, key)}", ttl


def verify_session_token(token: str) -> bool:
    """True when ``token`` is a well-formed, unexpired session token."""
    key = _signing_key()
    if key is None or not token or "." not in token:
        return False
    try:
        payload, sig = token.rsplit(".", 1)
        expected = _sign(payload, key)
        if not hmac.compare_digest(sig, expected):
            return False
        exp = int(_b64d(payload).decode())
        return exp > int(time.time())
    except Exception:
        return False
