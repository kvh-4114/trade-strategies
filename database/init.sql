-- ============================================================================
-- Mean Reversion Trading Framework - PostgreSQL Database Schema
-- ============================================================================
-- This schema supports the multi-agent mean reversion testing framework
-- Optimized for AWS RDS PostgreSQL 15+
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: stock_data
-- Raw OHLCV stock price data
-- ============================================================================
CREATE TABLE IF NOT EXISTS stock_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    adjusted_close DECIMAL(10,2),  -- For split/dividend adjustments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

COMMENT ON TABLE stock_data IS 'Raw stock OHLCV data loaded from external sources';
COMMENT ON COLUMN stock_data.symbol IS 'Stock ticker symbol (e.g., AAPL, MSFT)';
COMMENT ON COLUMN stock_data.adjusted_close IS 'Split and dividend adjusted close price';

-- ============================================================================
-- TABLE: candles
-- Generated candles (Regular, Heiken Ashi, Linear Regression)
-- With 1-5 day aggregations (13 combinations total per stock)
-- ============================================================================
CREATE TABLE IF NOT EXISTS candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    candle_type VARCHAR(20) NOT NULL,  -- 'regular', 'heiken_ashi', 'linear_regression'
    aggregation_days INT NOT NULL,     -- 1, 2, 3, 4, 5
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, candle_type, aggregation_days)
);

COMMENT ON TABLE candles IS 'Generated candles with various types and aggregation periods';
COMMENT ON COLUMN candles.candle_type IS 'Type: regular, heiken_ashi, or linear_regression';
COMMENT ON COLUMN candles.aggregation_days IS 'Aggregation period: 1-5 days';

-- ============================================================================
-- TABLE: strategy_configs
-- Strategy parameter configurations for each test run
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_configs (
    id SERIAL PRIMARY KEY,
    config_name VARCHAR(100) UNIQUE NOT NULL,
    phase INT NOT NULL,

    -- Candle configuration
    candle_type VARCHAR(20),
    aggregation_days INT,

    -- Mean calculation
    mean_type VARCHAR(20),              -- 'SMA', 'EMA', 'LinReg', 'VWAP'
    mean_lookback INT,
    stddev_lookback INT,
    entry_threshold DECIMAL(5,2),       -- Number of standard deviations

    -- Exit configuration
    exit_type VARCHAR(20),              -- 'mean', 'opposite_band', 'profit_target', 'time_based'
    exit_threshold DECIMAL(5,2),        -- For profit target (%)
    exit_time_days INT,                 -- For time-based exit

    -- Filters
    use_volume_filter BOOLEAN DEFAULT FALSE,
    volume_threshold DECIMAL(5,2),      -- Multiplier of average volume
    use_rsi_filter BOOLEAN DEFAULT FALSE,
    rsi_oversold INT,
    rsi_overbought INT,
    use_trend_filter BOOLEAN DEFAULT FALSE,
    trend_ma_period INT,
    use_volatility_filter BOOLEAN DEFAULT FALSE,
    volatility_percentile INT,

    -- Position sizing & risk
    position_sizing VARCHAR(20),        -- 'fixed', 'volatility_adjusted', 'kelly'
    position_size DECIMAL(12,2),
    stop_loss_type VARCHAR(20),         -- 'none', 'fixed_pct', 'atr', 'trailing'
    stop_loss_value DECIMAL(5,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters JSONB                    -- Store all params as JSON for flexibility
);

COMMENT ON TABLE strategy_configs IS 'Strategy parameter configurations for backtesting';
COMMENT ON COLUMN strategy_configs.parameters IS 'Complete parameter set stored as JSON';

-- ============================================================================
-- TABLE: backtest_results
-- Performance metrics and results for each strategy configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id) ON DELETE CASCADE,
    symbol VARCHAR(10),                 -- Individual stock or 'PORTFOLIO' for aggregate
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Core performance metrics
    initial_capital DECIMAL(12,2),
    final_value DECIMAL(12,2),
    total_return DECIMAL(10,4),
    annualized_return DECIMAL(10,4),

    -- Risk-adjusted metrics
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),

    -- Drawdown metrics
    max_drawdown DECIMAL(10,4),
    max_drawdown_duration INT,          -- Days
    avg_drawdown DECIMAL(10,4),
    recovery_factor DECIMAL(10,4),

    -- Trade statistics
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DECIMAL(5,2),
    profit_factor DECIMAL(10,4),

    -- P&L statistics
    avg_win DECIMAL(10,4),
    avg_loss DECIMAL(10,4),
    avg_trade DECIMAL(10,4),
    largest_win DECIMAL(10,4),
    largest_loss DECIMAL(10,4),

    -- Time-based metrics
    avg_holding_period DECIMAL(10,2),   -- Days
    max_consecutive_wins INT,
    max_consecutive_losses INT,

    -- Risk metrics
    value_at_risk DECIMAL(10,4),        -- 95% VaR
    conditional_var DECIMAL(10,4),      -- CVaR (Expected Shortfall)

    -- Detailed data (stored as JSON)
    equity_curve JSONB,                 -- Daily equity values
    trade_log JSONB,                    -- All trades with entry/exit details
    monthly_returns JSONB,              -- Monthly return breakdown

    -- Execution metadata
    execution_time_seconds DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_results IS 'Backtest performance metrics and detailed results';
COMMENT ON COLUMN backtest_results.symbol IS 'Stock symbol or PORTFOLIO for aggregated results';
COMMENT ON COLUMN backtest_results.equity_curve IS 'Daily equity values stored as JSON array';

-- ============================================================================
-- TABLE: walk_forward_results
-- Walk-forward validation results
-- ============================================================================
CREATE TABLE IF NOT EXISTS walk_forward_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id) ON DELETE CASCADE,
    window_number INT,
    window_start DATE,
    window_end DATE,
    is_in_sample BOOLEAN,               -- TRUE for training, FALSE for testing

    -- Key metrics for this window
    sharpe_ratio DECIMAL(10,4),
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    total_trades INT,
    win_rate DECIMAL(5,2),

    -- Optimal parameters found (in-sample only)
    optimal_parameters JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE walk_forward_results IS 'Walk-forward validation results by window';
COMMENT ON COLUMN walk_forward_results.is_in_sample IS 'TRUE for training period, FALSE for test period';

-- ============================================================================
-- TABLE: phase_execution
-- Track execution of each testing phase
-- ============================================================================
CREATE TABLE IF NOT EXISTS phase_execution (
    id SERIAL PRIMARY KEY,
    phase_number INT NOT NULL,
    phase_name VARCHAR(100),
    status VARCHAR(20),                 -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Progress tracking
    total_configs INT,
    configs_completed INT,
    configs_failed INT,

    -- Results summary
    best_config_id INT REFERENCES strategy_configs(id),
    best_sharpe_ratio DECIMAL(10,4),
    avg_sharpe_ratio DECIMAL(10,4),

    -- Metadata
    config_file_path VARCHAR(255),
    notes TEXT,
    error_log TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE phase_execution IS 'Tracks progress and results of each testing phase';
COMMENT ON COLUMN phase_execution.status IS 'Status: pending, running, completed, failed';

-- ============================================================================
-- TABLE: agent_logs
-- Logging for all agent activities
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50),             -- 'orchestrator', 'agent_1', etc.
    phase INT,
    log_level VARCHAR(10),              -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT,
    context JSONB,                      -- Additional context as JSON
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE agent_logs IS 'Centralized logging for all agent activities';
COMMENT ON COLUMN agent_logs.context IS 'Additional log context stored as JSON';

-- ============================================================================
-- TABLE: monte_carlo_results
-- Monte Carlo simulation results for robustness testing
-- ============================================================================
CREATE TABLE IF NOT EXISTS monte_carlo_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id) ON DELETE CASCADE,
    simulation_number INT,

    -- Simulated metrics
    total_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),

    -- Simulation metadata
    resample_method VARCHAR(20),        -- 'bootstrap', 'parametric', etc.
    random_seed INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE monte_carlo_results IS 'Monte Carlo simulation results for strategy robustness';

-- ============================================================================
-- INDEXES
-- Optimized for query performance
-- ============================================================================

-- Stock data indexes
CREATE INDEX idx_stock_data_symbol ON stock_data(symbol);
CREATE INDEX idx_stock_data_date ON stock_data(date);
CREATE INDEX idx_stock_data_symbol_date ON stock_data(symbol, date);

-- Candles indexes
CREATE INDEX idx_candles_symbol ON candles(symbol);
CREATE INDEX idx_candles_type_agg ON candles(candle_type, aggregation_days);
CREATE INDEX idx_candles_lookup ON candles(symbol, candle_type, aggregation_days, date);
CREATE INDEX idx_candles_date ON candles(date);

-- Strategy configs indexes
CREATE INDEX idx_strategy_configs_phase ON strategy_configs(phase);
CREATE INDEX idx_strategy_configs_candle ON strategy_configs(candle_type, aggregation_days);

-- Backtest results indexes
CREATE INDEX idx_backtest_config ON backtest_results(config_id);
CREATE INDEX idx_backtest_symbol ON backtest_results(symbol);
CREATE INDEX idx_backtest_sharpe ON backtest_results(sharpe_ratio DESC);
CREATE INDEX idx_backtest_return ON backtest_results(total_return DESC);
CREATE INDEX idx_backtest_run_date ON backtest_results(run_date);

-- Walk-forward indexes
CREATE INDEX idx_walkforward_config ON walk_forward_results(config_id);
CREATE INDEX idx_walkforward_window ON walk_forward_results(window_number, is_in_sample);

-- Phase execution indexes
CREATE INDEX idx_phase_exec_number ON phase_execution(phase_number);
CREATE INDEX idx_phase_exec_status ON phase_execution(status);

-- Agent logs indexes
CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_name);
CREATE INDEX idx_agent_logs_timestamp ON agent_logs(timestamp DESC);
CREATE INDEX idx_agent_logs_level ON agent_logs(log_level);
CREATE INDEX idx_agent_logs_phase ON agent_logs(phase);

-- Monte Carlo indexes
CREATE INDEX idx_monte_carlo_config ON monte_carlo_results(config_id);

-- ============================================================================
-- VIEWS
-- Convenient views for common queries
-- ============================================================================

-- View: Top performing configs by phase
CREATE OR REPLACE VIEW v_top_configs_by_phase AS
SELECT
    sc.phase,
    sc.id as config_id,
    sc.config_name,
    sc.candle_type,
    sc.aggregation_days,
    sc.mean_type,
    sc.mean_lookback,
    AVG(br.sharpe_ratio) as avg_sharpe,
    AVG(br.total_return) as avg_return,
    AVG(br.max_drawdown) as avg_drawdown,
    AVG(br.win_rate) as avg_win_rate,
    SUM(br.total_trades) as total_trades,
    COUNT(DISTINCT br.symbol) as num_stocks
FROM strategy_configs sc
JOIN backtest_results br ON sc.id = br.config_id
WHERE br.symbol != 'PORTFOLIO'  -- Exclude portfolio aggregates
GROUP BY sc.phase, sc.id, sc.config_name, sc.candle_type,
         sc.aggregation_days, sc.mean_type, sc.mean_lookback
ORDER BY sc.phase, avg_sharpe DESC;

-- View: Phase summary statistics
CREATE OR REPLACE VIEW v_phase_summary AS
SELECT
    pe.phase_number,
    pe.phase_name,
    pe.status,
    pe.total_configs,
    pe.configs_completed,
    pe.best_sharpe_ratio,
    pe.avg_sharpe_ratio,
    sc.config_name as best_config_name,
    sc.candle_type as best_candle_type,
    pe.started_at,
    pe.completed_at,
    EXTRACT(EPOCH FROM (pe.completed_at - pe.started_at))/3600 as duration_hours
FROM phase_execution pe
LEFT JOIN strategy_configs sc ON pe.best_config_id = sc.id
ORDER BY pe.phase_number;

-- View: Recent agent activity
CREATE OR REPLACE VIEW v_recent_agent_activity AS
SELECT
    agent_name,
    phase,
    log_level,
    message,
    timestamp
FROM agent_logs
ORDER BY timestamp DESC
LIMIT 100;

-- ============================================================================
-- FUNCTIONS
-- Utility functions for common operations
-- ============================================================================

-- Function: Get top N configs for a phase
CREATE OR REPLACE FUNCTION get_top_configs(
    p_phase INT,
    p_limit INT DEFAULT 10,
    p_metric VARCHAR DEFAULT 'sharpe_ratio'
)
RETURNS TABLE (
    config_id INT,
    config_name VARCHAR,
    avg_metric DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.id,
        sc.config_name,
        AVG(
            CASE p_metric
                WHEN 'sharpe_ratio' THEN br.sharpe_ratio
                WHEN 'total_return' THEN br.total_return
                WHEN 'calmar_ratio' THEN br.calmar_ratio
                ELSE br.sharpe_ratio
            END
        ) as avg_metric
    FROM strategy_configs sc
    JOIN backtest_results br ON sc.id = br.config_id
    WHERE sc.phase = p_phase AND br.symbol != 'PORTFOLIO'
    GROUP BY sc.id, sc.config_name
    ORDER BY avg_metric DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate portfolio statistics
CREATE OR REPLACE FUNCTION calculate_portfolio_stats(
    p_config_id INT
)
RETURNS TABLE (
    avg_sharpe DECIMAL,
    avg_return DECIMAL,
    avg_drawdown DECIMAL,
    total_stocks INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        AVG(sharpe_ratio),
        AVG(total_return),
        AVG(max_drawdown),
        COUNT(DISTINCT symbol)::INT
    FROM backtest_results
    WHERE config_id = p_config_id AND symbol != 'PORTFOLIO';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- Insert initial phase records
-- ============================================================================

INSERT INTO phase_execution (phase_number, phase_name, status) VALUES
    (1, 'Candle Type Baseline', 'pending'),
    (2, 'Mean & StdDev Optimization', 'pending'),
    (3, 'Entry/Exit Logic Refinement', 'pending'),
    (4, 'Filter Integration', 'pending'),
    (5, 'Risk Management Optimization', 'pending'),
    (6, 'Final Validation & Stress Testing', 'pending')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- GRANTS
-- Set appropriate permissions (adjust based on your RDS user setup)
-- ============================================================================

-- Grant permissions to application user (replace 'app_user' with your RDS username)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- ============================================================================
-- COMPLETE
-- ============================================================================

-- Log completion
DO $$
BEGIN
    INSERT INTO agent_logs (agent_name, phase, log_level, message)
    VALUES ('database', 0, 'INFO', 'Database schema initialized successfully');
END $$;

-- Display summary
SELECT 'Database schema initialization complete!' as status;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'public';
