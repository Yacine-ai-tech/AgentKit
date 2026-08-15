"""Multi-provider LLM routing with a real local-inference tier.

Every LLM call in AgentKit goes through `llm_call()` rather than talking to a provider
SDK directly, so switching providers — including to a model running on hardware you
control — is a config change, not a code change.

Tiers (each an env-configurable LiteLLM "provider/model" string):
    default    LLM_DEFAULT    high-volume work (tool-calling analyst)
    reasoning  LLM_REASONING  nuanced work (planner, reporter synthesis)
    judge      LLM_JUDGE      eval/scoring
    local      LLM_LOCAL      self-hosted (Ollama or any OpenAI-compatible server)

"Local" here means *inference on hardware you control*, not necessarily this machine —
never an assumption that a third-party cloud provider is the only option:

    INFERENCE_MODE=remote  (default)  use the hosted tier models above
    INFERENCE_MODE=local              force EVERY tier to LLM_LOCAL — no hosted
                                      provider is contacted and no provider API key
                                      is needed at all

    LLM_FALLBACK_TO_LOCAL=true        additionally, if a hosted call fails (outage,
                                      rate limit, missing/invalid key, network), retry
                                      once against the local tier instead of failing.
                                      Off by default: silently degrading model quality
                                      is a decision the operator should opt into.

The endpoint is fully env-driven, so the same code covers every deployment shape —
point `LOCAL_LLM_ENDPOINT` (or `OLLAMA_HOST`) at whichever you actually have:

  * Ollama on this machine ......... http://localhost:11434        (needs a local GPU)
  * Ollama on your own GPU box ..... http://192.168.1.50:11434     (LAN or via tunnel)
  * A shared inference orchestrator  https://<your-orchestrator>   + LOCAL_LLM_TOKEN
  * Any OpenAI-compatible server .... vLLM / llama.cpp / LM Studio / TGI

`LOCAL_LLM_TOKEN` sets the bearer token for endpoints that require auth (a shared
orchestrator will; a bare Ollama on localhost won't). Note the model prefix selects the
wire protocol LiteLLM speaks: `ollama/<model>` calls `/api/generate`, while
`ollama_chat/<model>` calls `/api/chat` — pick whichever your endpoint implements.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from agentkit_mcp.core.config import settings
from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)

try:
    from litellm import acompletion
    _LITELLM = True
except ImportError:  # pragma: no cover - exercised only in minimal installs
    _LITELLM = False
    log.warning("litellm not installed — LLM routing unavailable (pip install litellm)")


TIERS = ("default", "reasoning", "judge", "local")


class LLMUnavailable(RuntimeError):
    """Raised when a call cannot be completed. Carries the underlying provider error.

    Deliberately explicit: AgentKit never silently substitutes a canned answer for a
    failed model call, the same way the data tools never fabricate KPI numbers.
    """


def _tier_models() -> Dict[str, str]:
    return {
        "default": settings.LLM_DEFAULT,
        "reasoning": settings.LLM_REASONING,
        "judge": settings.LLM_JUDGE,
        "local": settings.LLM_LOCAL,
    }


def is_local_mode() -> bool:
    return (os.getenv("INFERENCE_MODE", settings.INFERENCE_MODE) or "remote").lower() == "local"


def fallback_enabled() -> bool:
    return os.getenv("LLM_FALLBACK_TO_LOCAL", "").lower() in ("1", "true", "yes")


def local_api_base() -> Optional[str]:
    """Base URL for the self-hosted endpoint, or None to use LiteLLM's default.

    OLLAMA_HOST is the conventional name and is what most self-hosters already set;
    LOCAL_LLM_ENDPOINT is accepted as an explicit alias for non-Ollama OpenAI-compatible
    servers (vLLM, llama.cpp, LM Studio, text-generation-webui, ...) and for a shared
    inference orchestrator fronting any of the above.
    """
    base = os.getenv("LOCAL_LLM_ENDPOINT") or os.getenv("OLLAMA_HOST") or None
    if not base:
        return None
    base = base.rstrip("/")
    # LiteLLM appends the protocol path itself (/api/chat for ollama_chat/*,
    # /api/generate for ollama/*), so a base that already ends in /api produces
    # //api/api/chat and a 404. Warn rather than rewrite — the operator should fix the
    # config, and silently rewriting could break a genuinely /api-rooted deployment.
    if base.endswith("/api"):
        log.warning(
            "local endpoint %r ends with '/api' — LiteLLM appends '/api/chat' itself, "
            "so this will request '%s/api/chat'. Use the base URL without '/api'.",
            base, base,
        )
    return base


def local_api_key() -> Optional[str]:
    """Bearer token for the self-hosted endpoint, if it requires one.

    A bare Ollama on localhost needs nothing; a shared orchestrator or anything exposed
    beyond your LAN will. Falls back to the global internal-service token so a
    deployment that already sets that doesn't need a second secret.
    """
    return (os.getenv("LOCAL_LLM_TOKEN") or
            os.getenv("INFERENCE_TOKEN") or
            os.getenv("AGENTKIT_INTERNAL_TOKEN") or
            None)


def resolve_model(tier: str = "default") -> str:
    """Model string actually used for `tier`, honoring INFERENCE_MODE=local."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r} — expected one of {TIERS}")
    if is_local_mode():
        return settings.LLM_LOCAL
    return _tier_models()[tier]


def describe_routing() -> Dict[str, Any]:
    """Introspection for /api/llm-routing and the UI — what would run, and where.

    Never includes API keys; only whether one is present.
    """
    local = is_local_mode()
    return {
        "inference_mode": "local" if local else "remote",
        "fallback_to_local": fallback_enabled(),
        "local_endpoint": local_api_base() or "litellm default (http://localhost:11434)",
        "local_endpoint_authenticated": bool(local_api_key()),
        "effective_models": {t: resolve_model(t) for t in TIERS},
        "configured_models": _tier_models(),
        "provider_keys_present": {
            "groq": bool(settings.GROQ_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
        },
        "litellm_installed": _LITELLM,
    }


async def _complete(model: str, messages: List[Dict[str, str]], **kwargs: Any):
    call: Dict[str, Any] = {"model": model, "messages": messages, **kwargs}
    # Point self-hosted models at the operator's own endpoint. Only for local-style
    # providers — never rewrite the base URL or inject the local token into a call
    # bound for a hosted provider.
    if model.startswith(("ollama/", "ollama_chat/", "openai/local", "hosted_vllm/")):
        base = local_api_base()
        if base:
            call["api_base"] = base
        key = local_api_key()
        if key:
            call["api_key"] = key
    return await acompletion(**call)


async def llm_call(messages: List[Dict[str, str]], *, tier: str = "default", **kwargs: Any):
    """Route one chat completion through the configured tier.

    Raises LLMUnavailable (never returns a fabricated response) when the call cannot be
    completed and no fallback succeeds.
    """
    if not _LITELLM:
        raise LLMUnavailable("litellm is not installed — pip install litellm")

    model = resolve_model(tier)
    try:
        return await _complete(model, messages, **kwargs)
    except Exception as primary_error:
        local_model = settings.LLM_LOCAL
        should_fallback = (fallback_enabled() and
                           not is_local_mode() and   # already local: nothing to fall back to
                           model != local_model)
        if not should_fallback:
            raise LLMUnavailable(f"{model} failed: {primary_error}") from primary_error

        log.warning("tier=%s model=%s failed (%s) — falling back to local %s",
                    tier, model, primary_error, local_model)
        try:
            return await _complete(local_model, messages, **kwargs)
        except Exception as local_error:
            raise LLMUnavailable(
                f"{model} failed ({primary_error}); local fallback {local_model} "
                f"also failed ({local_error})"
            ) from local_error
