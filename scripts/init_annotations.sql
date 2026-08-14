-- Schema for the bundled `annotations` tool pack (packs/annotations.yaml).
--
-- Lets an agent write findings back to the system of record instead of only reading:
-- an anomaly it explained stays explained for the next reader. Retraction is a soft
-- delete so the trail survives — combined with the audit log, every annotation can be
-- traced to the invocation that created it.
--
-- Apply:  psql "$POSTGRES_URL" -f scripts/init_annotations.sql

CREATE TABLE IF NOT EXISTS kpi_annotations (
    id           SERIAL PRIMARY KEY,
    metric       TEXT        NOT NULL,
    period       TEXT        NOT NULL,          -- e.g. '2026-07'
    note         TEXT        NOT NULL,
    severity     TEXT        NOT NULL DEFAULT 'info',   -- info | warning | critical
    author       TEXT        NOT NULL DEFAULT 'agentkit',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retracted_at TIMESTAMPTZ                     -- NULL = active
);

-- Reads filter by metric and hide retracted rows; this covers both.
CREATE INDEX IF NOT EXISTS idx_kpi_annotations_metric
    ON kpi_annotations (metric, retracted_at);

CREATE INDEX IF NOT EXISTS idx_kpi_annotations_created
    ON kpi_annotations (created_at DESC);
