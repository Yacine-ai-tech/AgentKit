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
    "postgresql://", "postgresql+asyncpg://"
)

# Sync engine — for migrations, init, and simple scripts
sync_engine = create_engine(
    POSTGRES_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)

# Async engine — for FastAPI request handling
try:
    async_engine = create_async_engine(
        POSTGRES_ASYNC_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    _ASYNC_AVAILABLE = True
except Exception as e:
    log.warning("Async engine not available: %s — using sync only", e)
    async_engine = None
    AsyncSessionLocal = None
    _ASYNC_AVAILABLE = False


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all ORM models."""
    pass


# ── Dependency injection for FastAPI ───────────────────────────────────────

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    if not _ASYNC_AVAILABLE or AsyncSessionLocal is None:
        raise RuntimeError("Async database engine not available")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get a synchronous database session."""
    return SyncSessionLocal()


# ── Health check ───────────────────────────────────────────────────────────

def check_database_health() -> dict:
    """Check PostgreSQL connectivity and return status."""
    try:
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "healthy", "engine": "postgresql", "url": POSTGRES_URL.split("@")[-1]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ── Init ───────────────────────────────────────────────────────────────────

def init_database():
    """Create all tables from ORM models (if not using schema.sql)."""
    from models import pg_models  # noqa: F401
    Base.metadata.create_all(bind=sync_engine)
    log.info("PostgreSQL tables created/verified")
