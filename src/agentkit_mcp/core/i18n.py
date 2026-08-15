"""Minimal i18n shim for AgentKit.

The BI services (`insights.py`, `forecasting.py`) are
bilingual. AgentKit defaults to English and doesn't need the full localization framework, so it runs English-only —
this provides the same ``I18N.lang()`` + ``t(section, key)`` API those modules import, with
``lang()`` fixed to English. (In the services, ``t(...)`` is only invoked on the French
branch, which never runs here.)
"""
from __future__ import annotations


class I18N:
    """English-only stand-in for I18N (class-level API: ``I18N.lang()``)."""

    @classmethod
    def lang(cls) -> str:
        return "en"

    @classmethod
    def set_lang(cls, *args, **kwargs) -> None:  # no-op (English only)
        return None


def t(section: str, key: str, default: str = "") -> str:
    """Translation lookup stub — returns the explicit default, else the key."""
    return default or key
