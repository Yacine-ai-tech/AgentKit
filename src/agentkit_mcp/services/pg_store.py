"""
PostgreSQL Data Store — Single source of truth for the entire platform.

Handles all persistence:
  - User accounts (auth, roles, preferences)
  - KPI metrics (analytics, multi-domain)
  - Knowledge base (documents, embeddings)
  - Conversation history (per session, cross-session memory)
  - Chat sessions metadata
  - Audit trail
  - Monitoring logs
"""
from __future__ import annotations
from datetime import datetime

import uuid
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row
import pandas as pd

try:
    from src.core.config import settings
    from src.core.logger import get_logger
except ImportError:
    from agentkit_mcp.core.config import settings
    from agentkit_mcp.core.logger import get_logger


log = get_logger(__name__)

_pool = None
_pool_lock = None


def _init_pool():
    """Initialize a persistent connection pool for Neon PostgreSQL.

    This is the #2 fix for IntelAI latency. Previously every DB call created a
    fresh TCP+TLS connection to Neon (2-4s each). With pool=3 min connections,
    subsequent calls reuse existing connections (<50ms overhead).
    """
    global _pool, _pool_lock
    if _pool is not None:
        return _pool
    import threading
    if _pool_lock is None:
        _pool_lock = threading.Lock()
    with _pool_lock:
        if _pool is not None:
            return _pool
        try:
            from psycopg_pool import ConnectionPool
            _pool = ConnectionPool(
                settings.POSTGRES_URL,
                min_size=2,
                max_size=8,
                kwargs={"row_factory": dict_row},
                open=False,
                reconnect_timeout=30,
                reconnect_failed=None,
            )
            # Open the pool in the background so it doesn't block startup
            import threading
            threading.Thread(target=_pool.open, daemon=True).start()
            log.info("✅ Neon connection pool initialized (min=2, max=8, lazy open)")
        except ImportError:
            log.warning("⚠️ psycopg_pool not installed — falling back to per-call connections (slower)")
            _pool = False  # Mark as unavailable, fall through to direct connect
        except Exception as e:
            log.warning("⚠️ Connection pool init failed: %s — using per-call connections", e)
            _pool = False
    return _pool


def _get_conn():
    """Get a PostgreSQL connection. Uses pool if available, else direct connect.

    Pool reuse eliminates the 2-4s Neon cold-start per call. Falls back
    gracefully to direct psycopg.connect() if psycopg_pool is not installed.
    """
    pool = _init_pool()
    if pool and pool is not False:
        class ConnWrapper:
            def __init__(self, p):
                self._p = p
                self._c = p.getconn(timeout=10)

            def __getattr__(self, item):
                return getattr(self._c, item)

            def close(self):
                self._p.putconn(self._c)

            def __enter__(self):
                return self._c.__enter__()

            def __exit__(self, exc_type, exc_val, exc_tb):
                res = self._c.__exit__(exc_type, exc_val, exc_tb)
                self.close()
                return res
        return ConnWrapper(pool)
    # Fallback: direct connection (original behavior)
    import time
    for attempt in range(3):
        try:
            return psycopg.connect(settings.POSTGRES_URL, row_factory=dict_row, connect_timeout=15)
        except Exception as e:
            if attempt == 2:
                log.error("Failed to connect to PostgreSQL after 3 attempts: %s", e)
                raise
            log.warning("PostgreSQL connection failed (attempt %d/3). Retrying in 2s... (%s)", attempt + 1, e)
            time.sleep(2)


def init_pg_tables():
    """Create all PostgreSQL tables if they don't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'viewer',
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                preferred_language TEXT NOT NULL DEFAULT 'en',
                full_name   TEXT,
                avatar_url  TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                persona     TEXT DEFAULT 'general',
                is_pinned   BOOLEAN NOT NULL DEFAULT FALSE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content     TEXT NOT NULL,
                mode        TEXT DEFAULT 'conversation',
                sources     JSONB DEFAULT '[]'::jsonb,
                tokens_used INTEGER DEFAULT 0,
                latency_ms  INTEGER DEFAULT 0,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kpi_metrics (
                id          SERIAL PRIMARY KEY,
                period      TEXT NOT NULL,
                metric      TEXT NOT NULL,
                value       DOUBLE PRECISION NOT NULL,
                category    TEXT NOT NULL,
                segment     TEXT DEFAULT '',
                unit        TEXT DEFAULT '',
                direction   TEXT DEFAULT 'higher_is_better',
                source      TEXT DEFAULT 'manual',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kpi_entities (
                id            SERIAL PRIMARY KEY,
                record_ref    TEXT NOT NULL,
                entity_type   TEXT NOT NULL,
                entity_value  TEXT NOT NULL,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_entities_ref ON kpi_entities(record_ref)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kpi_targets (
                metric          TEXT PRIMARY KEY,
                target          DOUBLE PRECISION,
                good_threshold  DOUBLE PRECISION,
                bad_threshold   DOUBLE PRECISION,
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                doc_id      TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                content     TEXT NOT NULL,
                source      TEXT DEFAULT 'manual',
                embedding   TEXT DEFAULT '',
                language    TEXT DEFAULT 'en',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id          SERIAL PRIMARY KEY,
                event_type  TEXT NOT NULL,
                event_detail TEXT,
                actor       TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        # Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_period ON kpi_metrics(period)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_category ON kpi_metrics(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_metric ON kpi_metrics(metric)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_trail(event_type)")

        # File management (uploaded artifacts and extracted content)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,
                extracted_content TEXT,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_user ON uploaded_files(username)")

        # Ingestion and export operation logs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_ingestion_log (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                filename TEXT,
                file_type TEXT,
                source TEXT,
                status TEXT NOT NULL DEFAULT 'processing',
                row_count INTEGER DEFAULT 0,
                file_size_bytes BIGINT,
                import_destination TEXT,
                mapping_config JSONB,
                preview_data JSONB,
                error_message TEXT,
                ingested_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_export_log (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                export_name TEXT NOT NULL,
                export_format TEXT NOT NULL,
                source_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                query JSONB,
                output_location TEXT,
                row_count INTEGER,
                file_size_bytes BIGINT,
                error_message TEXT,
                expiration_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # Domain preference and history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_preference (
                username TEXT PRIMARY KEY,
                default_domain TEXT NOT NULL DEFAULT 'general',
                last_used_domain TEXT,
                domain_history JSONB DEFAULT '{}'::jsonb,
                last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # Mini spreadsheet store
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_spreadsheet (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                domain TEXT DEFAULT 'general',
                description TEXT,
                is_public BOOLEAN NOT NULL DEFAULT FALSE,
                data TEXT,
                schema_columns TEXT,
                row_count INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(username, name)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_data_spreadsheet_user ON data_spreadsheet(username)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_logs (
                id          SERIAL PRIMARY KEY,
                event_type  TEXT NOT NULL,
                module      TEXT,
                detail      JSONB DEFAULT '{}'::jsonb,
                actor       TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_type ON monitoring_logs(event_type)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS integration_credentials (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                credentials_encrypted TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_integration_user ON integration_credentials(username)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_oauth_state_username ON oauth_states(username)")

        conn.commit()
        log.info("✅ PostgreSQL tables initialized")
    except Exception as e:
        log.error("PostgreSQL init failed: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# KPI OPERATIONS
# ═══════════════════════════════════════════════════════════

def store_kpi_metrics(df: "pd.DataFrame", source_name: str = "manual", replace: bool = True, replace_prefix: Optional[str] = None) -> None:
    if df.empty:
        return
    params = [
        (
            str(row.get("period", "")),
            str(row.get("metric", "")),
            float(row.get("value", 0)),
            str(row.get("category", "")),
            str(row.get("segment", "")),
            str(row.get("unit", "")),
            str(row.get("direction", "higher_is_better")),
            source_name,
        )
        for _, row in df.iterrows()
    ]
    insert_sql = (
        "INSERT INTO kpi_metrics (period, metric, value, category, segment, unit, direction, source) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    )
    last_err: Optional[Exception] = None
    for _ in range(3):
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                if replace:
                    if replace_prefix:
                        cur.execute("DELETE FROM kpi_metrics WHERE source LIKE %s", [f"{replace_prefix}%"])
                    else:
                        cur.execute("DELETE FROM kpi_metrics WHERE source = %s", [source_name])
                cur.executemany(insert_sql, params)
            conn.commit()
            return
        except Exception as e:
            last_err = e
            try:
                conn.rollback()
            except Exception:
                log.exception("Unexpected error")
                pass
        finally:
            conn.close()
    if last_err:
        raise last_err


def get_kpi_metrics(
    periods: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    segments: Optional[List[str]] = None,
    limit: Optional[int] = 2000,
) -> "pd.DataFrame":
    import pandas as pd
    conn = _get_conn()
    try:
        q = "SELECT period, metric, value, category, segment, unit, direction, source FROM kpi_metrics"
        filters: List[str] = []
        params: List[Any] = []
        for col, vals in [("period", periods), ("metric", metrics), ("category", categories), ("segment", segments)]:
            if vals:
                ph = ",".join(["%s"] * len(vals))
                filters.append(f"{col} IN ({ph})")
                params.extend(vals)
        if filters:
            q += " WHERE " + " AND ".join(filters)
        q += " ORDER BY period, metric"
        if limit:
            q += " LIMIT %s"
            params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


def store_kpi_entities(rows: List[Dict[str, str]], replace: bool = True) -> int:
    """Persist GraphRAG-lite entities (the kpi_entities sidecar table).

    ``rows`` = ``[{record_ref, entity_type, entity_value}, ...]`` extracted at ingestion.
    Returns the number of rows written.
    """
    if not rows:
        return 0
    conn = _get_conn()
    try:
        if replace:
            conn.execute("DELETE FROM kpi_entities")
        params = [
            (str(r.get("record_ref", "")), str(r.get("entity_type", "")), str(r.get("entity_value", "")))
            for r in rows
        ]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO kpi_entities (record_ref, entity_type, entity_value) VALUES (%s, %s, %s)",
                params,
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_kpi_entities() -> "pd.DataFrame":
    """Return the persisted GraphRAG-lite entities (record_ref, entity_type, entity_value)."""
    import pandas as pd
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT record_ref, entity_type, entity_value FROM kpi_entities"
        ).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


def get_available_periods() -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT period FROM kpi_metrics ORDER BY period DESC").fetchall()
        return [r["period"] for r in rows]
    finally:
        conn.close()


def get_available_metrics() -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT metric FROM kpi_metrics ORDER BY metric").fetchall()
        return [r["metric"] for r in rows]
    finally:
        conn.close()


def get_available_categories() -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT category FROM kpi_metrics ORDER BY category").fetchall()
        return [r["category"] for r in rows]
    finally:
        conn.close()


def get_available_segments() -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT segment FROM kpi_metrics ORDER BY segment").fetchall()
        return [r["segment"] for r in rows]
    finally:
        conn.close()


def get_latest_period() -> Optional[str]:
    periods = get_available_periods()
    if not periods:
        return None
    # Prefer the latest real monthly period (YYYY-MM) — these carry the full metric
    # set (incl. Finance line items). For YYYY-MM, lexical sort == chronological order.
    # This avoids placeholder/future tags (e.g. "2099Q1") or sparse quarterly aggregates
    # ("2026-Q2") being picked as "latest" and yielding empty statements/dashboards.
    import re
    monthly = sorted(p for p in periods if re.match(r"^\d{4}-\d{2}$", p))
    if monthly:
        return monthly[-1]
    return periods[0]


def delete_period(period: str) -> None:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM kpi_metrics WHERE period = %s", [period])
        conn.commit()
    finally:
        conn.close()


def upsert_kpi_targets(targets_df: "pd.DataFrame") -> None:
    if targets_df.empty:
        return
    conn = _get_conn()
    try:
        for _, row in targets_df.iterrows():
            conn.execute(
                """INSERT INTO kpi_targets (metric, target, good_threshold, bad_threshold)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (metric) DO UPDATE
                   SET target = EXCLUDED.target,
                       good_threshold = EXCLUDED.good_threshold,
                       bad_threshold = EXCLUDED.bad_threshold,
                       updated_at = NOW()""",
                [row["metric"], float(row.get("target", 0)), float(row.get("good_threshold", 0)), float(row.get("bad_threshold", 0))],
            )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# FILE MANAGEMENT OPERATIONS
# ═══════════════════════════════════════════════════════════

def get_user_files(username: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Return uploaded files metadata for a user."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, file_name, file_path, file_type, created_at
            FROM uploaded_files
            WHERE username = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            [username, limit, offset],
        ).fetchall()
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        log.warning("Failed to fetch user files: %s", e)
        return []
    finally:
        conn.close()


def delete_file(file_id: str, username: str) -> bool:
    """Delete a file from the database for the given user."""
    conn = _get_conn()
    try:
        res = conn.execute(
            "DELETE FROM uploaded_files WHERE id = %s AND username = %s",
            [file_id, username]
        )
        return res.rowcount > 0
    except Exception as e:
        log.warning("Failed to delete file: %s", e)
        return False


def get_file_content(file_id: str, username: str) -> Optional[str]:
    """Return extracted content for a file owned by a user."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT extracted_content FROM uploaded_files WHERE id = %s AND username = %s",
            [file_id, username],
        ).fetchone()
        return row["extracted_content"] if row else None
    except Exception as e:
        log.warning("Failed to fetch file content: %s", e)
        return None
    finally:
        conn.close()


def get_file_path(file_id: str, username: str) -> Optional[str]:
    """Return local file path for a file owned by a user."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT file_path FROM uploaded_files WHERE id = %s AND username = %s",
            [file_id, username],
        ).fetchone()
        return row["file_path"] if row and row.get("file_path") else None
    except Exception as e:
        log.warning("Failed to fetch file path: %s", e)
        return None
    finally:
        conn.close()


def get_kpi_targets(metrics: Optional[List[str]] = None) -> "pd.DataFrame":
    import pandas as pd
    conn = _get_conn()
    try:
        q = "SELECT metric, target, good_threshold, bad_threshold FROM kpi_targets"
        params: List[Any] = []
        if metrics:
            q += " WHERE metric IN ({})".format(",".join(["%s"] * len(metrics)))
            params.extend(metrics)
        rows = conn.execute(q, params).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# KNOWLEDGE BASE OPERATIONS
# ═══════════════════════════════════════════════════════════

def store_knowledge_docs(docs_df: "pd.DataFrame", replace_prefix: Optional[str] = None) -> None:
    """Upsert knowledge-base docs. ON CONFLICT updates ALL fields (title/content/source/
    embedding) — not just content — so a reused doc_id can never end up with a stale title
    paired to new content. ``replace_prefix`` first deletes docs whose doc_id starts with it
    (e.g. ``"seed-"``) so a re-seed with a different doc set leaves no orphaned rows."""
    if docs_df.empty:
        return
    params = [
        (
            str(row.get("doc_id", "")),
            str(row.get("title", "")),
            str(row.get("content", "")),
            str(row.get("source", "manual")),
            str(row.get("embedding", "")),
            str(row.get("language", "en")),
        )
        for _, row in docs_df.iterrows()
    ]
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if replace_prefix:
                cur.execute("DELETE FROM knowledge_base WHERE doc_id LIKE %s", [f"{replace_prefix}%"])
            cur.executemany(
                """INSERT INTO knowledge_base (doc_id, title, content, source, embedding, language)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (doc_id) DO UPDATE
                   SET title = EXCLUDED.title, content = EXCLUDED.content,
                       source = EXCLUDED.source, embedding = EXCLUDED.embedding,
                       language = EXCLUDED.language""",
                params,
            )
        conn.commit()
    finally:
        conn.close()


_DOCS_SEED_CACHE = None


def _get_seeded_fallback_docs() -> "pd.DataFrame":
    import pandas as pd
    global _DOCS_SEED_CACHE
    if _DOCS_SEED_CACHE is not None:
        return _DOCS_SEED_CACHE.copy()
    try:
        from src.data.seed import generate_kpi_rows, generate_knowledge_docs
        rows = generate_kpi_rows()
        docs = generate_knowledge_docs(rows)
        try:
            from src.data.glossary import as_knowledge_docs
            docs += as_knowledge_docs()
        except Exception:
            pass
        _DOCS_SEED_CACHE = pd.DataFrame([
            {"doc_id": f"seed-{i}", "title": d["title"], "content": d["content"],
             "source": d["source"], "embedding": "", "language": "en", "created_at": "2026-01-01T00:00:00Z"}
            for i, d in enumerate(docs)
        ])
        return _DOCS_SEED_CACHE.copy()
    except Exception as e:
        log.error("Failed to generate seed fallback docs DataFrame: %s", e)
        return pd.DataFrame()


def get_knowledge_docs() -> "pd.DataFrame":
    import pandas as pd
    try:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT doc_id, title, content, source, embedding, language, created_at "
                "FROM knowledge_base ORDER BY created_at DESC"
            ).fetchall()
            if rows:
                return pd.DataFrame([dict(r) for r in rows])
        finally:
            conn.close()
    except Exception as e:
        log.warning("Postgres query for knowledge_base failed (%s) — falling back to seed docs", e)

    return _get_seeded_fallback_docs()


def get_conversation_history(session_id: str) -> "pd.DataFrame":
    import pandas as pd
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role AS user_message, content AS ai_response, created_at "
            "FROM chat_messages WHERE session_id = %s ORDER BY created_at",
            [session_id],
        ).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


def get_conversations(limit: int = 50) -> "pd.DataFrame":
    import pandas as pd
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT session_id AS cid, role, content, created_at "
            "FROM chat_messages ORDER BY created_at DESC LIMIT %s",
            [limit],
        ).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


def store_conversation(cid: str, user_msg: str, ai_resp: str, language: str = "en") -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, mode) VALUES (%s, %s, %s, %s)",
            [cid, "user", user_msg, "conversation"],
        )
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, mode) VALUES (%s, %s, %s, %s)",
            [cid, "assistant", ai_resp, "conversation"],
        )
        conn.commit()
    except Exception:
        log.exception("Unexpected error")
        pass
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# AUDIT TRAIL
# ═══════════════════════════════════════════════════════════

def log_audit_event(actor: str, event_type: str, detail: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO audit_trail (event_type, event_detail, actor) VALUES (%s, %s, %s)",
            [event_type, detail, actor],
        )
        conn.commit()
    except Exception:
        log.exception("Unexpected error")
        pass
    finally:
        conn.close()


def get_audit_trail(limit: int = 100) -> "pd.DataFrame":
    import pandas as pd
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT event_type, event_detail, actor, created_at FROM audit_trail ORDER BY created_at DESC LIMIT %s",
            [limit],
        ).fetchall()
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    finally:
        conn.close()


# ── Integration credentials (encrypted) ─────────────────────────────────────

    # ── Chat session helpers ───────────────────────────────────────────────────
def store_chat_session(session_id: str, user_id: str, title: str = "New Chat", persona: str = "general", is_pinned: bool = False) -> None:
    """Create or update a chat session record.

    This helper provides the interface expected by higher-level modules.
    If the session already exists it will update the title/persona; otherwise
    it inserts a new chat_sessions row.
    """
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id FROM chat_sessions WHERE id = %s", [session_id]).fetchone()
        if row:
            conn.execute(
                "UPDATE chat_sessions SET title = %s, persona = %s, is_pinned = %s, updated_at = NOW() WHERE id = %s",
                [title, persona, is_pinned, session_id],
            )
        else:
            conn.execute(
                "INSERT INTO chat_sessions (id, user_id, title, persona, is_pinned) VALUES (%s, %s, %s, %s, %s)",
                [session_id, user_id, title, persona, is_pinned],
            )
        conn.commit()
    except Exception:
        # intentionally swallow DB errors to keep higher-level flows resilient
        pass
    finally:
        conn.close()


# ── OAuth state persistence (to avoid in-memory loss on restart)


# ═══════════════════════════════════════════════════════════
# USER OPERATIONS
# ═══════════════════════════════════════════════════════════

def get_user(username: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = %s", [username]).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = %s", [user_id]).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(
    username: str,
    password_hash: str,
    role: str = "viewer",
    preferred_language: str = "en",
    full_name: str = "",
) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    if not full_name:
        full_name = username.replace("_", " ").title()
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO users (id, username, password_hash, role, preferred_language, full_name)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (username) DO NOTHING""",
            [user_id, username, password_hash, role, preferred_language, full_name],
        )
        conn.commit()
        return {"id": user_id, "username": username, "role": role}
    finally:
        conn.close()


def update_user(user_id: str, **kwargs) -> bool:
    conn = _get_conn()
    try:
        sets = []
        vals = []
        for key in ("role", "is_active", "preferred_language", "full_name", "avatar_url"):
            if key in kwargs and kwargs[key] is not None:
                sets.append(f"{key} = %s")
                vals.append(kwargs[key])
        if not sets:
            return False
        sets.append("updated_at = NOW()")
        vals.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = %s", vals)
        conn.commit()
        return True
    finally:
        conn.close()


def list_users() -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, username, role, is_active, preferred_language, full_name, created_at FROM users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def user_exists(username: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT 1 FROM users WHERE username = %s", [username]).fetchone()
        return row is not None
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# CHAT SESSION OPERATIONS
# ═══════════════════════════════════════════════════════════

def create_chat_session(user_id: str, title: str = "New Chat", persona: str = "general") -> str:
    session_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO chat_sessions (id, user_id, title, persona) VALUES (%s, %s, %s, %s)",
            [session_id, user_id, title, persona],
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def get_user_sessions(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT s.id, s.title, s.persona, s.is_pinned, s.created_at, s.updated_at,
                      COUNT(m.id) AS message_count,
                      MAX(m.created_at) AS last_message_at
               FROM chat_sessions s
               LEFT JOIN chat_messages m ON m.session_id = s.id
               WHERE s.user_id = %s
               GROUP BY s.id
               ORDER BY s.is_pinned DESC, s.updated_at DESC
               LIMIT %s""",
            [user_id, limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_session_title(session_id: str, title: str):
    conn = _get_conn()
    try:
        conn.execute("UPDATE chat_sessions SET title = %s, updated_at = NOW() WHERE id = %s", [title, session_id])
        conn.commit()
    finally:
        conn.close()


def toggle_pin_session(session_id: str):
    conn = _get_conn()
    try:
        conn.execute("UPDATE chat_sessions SET is_pinned = NOT is_pinned, updated_at = NOW() WHERE id = %s", [session_id])
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id: str):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM chat_sessions WHERE id = %s", [session_id])
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# CHAT MESSAGE OPERATIONS
# ═══════════════════════════════════════════════════════════

def store_message(
    session_id: str,
    role: str,
    content: str,
    mode: str = "conversation",
    sources: str = "[]",
    tokens_used: int = 0,
    latency_ms: int = 0,
):
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO chat_messages (session_id, role, content, mode, sources, tokens_used, latency_ms)
               VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)""",
            [session_id, role, content, mode, sources, tokens_used, latency_ms],
        )
        conn.execute("UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s", [session_id])
        # Auto-title the session from the FIRST user message (only while it's still the default),
        # so the history list shows real titles instead of every entry reading "New Chat".
        if role == "user" and content and content.strip():
            snippet = " ".join(content.strip().split())
            snippet = (snippet[:60] + "…") if len(snippet) > 60 else snippet
            conn.execute(
                "UPDATE chat_sessions SET title = %s "
                "WHERE id = %s AND (title = 'New Chat' OR title IS NULL OR title = '')",
                [snippet, session_id],
            )
        conn.commit()
    finally:
        conn.close()


def get_session_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT id, role, content, mode, sources, tokens_used, latency_ms, created_at
               FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT %s""",
            [session_id, limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_context(user_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """Get recent messages across sessions for cross-session memory."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT m.role, m.content FROM chat_messages m
               JOIN chat_sessions s ON s.id = m.session_id
               WHERE s.user_id = %s
               ORDER BY m.created_at DESC LIMIT %s""",
            [user_id, limit],
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# MONITORING
# ═══════════════════════════════════════════════════════════


def clear_user_data() -> Dict[str, int]:
    """Delete safe-to-wipe data (chat history + audit trail). Preserves everything the app
    needs to work: KPI metrics, knowledge base, targets, entities, and users."""
    out: Dict[str, int] = {}
    conn = _get_conn()
    try:
        for tbl in ("chat_messages", "chat_sessions", "audit_trail"):
            try:
                cur = conn.execute(f"DELETE FROM {tbl}")
                out[tbl] = getattr(cur, "rowcount", 0) or 0
            except Exception:
                out[tbl] = -1
        conn.commit()
    finally:
        conn.close()
    return out


def ensure_session_exists(session_id: str, user_id: str) -> str:
    """Ensure a chat session exists, create if not. Return session_id."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id FROM chat_sessions WHERE id = %s", [session_id]).fetchone()
        if row:
            return session_id
        # Create it
        conn.execute(
            "INSERT INTO chat_sessions (id, user_id, title, persona) VALUES (%s, %s, %s, %s)",
            [session_id, user_id, "New Chat", "general"],
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


# ── Seed data ─────────────────────────────────────────────────────────────────

def seed_all_domains() -> int:
    """
    Seed multi-domain KPI data (+ knowledge-base docs) if the table is empty.
    Delegates to the robust, deterministic seed in ``src.data.seed``.
    Returns the number of KPI rows inserted.
    """
    from src.data.seed import seed_database  # lazy import avoids circular dependency
    counts = seed_database(replace=True)
    return counts.get("kpi_rows", 0)


# ════════════════════════════════════════════════════════════════════════════
# TOKEN REFRESH & OAUTH MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════

def store_token_refresh_metadata(
    username: str,
    integration_type: str,
    refresh_token: str,
    token_expires_at: str,
    scope: Optional[str] = None,
    encrypt: bool = True,
) -> bool:
    """
    Store refresh token metadata for long-lived OAuth integrations.

    Args:
        username: User account
        integration_type: gmail, sheets, clickup, etc.
        refresh_token: OAuth refresh token (will be encrypted)
        token_expires_at: ISO 8601 timestamp when access token expires
        scope: OAuth scope
        encrypt: Whether to encrypt the refresh token before storing

    Returns:
        True if successful
    """
    conn = _get_conn()
    try:
        from src.core.crypto import encrypt_value

        encrypted_token = refresh_token
        if encrypt:
            encrypted_token = encrypt_value(refresh_token)

        conn.execute(
            """
            INSERT INTO token_refresh_metadata (
                username, integration_type, refresh_token, token_expires_at,
                scope, is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
            ON CONFLICT (username, integration_type) DO UPDATE SET
                refresh_token = EXCLUDED.refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                scope = EXCLUDED.scope,
                is_active = TRUE,
                updated_at = NOW(),
                consecutive_failures = 0
            """,
            [username, integration_type, encrypted_token, token_expires_at, scope],
        )
        conn.commit()
        log.info("Stored refresh token for %s:%s", username, integration_type)
        return True
    except Exception as e:
        log.error("Failed to store refresh token: %s", e)
        return False
    finally:
        conn.close()


def get_token_refresh_metadata(
    username: str,
    integration_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve refresh token metadata for OAuth integration.

    Returns:
        Dict with refresh_token, token_expires_at, scope, etc. or None
    """
    conn = _get_conn()
    try:
        from src.core.crypto import decrypt_value

        row = conn.execute(
            """
            SELECT refresh_token, token_expires_at, scope, last_refresh_success,
                   consecutive_failures, is_active
            FROM token_refresh_metadata
            WHERE username = %s AND integration_type = %s AND is_active = TRUE
            """,
            [username, integration_type],
        ).fetchone()

        if not row:
            return None

        # Decrypt refresh token
        try:
            refresh_token = decrypt_value(row["refresh_token"])
        except Exception as e:
            log.warning("Failed to decrypt refresh token: %s", e)
            refresh_token = row["refresh_token"]  # Return encrypted if decryption fails

        return {
            "refresh_token": refresh_token,
            "token_expires_at": row["token_expires_at"],
            "scope": row["scope"],
            "last_refresh_success": row["last_refresh_success"],
            "consecutive_failures": row["consecutive_failures"],
            "is_active": row["is_active"],
        }
    except Exception as e:
        log.error("Failed to retrieve refresh token: %s", e)
        return None
    finally:
        conn.close()


def update_token_refresh_status(
    username: str,
    integration_type: str,
    success: bool,
    new_expires_at: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """
    Update token refresh attempt status.

    Args:
        username: User account
        integration_type: Integration type
        success: True if refresh succeeded
        new_expires_at: New expiry time if successful
        error_message: Error if failed

    Returns:
        True if successful
    """
    conn = _get_conn()
    try:
        if success:
            conn.execute(
                """
                UPDATE token_refresh_metadata
                SET token_expires_at = %s,
                    last_refresh_attempt = NOW(),
                    last_refresh_success = NOW(),
                    refresh_attempt_count = refresh_attempt_count + 1,
                    consecutive_failures = 0,
                    updated_at = NOW()
                WHERE username = %s AND integration_type = %s
                """,
                [new_expires_at, username, integration_type],
            )
        else:
            conn.execute(
                """
                UPDATE token_refresh_metadata
                SET last_refresh_attempt = NOW(),
                    refresh_attempt_count = refresh_attempt_count + 1,
                    consecutive_failures = consecutive_failures + 1,
                    updated_at = NOW()
                WHERE username = %s AND integration_type = %s
                """,
                [username, integration_type],
            )

            # Record failure event
            if error_message:
                conn.execute(
                    """
                    INSERT INTO oauth_token_events (
                        username, integration_type, event_type, error_message, created_at
                    ) VALUES (%s, %s, 'refresh_failed', %s, NOW())
                    """,
                    [username, integration_type, error_message[:500]],
                )

        conn.commit()
        return True
    except Exception as e:
        log.error("Failed to update refresh status: %s", e)
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
# DATA INGESTION & EXPORT
# ════════════════════════════════════════════════════════════════════════════

def log_data_ingestion(
    username: str,
    filename: str,
    file_type: str,
    source: str,
    status: str = "pending",
    row_count: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
    import_destination: Optional[str] = None,
    mapping_config: Optional[Dict[str, Any]] = None,
    preview_data: Optional[List[Dict[str, Any]]] = None,
    error_message: Optional[str] = None,
) -> int:
    """
    Log data ingestion attempt.

    Returns:
        Ingestion log ID
    """
    import json
    conn = _get_conn()
    try:
        result = conn.execute(
            """
            INSERT INTO data_ingestion_log (
                username, filename, file_type, source, status,
                row_count, file_size_bytes, import_destination,
                mapping_config, preview_data, error_message,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            [
                username,
                filename,
                file_type,
                source,
                status,
                row_count,
                file_size_bytes,
                import_destination,
                json.dumps(mapping_config) if mapping_config else None,
                json.dumps(preview_data) if preview_data else None,
                error_message[:500] if error_message else None,
            ],
        )
        log_id = result.fetchone()["id"]
        conn.commit()
        return log_id
    except Exception as e:
        log.error("Failed to log ingestion: %s", e)
        return -1
    finally:
        conn.close()


def update_ingestion_log(
    ingestion_id: int,
    status: str,
    row_count: Optional[int] = None,
    error_message: Optional[str] = None,
    ingested_at: Optional[str] = None,
) -> bool:
    """Update data ingestion log status."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            UPDATE data_ingestion_log
            SET status = %s, row_count = COALESCE(%s, row_count),
                error_message = %s, ingested_at = %s, updated_at = NOW()
            WHERE id = %s
            """,
            [status, row_count, error_message[:500] if error_message else None, ingested_at, ingestion_id],
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("Failed to update ingestion log: %s", e)
        return False
    finally:
        conn.close()


def log_data_export(
    username: str,
    export_name: str,
    export_format: str,
    source_type: str,
    status: str = "pending",
    query: Optional[Dict[str, Any]] = None,
    output_location: Optional[str] = None,
    row_count: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None,
    expiration_at: Optional[str] = None,
) -> int:
    """
    Log data export request.

    Returns:
        Export log ID
    """
    import json
    conn = _get_conn()
    try:
        result = conn.execute(
            """
            INSERT INTO data_export_log (
                username, export_name, export_format, source_type, status,
                query, output_location, row_count, file_size_bytes,
                error_message, expiration_at, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
            """,
            [
                username,
                export_name,
                export_format,
                source_type,
                status,
                json.dumps(query) if query else None,
                output_location,
                row_count,
                file_size_bytes,
                error_message[:500] if error_message else None,
                expiration_at,
            ],
        )
        export_id = result.fetchone()["id"]
        conn.commit()
        return export_id
    except Exception as e:
        log.error("Failed to log export: %s", e)
        return -1
    finally:
        conn.close()


def update_export_log(
    export_id: int,
    status: str,
    output_location: Optional[str] = None,
    row_count: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None,
) -> bool:
    """Update data export log status."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            UPDATE data_export_log
            SET status = %s, output_location = COALESCE(%s, output_location),
                row_count = COALESCE(%s, row_count),
                file_size_bytes = COALESCE(%s, file_size_bytes),
                error_message = %s, updated_at = NOW()
            WHERE id = %s
            """,
            [
                status,
                output_location,
                row_count,
                file_size_bytes,
                error_message[:500] if error_message else None,
                export_id,
            ],
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("Failed to update export log: %s", e)
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
# DOMAIN PREFERENCE & PERSONALIZATION
# ════════════════════════════════════════════════════════════════════════════

def set_user_default_domain(username: str, domain: str) -> bool:
    """Set user's default domain preference."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO domain_preference (username, default_domain, last_updated)
            VALUES (%s, %s, NOW())
            ON CONFLICT (username) DO UPDATE SET
                default_domain = %s,
                last_updated = NOW()
            """,
            [username, domain, domain],
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("Failed to set domain preference: %s", e)
        return False
    finally:
        conn.close()


def get_user_default_domain(username: str) -> str:
    """Get user's default domain (defaults to 'general')."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT default_domain FROM domain_preference WHERE username = %s",
            [username],
        ).fetchone()
        return row["default_domain"] if row else "general"
    except Exception as e:
        log.warning("Failed to get domain preference: %s", e)
        return "general"
    finally:
        conn.close()


def update_domain_history(username: str, domain: str) -> bool:
    """Update domain usage history for the user."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            UPDATE domain_preference
            SET last_used_domain = %s,
                domain_history = jsonb_set(
                    COALESCE(domain_history, '{}'),
                    ARRAY[%s],
                    to_jsonb(NOW()::text)
                ),
                last_updated = NOW()
            WHERE username = %s
            """,
            [domain, domain, username],
        )
        conn.commit()
        return True
    except Exception as e:
        log.warning("Failed to update domain history: %s", e)
        return False
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
# MINI-SPREADSHEET (Excel-like Data Management)
# ════════════════════════════════════════════════════════════════════════════

def create_spreadsheet(
    username: str,
    name: str,
    domain: str = "general",
    schema_columns: Optional[List[Dict[str, Any]]] = None,
    description: Optional[str] = None,
    is_public: bool = False,
) -> bool:
    """Create a new mini-spreadsheet for data management."""
    import json
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO data_spreadsheet (
                username, name, domain, description, is_public,
                data, schema_columns, row_count, created_by, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, NOW(), NOW())
            """,
            [
                username,
                name,
                domain,
                description,
                is_public,
                json.dumps([]),  # empty data
                json.dumps(schema_columns or []),
                username,
            ],
        )
        conn.commit()
        log.info("Created spreadsheet %s for %s", name, username)
        return True
    except Exception as e:
        log.error("Failed to create spreadsheet: %s", e)
        return False
    finally:
        conn.close()


def append_spreadsheet_rows(
    username: str,
    spreadsheet_name: str,
    rows: List[Dict[str, Any]],
) -> bool:
    """Append rows to existing spreadsheet."""
    import json
    conn = _get_conn()
    try:
        # Get current data
        current = conn.execute(
            "SELECT data FROM data_spreadsheet WHERE username = %s AND name = %s",
            [username, spreadsheet_name],
        ).fetchone()

        if not current:
            return False

        data = json.loads(current["data"]) if current["data"] else []
        data.extend(rows)

        # Update
        conn.execute(
            """
            UPDATE data_spreadsheet
            SET data = %s, row_count = %s, updated_at = NOW()
            WHERE username = %s AND name = %s
            """,
            [json.dumps(data), len(data), username, spreadsheet_name],
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("Failed to append spreadsheet rows: %s", e)
        return False
    finally:
        conn.close()


def export_spreadsheet(
    username: str,
    spreadsheet_name: str,
    format: str = "csv",  # csv, xlsx, json
) -> Optional[str]:
    """Export spreadsheet data to file."""
    import json
    import csv
    from io import StringIO

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, schema_columns FROM data_spreadsheet WHERE username = %s AND name = %s",
            [username, spreadsheet_name],
        ).fetchone()

        if not row:
            return None

        data = json.loads(row["data"]) if row["data"] else []

        if format == "json":
            return json.dumps(data, indent=2)

        elif format == "csv":
            output = StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()

        else:
            log.warning("Unsupported export format: %s", format)
            return None

    except Exception as e:
        log.error("Failed to export spreadsheet: %s", e)
        return None
    finally:
        conn.close()


def store_integration_credentials(username: str, integration_type: str, credentials_encrypted: str) -> None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id FROM integration_credentials WHERE username = %s AND integration_type = %s", [username, integration_type]).fetchone()
        if row:
            conn.execute("UPDATE integration_credentials SET credentials_encrypted = %s, updated_at = NOW() WHERE id = %s", [credentials_encrypted, row["id"]])
        else:
            conn.execute("INSERT INTO integration_credentials (username, integration_type, credentials_encrypted) VALUES (%s, %s, %s)", [username, integration_type, credentials_encrypted])
        conn.commit()
    finally:
        conn.close()


def remove_integration_credentials(username: str, integration_type: str) -> None:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM integration_credentials WHERE username = %s AND integration_type = %s", [username, integration_type])
        conn.commit()
    finally:
        conn.close()


def get_integration_credentials(username: str, integration_type: str):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id, credentials_encrypted, created_at, updated_at FROM integration_credentials WHERE username = %s AND integration_type = %s", [username, integration_type]).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def store_integration_token_refresh(username: str, integration_type: str, refresh_token: str, expires_in: int = 3600) -> None:
    from datetime import timedelta
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT id FROM integration_credentials WHERE username = %s AND integration_type = %s", [username, integration_type]).fetchone()
        if row:
            from agentkit_mcp.core.crypto import encrypt_value
            import json as _json
            metadata = {"refresh_token": refresh_token, "expires_at": expires_at}
            enc = encrypt_value(_json.dumps(metadata))
            conn.execute("UPDATE integration_credentials SET credentials_encrypted = %s, updated_at = NOW() WHERE id = %s", [enc, row["id"]])
            conn.commit()
    finally:
        conn.close()


def get_integration_refresh_token(username: str, integration_type: str):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT credentials_encrypted FROM integration_credentials WHERE username = %s AND integration_type = %s", [username, integration_type]).fetchone()
        if not row:
            return None
        from agentkit_mcp.core.crypto import decrypt_value
        import json as _json
        try:
            decrypted = decrypt_value(row["credentials_encrypted"])
            metadata = _json.loads(decrypted)
            if "refresh_token" in metadata:
                return metadata
        except Exception:
            pass
        return None
    finally:
        conn.close()


def log_monitoring_event(event_type: str, module: str, detail: str, actor: str) -> None:
    conn = _get_conn()
    try:
        conn.execute("INSERT INTO monitoring_logs (event_type, module, detail, actor) VALUES (%s, %s, %s::jsonb, %s)", [event_type, module, detail, actor])
        conn.commit()
    finally:
        conn.close()


def get_monitoring_stats():
    conn = _get_conn()
    try:
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        total_sessions = conn.execute("SELECT COUNT(*) AS c FROM chat_sessions").fetchone()["c"]
        return {"users": total_users, "sessions": total_sessions}
    finally:
        conn.close()
