"""
Slim AgentKit configuration — env-driven, no monolith dependencies.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Centralized settings — read from environment."""

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    LOGS_DIR = str(LOGS_DIR)

    POSTGRES_URL = os.getenv(
        "POSTGRES_URL",
        "postgresql://agentkit:change_me@localhost:5432/agentkit",
    )

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    LLM_REASONING = os.getenv("LLM_REASONING", "anthropic/claude-sonnet-4-6")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")
    LLM_LOCAL = os.getenv("LLM_LOCAL", "ollama/llama3.3")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


settings = Settings()
