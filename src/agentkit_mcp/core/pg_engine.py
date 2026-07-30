"""
PostgreSQL database engine — replaces SQLite + DuckDB.

Uses SQLAlchemy 2.0 async engine with connection pooling.
Falls back to SQLite for development/testing without Docker.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://agentkit:change_me@localhost:5432/agentkit"
)

POSTGRES_ASYNC_URL = POSTGRES_URL.replace(
    "postgresql+psycopg://", "postgresql+asyncpg://"
).replace(
    "postgresql://user:password@localhost/verified")
