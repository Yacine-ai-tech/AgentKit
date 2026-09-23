import asyncio

import pytest

from agentkit_mcp.core import llm_router as lr
from agentkit_mcp.core.config import settings


def _rate_limit_error(wait_s: float) -> Exception:
    return lr.RateLimitError(
        message=f"Rate limit reached. Please try again in {wait_s}s.",
        llm_provider="groq",
        model="openai/gpt-oss-120b",
    )


def test_rate_limit_wait_s_parses_provider_hint():
    exc = _rate_limit_error(8.5)
    assert lr._rate_limit_wait_s(exc) == pytest.approx(8.5)


def test_rate_limit_wait_s_falls_back_to_default_when_unparseable():
    assert lr._rate_limit_wait_s(Exception("some other error")) == pytest.approx(10.0)


class _FakeResponse:
    class _Choice:
        class _Message:
            content = "ok"

        message = _Message()

    choices = [_Choice()]


def test_complete_retries_on_rate_limit_then_succeeds(monkeypatch):
    """Real bug found via eval/run_dspy_eval.py's multi-domain suite: a transient
    provider rate limit produced a silently empty report instead of retrying — this
    covers the fix (llm_router._complete_with_rate_limit_retry)."""
    calls = {"n": 0}

    async def _fake_complete(model, messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _rate_limit_error(0.01)  # tiny wait so the test stays fast
        return _FakeResponse()

    monkeypatch.setattr(lr, "_complete", _fake_complete)
    resp = asyncio.run(lr._complete_with_rate_limit_retry("groq/openai/gpt-oss-120b", []))
    assert resp.choices[0].message.content == "ok"
    assert calls["n"] == 2  # one failure, one successful retry


def test_complete_exhausts_retries_and_raises(monkeypatch):
    calls = {"n": 0}

    async def _always_rate_limited(model, messages, **kwargs):
        calls["n"] += 1
        raise _rate_limit_error(0.01)

    monkeypatch.setattr(lr, "_complete", _always_rate_limited)
    monkeypatch.setattr(settings, "LLM_RATE_LIMIT_RETRIES", 2)
    with pytest.raises(lr.RateLimitError):
        asyncio.run(lr._complete_with_rate_limit_retry("groq/openai/gpt-oss-120b", []))
    assert calls["n"] == 3  # initial attempt + 2 retries


def test_complete_does_not_retry_non_rate_limit_errors(monkeypatch):
    """A genuine failure (bad key, network error) should still fail fast, not spend
    the rate-limit retry budget on an unrelated error class."""
    calls = {"n": 0}

    async def _always_broken(model, messages, **kwargs):
        calls["n"] += 1
        raise ValueError("not a rate limit")

    monkeypatch.setattr(lr, "_complete", _always_broken)
    with pytest.raises(ValueError):
        asyncio.run(lr._complete_with_rate_limit_retry("groq/openai/gpt-oss-120b", []))
    assert calls["n"] == 1
