-- Pipeline schema. Safe to re-run: every statement is IF NOT EXISTS / OR REPLACE.
-- Apply with: psql "$DATABASE_URL" -f pipeline/sql/schema.sql

-- ---------------------------------------------------------------------------
-- Audit log: one row per pipeline run. Lets us answer "did last night's run
-- work, how much did it load, and what broke?" with a single query.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id            BIGSERIAL PRIMARY KEY,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'running'
                      CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    symbols_attempted INT,
    symbols_failed    INT,
    rows_loaded       INT,
    error             TEXT
);

-- ---------------------------------------------------------------------------
-- Dimension: the universe of stocks we track. The pipeline reads active
-- symbols from here, so adding a ticker is a data change, not a code change.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS symbols (
    symbol     TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    sector     TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Fact: one row per symbol per trading day. The natural key (symbol,
-- trade_date) makes loads idempotent: re-running a day updates, never duplicates.
-- CHECK constraints are the last line of defence behind Python validation.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol      TEXT NOT NULL REFERENCES symbols (symbol),
    trade_date  DATE NOT NULL,
    open        NUMERIC(12, 4) NOT NULL CHECK (open > 0),
    high        NUMERIC(12, 4) NOT NULL CHECK (high > 0),
    low         NUMERIC(12, 4) NOT NULL CHECK (low > 0),
    close       NUMERIC(12, 4) NOT NULL CHECK (close > 0),
    volume      BIGINT NOT NULL CHECK (volume >= 0),
    run_id      BIGINT REFERENCES pipeline_runs (run_id),
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, trade_date),
    CHECK (low <= LEAST(open, close) AND high >= GREATEST(open, close))
);

-- ---------------------------------------------------------------------------
-- Fact: quarterly earnings. reported_date (when the market learned the number)
-- is kept separately from fiscal_date_ending (the period it describes) so
-- features can be built point-in-time, without look-ahead bias.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quarterly_earnings (
    symbol              TEXT NOT NULL REFERENCES symbols (symbol),
    fiscal_date_ending  DATE NOT NULL,
    reported_date       DATE,
    report_time         TEXT,
    reported_eps        NUMERIC(12, 4),
    estimated_eps       NUMERIC(12, 4),
    surprise            NUMERIC(12, 4),
    surprise_pct        NUMERIC(12, 4),
    run_id              BIGINT REFERENCES pipeline_runs (run_id),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, fiscal_date_ending)
);

CREATE INDEX IF NOT EXISTS idx_quarterly_earnings_reported
    ON quarterly_earnings (symbol, reported_date);

-- ---------------------------------------------------------------------------
-- Model-ready features, one row per symbol per trading day.
-- * Rolling windows count trading days (ROWS), not calendar days.
-- * A window is NULL until it has full history, never averaged over fewer rows.
-- * next_day_return is the prediction target (label); it uses the future by
--   design and must never be used as an input feature.
-- * Earnings are joined as of the latest report strictly before trade_date.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW price_features AS
WITH returns AS (
    SELECT
        symbol,
        trade_date,
        close,
        volume,
        close / LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date) - 1 AS return_1d
    FROM daily_prices
),
rolling AS (
    SELECT
        r.*,
        CASE WHEN COUNT(*) OVER w5 = 5 THEN AVG(close) OVER w5 END                      AS sma_5,
        CASE WHEN COUNT(*) OVER w20 = 20 THEN AVG(close) OVER w20 END                   AS sma_20,
        CASE WHEN COUNT(return_1d) OVER w20 = 20 THEN STDDEV_SAMP(return_1d) OVER w20 END AS volatility_20d,
        CASE WHEN COUNT(*) OVER w20 = 20 THEN volume / AVG(volume) OVER w20 END         AS volume_ratio_20d,
        LEAD(close) OVER (PARTITION BY symbol ORDER BY trade_date) / close - 1          AS next_day_return
    FROM returns r
    WINDOW
        w5  AS (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW),
        w20 AS (PARTITION BY symbol ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
)
SELECT
    rolling.*,
    e.reported_eps  AS last_reported_eps,
    e.surprise_pct  AS last_eps_surprise_pct,
    rolling.trade_date - e.reported_date AS days_since_earnings
FROM rolling
LEFT JOIN LATERAL (
    SELECT q.reported_eps, q.surprise_pct, q.reported_date
    FROM quarterly_earnings q
    WHERE q.symbol = rolling.symbol
      AND q.reported_date < rolling.trade_date
    ORDER BY q.reported_date DESC
    LIMIT 1
) e ON TRUE;

-- ---------------------------------------------------------------------------
-- Newest bar per stock, with the change from the previous trading day.
-- Used by the screener; one definition shared by every consumer.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (symbol)
    symbol,
    trade_date,
    open,
    high,
    low,
    close,
    volume,
    close / prev_close - 1 AS change_pct
FROM (
    SELECT d.*, LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_close
    FROM daily_prices d
) with_prev
ORDER BY symbol, trade_date DESC;

-- ---------------------------------------------------------------------------
-- Screener app tables (pre-existing). Kept here so a fresh database
-- (e.g. a new Supabase project) gets everything from one file.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol          TEXT PRIMARY KEY,
    name            TEXT,
    sector          TEXT,
    market_cap      BIGINT,
    pe_ratio        FLOAT,
    dividend_yield  FLOAT,
    eps             FLOAT,
    pb_ratio        FLOAT,
    debt_to_equity  FLOAT
);

CREATE TABLE IF NOT EXISTS saved_screens (
    id          SERIAL PRIMARY KEY,
    label       TEXT NOT NULL,
    filters     JSONB NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
