"""
Slim AgentKit configuration — env-driven, no monolith dependencies.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# parents[3] = repo root (core -> agentkit_mcp -> src -> root). A no-op if the file
# isn't there (e.g. `pip install agentkit-mcp` usage, which relies on real env vars
# instead of a .env file).
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Centralized settings — read from environment."""

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    LOGS_DIR = str(LOGS_DIR)

    POSTGRES_URL = os.getenv("POSTGRES_URL", "")

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/openai/gpt-oss-120b")
    LLM_REASONING = os.getenv("LLM_REASONING", "anthropic/claude-sonnet-4-6")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")
    LLM_LOCAL = os.getenv("LLM_LOCAL", "ollama/llama3.3")

    INFERENCE_MODE = os.getenv("INFERENCE_MODE", "remote")
    LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")
    LLM_TOKEN = os.getenv("LLM_TOKEN", "")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


settings = Settings()
