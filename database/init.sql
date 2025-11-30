-- Mean Reversion Trading Framework - Database Schema
-- PostgreSQL 15
-- Created: 2024

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- TABLES
-- =============================================================================

-- Stock price data (raw OHLCV data)
CREATE TABLE IF NOT EXISTS stock_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

-- Generated candles (all types)
CREATE TABLE IF NOT EXISTS candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    candle_type VARCHAR(20) NOT NULL, -- 'regular', 'heiken_ashi', 'linear_regression'
    aggregation_days INT NOT NULL,    -- 1, 2, 3, 4, 5
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, candle_type, aggregation_days)
);

-- Strategy configurations
CREATE TABLE IF NOT EXISTS strategy_configs (
    id SERIAL PRIMARY KEY,
    config_name VARCHAR(100) UNIQUE NOT NULL,
    phase INT NOT NULL,
    candle_type VARCHAR(20),
    aggregation_days INT,
    mean_type VARCHAR(20),         -- 'SMA', 'EMA', 'LinReg', 'VWAP'
    mean_lookback INT,
    stddev_lookback INT,
    entry_threshold DECIMAL(5,2),
    exit_type VARCHAR(20),
    use_volume_filter BOOLEAN DEFAULT FALSE,
    use_rsi_filter BOOLEAN DEFAULT FALSE,
    use_trend_filter BOOLEAN DEFAULT FALSE,
    use_volatility_filter BOOLEAN DEFAULT FALSE,
    position_sizing VARCHAR(20),
    stop_loss_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters JSONB              -- Store all params as JSON for flexibility
);

-- Backtest results
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id) ON DELETE CASCADE,
    symbol VARCHAR(10),           -- Individual stock or 'PORTFOLIO' for aggregated
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Performance metrics
    total_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),
    profit_factor DECIMAL(10,4),

    -- Trade statistics
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DECIMAL(5,2),
    avg_win DECIMAL(10,4),
    avg_loss DECIMAL(10,4),
    avg_trade DECIMAL(10,4),

    -- Time-based metrics
    avg_holding_period DECIMAL(10,2),
    max_consecutive_wins INT,
    max_consecutive_losses INT,

    -- Risk metrics
    value_at_risk DECIMAL(10,4),
    conditional_var DECIMAL(10,4),

    -- Additional data (stored as JSON for flexibility)
    equity_curve JSONB,
    trade_log JSONB,
    monthly_returns JSONB,

    UNIQUE(config_id, symbol)
);

-- Walk-forward analysis results
CREATE TABLE IF NOT EXISTS walk_forward_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id) ON DELETE CASCADE,
    window_number INT NOT NULL,
    window_start DATE,
    window_end DATE,
    is_in_sample BOOLEAN,
    sharpe_ratio DECIMAL(10,4),
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    total_trades INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Phase execution tracking
CREATE TABLE IF NOT EXISTS phase_execution (
    id SERIAL PRIMARY KEY,
    phase_number INT NOT NULL UNIQUE,
    phase_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    configs_tested INT DEFAULT 0,
    best_config_id INT REFERENCES strategy_configs(id),
    notes TEXT,
    error_message TEXT
);

-- Agent execution log
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50),
    phase INT,
    log_level VARCHAR(10),         -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB                  -- Additional context as JSON
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Stock data indexes
CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_date ON stock_data(symbol, date);
CREATE INDEX IF NOT EXISTS idx_stock_data_date ON stock_data(date);
CREATE INDEX IF NOT EXISTS idx_stock_data_symbol ON stock_data(symbol);

-- Candles indexes
CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol, candle_type, aggregation_days, date);
CREATE INDEX IF NOT EXISTS idx_candles_symbol ON candles(symbol);
CREATE INDEX IF NOT EXISTS idx_candles_type ON candles(candle_type, aggregation_days);
CREATE INDEX IF NOT EXISTS idx_candles_date ON candles(date);

-- Strategy configs indexes
CREATE INDEX IF NOT EXISTS idx_strategy_configs_phase ON strategy_configs(phase);
CREATE INDEX IF NOT EXISTS idx_strategy_configs_name ON strategy_configs(config_name);

-- Backtest results indexes
CREATE INDEX IF NOT EXISTS idx_backtest_config ON backtest_results(config_id);
CREATE INDEX IF NOT EXISTS idx_backtest_symbol ON backtest_results(symbol);
CREATE INDEX IF NOT EXISTS idx_backtest_sharpe ON backtest_results(sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_config_symbol ON backtest_results(config_id, symbol);

-- Walk-forward indexes
CREATE INDEX IF NOT EXISTS idx_wf_config ON walk_forward_results(config_id);
CREATE INDEX IF NOT EXISTS idx_wf_window ON walk_forward_results(window_number);
CREATE INDEX IF NOT EXISTS idx_wf_sample_type ON walk_forward_results(is_in_sample);

-- Phase execution indexes
CREATE INDEX IF NOT EXISTS idx_phase_exec ON phase_execution(phase_number, status);

-- Agent logs indexes
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_name, phase);
CREATE INDEX IF NOT EXISTS idx_agent_logs_level ON agent_logs(log_level);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Top performing configurations by phase
CREATE OR REPLACE VIEW v_top_configs_by_phase AS
SELECT
    sc.phase,
    sc.config_name,
    sc.candle_type,
    sc.aggregation_days,
    sc.mean_type,
    sc.mean_lookback,
    AVG(br.sharpe_ratio) as avg_sharpe,
    AVG(br.total_return) as avg_return,
    AVG(br.max_drawdown) as avg_max_drawdown,
    AVG(br.win_rate) as avg_win_rate,
    SUM(br.total_trades) as total_trades,
    COUNT(DISTINCT br.symbol) as num_stocks
FROM strategy_configs sc
JOIN backtest_results br ON sc.id = br.config_id
WHERE br.symbol != 'PORTFOLIO'  -- Exclude portfolio aggregates
GROUP BY sc.id, sc.phase, sc.config_name, sc.candle_type, sc.aggregation_days,
         sc.mean_type, sc.mean_lookback
ORDER BY sc.phase, avg_sharpe DESC;

-- Portfolio performance summary
CREATE OR REPLACE VIEW v_portfolio_performance AS
SELECT
    sc.config_name,
    sc.phase,
    br.sharpe_ratio as portfolio_sharpe,
    br.total_return as portfolio_return,
    br.max_drawdown as portfolio_max_drawdown,
    br.total_trades,
    br.win_rate,
    br.profit_factor,
    br.calmar_ratio
FROM strategy_configs sc
JOIN backtest_results br ON sc.id = br.config_id
WHERE br.symbol = 'PORTFOLIO'
ORDER BY br.sharpe_ratio DESC;

-- Walk-forward performance comparison
CREATE OR REPLACE VIEW v_walk_forward_comparison AS
SELECT
    sc.config_name,
    AVG(CASE WHEN wf.is_in_sample THEN wf.sharpe_ratio END) as avg_in_sample_sharpe,
    AVG(CASE WHEN NOT wf.is_in_sample THEN wf.sharpe_ratio END) as avg_out_sample_sharpe,
    AVG(CASE WHEN wf.is_in_sample THEN wf.total_return END) as avg_in_sample_return,
    AVG(CASE WHEN NOT wf.is_in_sample THEN wf.total_return END) as avg_out_sample_return,
    COUNT(DISTINCT wf.window_number) as num_windows
FROM strategy_configs sc
JOIN walk_forward_results wf ON sc.id = wf.config_id
GROUP BY sc.id, sc.config_name
HAVING AVG(CASE WHEN NOT wf.is_in_sample THEN wf.sharpe_ratio END) > 0.8
ORDER BY avg_out_sample_sharpe DESC;

-- Phase execution summary
CREATE OR REPLACE VIEW v_phase_summary AS
SELECT
    pe.phase_number,
    pe.phase_name,
    pe.status,
    pe.configs_tested,
    pe.started_at,
    pe.completed_at,
    EXTRACT(EPOCH FROM (pe.completed_at - pe.started_at))/3600 as duration_hours,
    sc.config_name as best_config,
    br.sharpe_ratio as best_sharpe
FROM phase_execution pe
LEFT JOIN strategy_configs sc ON pe.best_config_id = sc.id
LEFT JOIN backtest_results br ON sc.id = br.config_id AND br.symbol = 'PORTFOLIO'
ORDER BY pe.phase_number;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to calculate Sharpe ratio
CREATE OR REPLACE FUNCTION calculate_sharpe_ratio(
    returns DECIMAL[],
    risk_free_rate DECIMAL DEFAULT 0.02
) RETURNS DECIMAL AS $$
DECLARE
    avg_return DECIMAL;
    std_return DECIMAL;
    sharpe DECIMAL;
BEGIN
    SELECT AVG(r), STDDEV(r) INTO avg_return, std_return
    FROM unnest(returns) AS r;

    IF std_return = 0 OR std_return IS NULL THEN
        RETURN NULL;
    END IF;

    sharpe := (avg_return - risk_free_rate) / std_return;
    RETURN ROUND(sharpe, 4);
END;
$$ LANGUAGE plpgsql;

-- Function to log agent activity
CREATE OR REPLACE FUNCTION log_agent_activity(
    p_agent_name VARCHAR,
    p_phase INT,
    p_log_level VARCHAR,
    p_message TEXT,
    p_context JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO agent_logs (agent_name, phase, log_level, message, context)
    VALUES (p_agent_name, p_phase, p_log_level, p_message, p_context);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Initialize phase execution tracking
INSERT INTO phase_execution (phase_number, phase_name, status) VALUES
(1, 'Candle Type Baseline', 'pending'),
(2, 'Mean & StdDev Optimization', 'pending'),
(3, 'Entry/Exit Logic Refinement', 'pending'),
(4, 'Filter Integration', 'pending'),
(5, 'Risk Management Optimization', 'pending'),
(6, 'Final Validation & Stress Testing', 'pending')
ON CONFLICT (phase_number) DO NOTHING;

-- =============================================================================
-- MAINTENANCE
-- =============================================================================

-- Vacuum and analyze tables for optimal performance
VACUUM ANALYZE stock_data;
VACUUM ANALYZE candles;
VACUUM ANALYZE strategy_configs;
VACUUM ANALYZE backtest_results;
VACUUM ANALYZE walk_forward_results;

-- =============================================================================
-- COMPLETION
-- =============================================================================

SELECT 'Database schema initialized successfully!' as status;
SELECT 'Tables created: ' || count(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SELECT 'Views created: ' || count(*) FROM information_schema.views
WHERE table_schema = 'public';
