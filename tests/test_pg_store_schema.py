"""Schema/seed consistency tests for the PostgreSQL store (F-02, F-03).

F-02: init_pg_tables() must create every table pg_store.py references.
F-03: seed.seed_database must populate Postgres via store_kpi_metrics and the
      seeded rows must be queryable again.

The DB-backed tests skip when POSTGRES_URL is unset or unreachable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

PG_STORE_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "agentkit_mcp"
    / "services"
    / "pg_store.py"
)

# Tables legitimately referenced in SQL text but not real tables.
_NON_TABLES = {"{tbl}", "excluded"}


def _referenced_tables() -> set:
    """Extract table names from SQL in pg_store.py (FROM/INTO/UPDATE/JOIN)."""
    src = PG_STORE_PATH.read_text()
    # FROM/INTO/UPDATE/JOIN cover DML; TABLE covers CREATE/ALTER TABLE targets
    # (e.g. kpi_annotations, which only appears in DDL). The (?!\.) lookahead
    # skips schema-qualified names like information_schema.columns.
    names = set(
        re.findall(
            r"(?:FROM|INTO|UPDATE|JOIN|TABLE)\s+"
            r"(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_]\w*)\b(?!\.)",
            src,
        )
    )
    # `UPDATE users SET ...` style is covered; drop anything that is not a
    # plausible snake_case table name.
    return {n for n in names if n.islower() and n not in _NON_TABLES}


@pytest.mark.unit
def test_seed_module_surface():
    """seed.py must expose the functions pg_store expects (no DB needed)."""
    from agentkit_mcp.data import seed

    assert callable(seed.seed_database)
    assert callable(seed.generate_kpi_rows)
    assert callable(seed.generate_knowledge_docs)
    # Regression: the old module imported a non-existent insert_kpi_metric.
    src = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "agentkit_mcp"
        / "data"
        / "seed.py"
    ).read_text()
    assert "insert_kpi_metric" not in src


@pytest.mark.unit
def test_referenced_tables_extracted():
    """Sanity-check the table extractor catches the known pg_store tables."""
    tables = _referenced_tables()
    for expected in (
        "users",
        "chat_sessions",
        "chat_messages",
        "uploaded_files",
        "kpi_metrics",
        "kpi_entities",
        "kpi_targets",
        "kpi_annotations",
        "knowledge_base",
        "audit_trail",
        "monitoring_logs",
        "token_refresh_metadata",
        "oauth_token_events",
        "data_ingestion_log",
        "data_export_log",
        "domain_preference",
        "data_spreadsheet",
        "integration_credentials",
    ):
        assert expected in tables, f"{expected} not found in pg_store SQL"


# ── DB-backed tests ──────────────────────────────────────────────────────────


def _db_available() -> bool:
    try:
        # Importing config runs load_dotenv(), which populates os.environ from .env.
        from agentkit_mcp.core.config import settings  # noqa: F401
        from agentkit_mcp.services import pg_store

        if not (os.getenv("POSTGRES_URL") or getattr(settings, "POSTGRES_URL", "")):
            return False
        conn = pg_store._get_conn()
        conn.close()
        return True
    except Exception:
        return False


pytestmark_db = pytest.mark.skipif(
    not _db_available(), reason="POSTGRES_URL not set or database unreachable"
)


@pytestmark_db
@pytest.mark.unit
def test_init_pg_tables_creates_every_referenced_table():
    """F-02: after init_pg_tables(), every table referenced in pg_store exists."""
    from agentkit_mcp.services import pg_store

    pg_store.init_pg_tables()

    conn = pg_store._get_conn()
    try:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).fetchall()
    finally:
        conn.close()

    existing = {r["table_name"] for r in rows}
    missing = _referenced_tables() - existing
    assert not missing, f"pg_store references tables that were not created: {missing}"


@pytestmark_db
@pytest.mark.unit
def test_seed_then_query_roundtrip():
    """F-03: seed_database populates Postgres and the rows are queryable."""
    from agentkit_mcp.data import seed
    from agentkit_mcp.services import pg_store

    pg_store.init_pg_tables()

    # Seed a small deterministic slice rather than the full 24-month dataset.
    records = seed.generate_time_series_data("healthy")[:300]
    counts = seed.seed_database(data=records, replace=True)

    assert counts["kpi_rows"] == len(records)
    assert counts["docs"] > 0

    df = pg_store.get_kpi_metrics(limit=10)
    assert not df.empty
    assert {"period", "metric", "value", "category"} <= set(df.columns)

    periods = pg_store.get_available_periods()
    assert periods

    docs = pg_store.get_knowledge_docs()
    assert not docs.empty
