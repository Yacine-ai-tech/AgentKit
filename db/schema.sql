-- OmniIntelOS — PostgreSQL Schema
-- Migration from DuckDB + SQLite → unified PostgreSQL

-- ════════════════════════════════════════════════════════════
-- EXTENSIONS
-- ════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ════════════════════════════════════════════════════════════
-- ENUMS
-- ════════════════════════════════════════════════════════════
CREATE TYPE user_role AS ENUM (
    'admin', 'ceo', 'cfo', 'cto', 'coo', 'chro',
    'hr', 'esg', 'risk', 'analyst', 'viewer',
    'board', 'logistics', 'it', 'operations', 'custom'
);

CREATE TYPE data_category AS ENUM (
    'Finance'
    
    , 'Growth', 'Operations', 'People', 'ESG',
    'Customer', 'Macro', 'Other'
);

CREATE TYPE document_status AS ENUM (
    'quarantine', 'processing', 'validated', 'rejected', 'active', 'archived'
);

CREATE TYPE statement_type AS ENUM (
    'income_statement', 'balance_sheet', 'cash_flow', 'trial_balance'
);

CREATE TYPE account_type AS ENUM (
    'asset', 'liability', 'equity', 'revenue', 'expense'
);

CREATE TYPE journal_status AS ENUM (
    'draft', 'posted', 'reversed'
);

-- ════════════════════════════════════════════════════════════
-- USERS & AUTH
-- ════════════════════════════════════════════════════════════
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(100) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role            user_role NOT NULL DEFAULT 'viewer',
    preferred_language VARCHAR(5) DEFAULT 'en',
    is_active       BOOLEAN DEFAULT TRUE,
    company_id      UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- ════════════════════════════════════════════════════════════
-- COMPANIES & ORGANIZATIONAL STRUCTURE
-- ════════════════════════════════════════════════════════════
CREATE TABLE companies (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    sector      VARCHAR(100),
    country     VARCHAR(100),
    fiscal_year_end VARCHAR(5) DEFAULT '12-31',
    currency    VARCHAR(3) DEFAULT 'USD',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE periods (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID REFERENCES companies(id) ON DELETE CASCADE,
    label       VARCHAR(20) NOT NULL,  -- e.g. '2025-Q1', '2025-01'
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    is_closed   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_periods_company ON periods(company_id);
CREATE INDEX idx_periods_label ON periods(label);

-- ════════════════════════════════════════════════════════════
-- CHART OF ACCOUNTS & FINANCIAL LEDGER
-- ════════════════════════════════════════════════════════════
CREATE TABLE accounts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID REFERENCES companies(id) ON DELETE CASCADE,
    code        VARCHAR(20) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    account_type account_type NOT NULL,
    parent_id   UUID REFERENCES accounts(id),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, code)
);

CREATE INDEX idx_accounts_company ON accounts(company_id);
CREATE INDEX idx_accounts_type ON accounts(account_type);

CREATE TABLE journal_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    period_id       UUID REFERENCES periods(id),
    entry_date      DATE NOT NULL,
    description     TEXT,
    reference       VARCHAR(100),
    source_document UUID,
    status          journal_status DEFAULT 'draft',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_journal_company ON journal_entries(company_id);
CREATE INDEX idx_journal_period ON journal_entries(period_id);
CREATE INDEX idx_journal_date ON journal_entries(entry_date);

CREATE TABLE journal_lines (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    journal_entry_id UUID REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id      UUID REFERENCES accounts(id),
    debit           NUMERIC(18,2) DEFAULT 0,
    credit          NUMERIC(18,2) DEFAULT 0,
    memo            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_journal_lines_entry ON journal_lines(journal_entry_id);
CREATE INDEX idx_journal_lines_account ON journal_lines(account_id);

-- ════════════════════════════════════════════════════════════
-- TRIAL BALANCE & FINANCIAL STATEMENTS
-- ════════════════════════════════════════════════════════════
CREATE TABLE trial_balance (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID REFERENCES companies(id) ON DELETE CASCADE,
    period_id   UUID REFERENCES periods(id),
    account_id  UUID REFERENCES accounts(id),
    debit_total NUMERIC(18,2) DEFAULT 0,
    credit_total NUMERIC(18,2) DEFAULT 0,
    balance     NUMERIC(18,2) DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tb_company_period ON trial_balance(company_id, period_id);

CREATE TABLE financial_statements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    period_id       UUID REFERENCES periods(id),
    statement_type  statement_type NOT NULL,
    data            JSONB NOT NULL,
    generated_by    UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_statements_company ON financial_statements(company_id);

-- ════════════════════════════════════════════════════════════
-- KPI METRICS (migrated from DuckDB)
-- ════════════════════════════════════════════════════════════
CREATE TABLE kpi_metrics (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID REFERENCES companies(id),
    period      VARCHAR(20) NOT NULL,
    metric      VARCHAR(255) NOT NULL,
    value       DOUBLE PRECISION,
    category    data_category DEFAULT 'Other',
    segment     VARCHAR(100) DEFAULT 'Global',
    unit        VARCHAR(50) DEFAULT '',
    direction   VARCHAR(50) DEFAULT 'higher_is_better',
    source      VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kpi_period ON kpi_metrics(period);
CREATE INDEX idx_kpi_metric ON kpi_metrics(metric);
CREATE INDEX idx_kpi_category ON kpi_metrics(category);
CREATE INDEX idx_kpi_company ON kpi_metrics(company_id);

CREATE TABLE kpi_targets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id),
    metric          VARCHAR(255) NOT NULL,
    target          DOUBLE PRECISION,
    good_threshold  DOUBLE PRECISION,
    bad_threshold   DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════
-- KNOWLEDGE BASE & CONVERSATIONS
-- ════════════════════════════════════════════════════════════
CREATE TABLE knowledge_base (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       VARCHAR(500),
    content     TEXT,
    source      VARCHAR(255),
    language    VARCHAR(5) DEFAULT 'en',
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kb_source ON knowledge_base(source);

CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    session_id      VARCHAR(100),
    user_message    TEXT,
    ai_response     TEXT,
    persona_used    VARCHAR(50),
    context_used    TEXT,
    language        VARCHAR(5) DEFAULT 'en',
    tokens_used     INTEGER DEFAULT 0,
    latency_ms      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_convos_user ON conversations(user_id);
CREATE INDEX idx_convos_session ON conversations(session_id);

-- ════════════════════════════════════════════════════════════
-- DOCUMENT MANAGEMENT & INGESTION
-- ════════════════════════════════════════════════════════════
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename        VARCHAR(500) NOT NULL,
    original_name   VARCHAR(500),
    doc_type        VARCHAR(50),
    mime_type       VARCHAR(100),
    file_size       BIGINT,
    status          document_status DEFAULT 'quarantine',
    extracted_data  JSONB,
    pii_detected    BOOLEAN DEFAULT FALSE,
    pii_details     JSONB,
    uploaded_by     UUID REFERENCES users(id),
    company_id      UUID REFERENCES companies(id),
    storage_path    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);

CREATE INDEX idx_docs_status ON documents(status);
CREATE INDEX idx_docs_company ON documents(company_id);

-- ════════════════════════════════════════════════════════════
-- AUDIT LOG (unified)
-- ════════════════════════════════════════════════════════════
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    action      VARCHAR(100) NOT NULL,
    resource    VARCHAR(100),
    details     JSONB,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ════════════════════════════════════════════════════════════
-- AGENT PERSONA TEMPLATES
-- ════════════════════════════════════════════════════════════
CREATE TABLE agent_personas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(255),
    system_prompt   TEXT NOT NULL,
    allowed_tools   JSONB DEFAULT '[]',
    data_access     JSONB DEFAULT '[]',
    temperature     DOUBLE PRECISION DEFAULT 0.3,
    max_tokens      INTEGER DEFAULT 2048,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════
-- SEED DATA — DEFAULT PERSONAS
-- ════════════════════════════════════════════════════════════
INSERT INTO agent_personas (name, display_name, system_prompt, allowed_tools, data_access, temperature) VALUES
('ceo', 'CEO Strategist', 'You are the CEO Intelligence Agent for OmniIntelOS. You provide strategic insights, market analysis, M&A guidance, and board-level reporting. Focus on high-level KPIs, growth trajectory, competitive positioning, and organizational health. Always think in terms of long-term value creation.', '["kpi_query","forecast","report_generate","market_analysis"]', '["Finance","Growth","Operations","People","ESG"]', 0.4),
('cfo', 'CFO Analyst', 'You are the CFO Intelligence Agent for OmniIntelOS. You provide financial analysis, budget variance reports, cash flow forecasting, and financial statement generation. You are precise with numbers, flag risks proactively, and always reference the data behind your conclusions.', '["kpi_query","forecast","financial_statements","budget_analysis","cash_flow"]', '["Finance","Growth"]', 0.2),
('cto', 'CTO Advisor', 'You are the CTO Intelligence Agent for OmniIntelOS. You advise on technology strategy, infrastructure costs, security posture, and engineering metrics. You analyze burn rate vs. engineering output, evaluate build-vs-buy decisions, and monitor technical debt.', '["kpi_query","risk_analysis","technology_metrics"]', '["Operations","Finance"]', 0.3),
('coo', 'COO Operations', 'You are the COO Intelligence Agent for OmniIntelOS. You focus on operational efficiency, supply chain metrics, process optimization, and cross-functional coordination. You track cycle times, throughput, and resource utilization.', '["kpi_query","operations_metrics","supply_chain"]', '["Operations","Growth","People"]', 0.3),
('chro', 'CHRO People', 'You are the CHRO Intelligence Agent for OmniIntelOS. You focus on talent management, workforce analytics, engagement scores, diversity metrics, and organizational development. You balance people metrics with business outcomes.', '["kpi_query","people_metrics","engagement_analysis"]', '["People","ESG"]', 0.4),
('esg', 'ESG & Sustainability', 'You are the ESG Intelligence Agent for OmniIntelOS. You track environmental, social, and governance metrics. You analyze carbon footprint, diversity indices, safety records, and sustainability targets. You help prepare ESG reports for stakeholders.', '["kpi_query","esg_metrics","sustainability_report"]', '["ESG","Operations","People"]', 0.3),
('risk', 'Risk & Compliance', 'You are the Risk & Compliance Intelligence Agent for OmniIntelOS. You monitor operational risks, compliance requirements, anomaly detection, and audit readiness. You proactively flag issues and recommend mitigation strategies.', '["kpi_query","risk_analysis","anomaly_detection","audit_report"]', '["Finance","Operations","ESG"]', 0.2),
('analyst', 'Business Analyst', 'You are the Business Analyst Agent for OmniIntelOS. You perform data analysis, create visualizations, run forecasts, and generate insights. You are thorough, data-driven, and communicate findings clearly with supporting evidence.', '["kpi_query","forecast","data_analysis","report_generate"]', '["Finance","Growth","Operations","Customer"]', 0.3),
('board', 'Board Advisor', 'You are the Board Advisory Agent for OmniIntelOS. You prepare board-level summaries, strategic recommendations, and governance insights. You communicate concisely, focus on material issues, and always provide actionable recommendations.', '["kpi_query","executive_summary","governance_report"]', '["Finance","Growth","Operations","People","ESG"]', 0.3),
('operations', 'Operations Manager', 'You are the Operations Manager Agent for OmniIntelOS. You monitor day-to-day operations, track KPIs, identify bottlenecks, and suggest process improvements. You are practical and action-oriented.', '["kpi_query","operations_metrics","process_analysis"]', '["Operations","People"]', 0.3);

-- ════════════════════════════════════════════════════════════
-- SEED DATA — DEFAULT USERS
-- ════════════════════════════════════════════════════════════
-- Passwords are bcrypt hashed versions of simple defaults
-- admin/admin123, ceo/ceo123, cfo/cfo123, etc.
-- In production, these MUST be changed immediately

-- Note: Actual password hashing happens in the application layer.
-- These are placeholder rows; the app's init_db will handle real hashing.

-- ════════════════════════════════════════════════════════════
-- SEED DATA — DEFAULT COMPANY
-- ════════════════════════════════════════════════════════════
INSERT INTO companies (name, sector, country, currency) VALUES
('Default Organization', 'Technology', 'Global', 'USD');
