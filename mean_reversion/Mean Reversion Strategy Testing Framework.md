# Mean Reversion Strategy Testing Framework
## Architecture Blueprint for Multi-Agent Claude Code Implementation

---

## Executive Summary

This document provides a comprehensive blueprint for building a multi-agent mean reversion testing framework. The system uses an orchestration agent to coordinate specialized coding agents, each responsible for different phases of the testing pipeline. All code will be version-controlled in GitHub, with a Dockerized database for portability to AWS or other cloud environments.

---

## System Architecture Overview

### Multi-Agent Structure
```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION AGENT                        │
│  - Controls workflow execution                               │
│  - Manages inter-agent communication                         │
│  - Tracks progress and results                               │
│  - Generates final reports                                   │
└──────────────────┬──────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬─────────────┐
    │              │              │              │             │
    ▼              ▼              ▼              ▼             ▼
┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Agent  │   │ Agent    │   │ Agent    │   │ Agent    │   │ Agent    │
│   1    │   │    2     │   │    3     │   │    4     │   │    5     │
│        │   │          │   │          │   │          │   │          │
│ Data & │   │ Strategy │   │Optimize  │   │Analysis &│   │Infra &   │
│ Candle │   │ Core     │   │& Test    │   │Reporting │   │Deploy    │
└────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Technology Stack

- **Language:** Python 3.10+
- **Backtesting:** Backtrader
- **Database:** PostgreSQL 15 (Dockerized)
- **Orchestration:** Custom Python orchestrator with agent management
- **Version Control:** GitHub
- **Containerization:** Docker & Docker Compose
- **Cloud Deployment:** AWS (EC2, RDS, S3) ready
- **Data Processing:** Pandas, NumPy
- **Parallelization:** Multiprocessing, Joblib
- **Visualization:** Matplotlib, Plotly

---

## Project Structure
```
mean-reversion-framework/
│
├── README.md
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
│
├── orchestrator/
│   ├── __init__.py
│   ├── main_orchestrator.py      # Main orchestration logic
│   ├── agent_manager.py           # Agent lifecycle management
│   ├── config.py                  # Global configuration
│   └── state_manager.py           # Track pipeline state
│
├── agents/
│   ├── __init__.py
│   ├── agent_1_data_candles/
│   │   ├── __init__.py
│   │   ├── candle_generator.py
│   │   ├── regular_candles.py
│   │   ├── heiken_ashi.py
│   │   ├── linear_regression.py
│   │   ├── aggregator.py
│   │   └── tests/
│   │
│   ├── agent_2_strategy_core/
│   │   ├── __init__.py
│   │   ├── base_strategy.py
│   │   ├── mean_calculators.py
│   │   ├── stddev_bands.py
│   │   ├── entry_logic.py
│   │   ├── exit_logic.py
│   │   ├── filters.py
│   │   └── tests/
│   │
│   ├── agent_3_optimization/
│   │   ├── __init__.py
│   │   ├── grid_search.py
│   │   ├── walk_forward.py
│   │   ├── parallel_executor.py
│   │   ├── parameter_space.py
│   │   └── tests/
│   │
│   ├── agent_4_analysis/
│   │   ├── __init__.py
│   │   ├── metrics_calculator.py
│   │   ├── performance_stats.py
│   │   ├── visualization.py
│   │   ├── report_generator.py
│   │   └── tests/
│   │
│   └── agent_5_infrastructure/
│       ├── __init__.py
│       ├── database_manager.py
│       ├── data_loader.py
│       ├── schema.sql
│       ├── aws_deployment.py
│       └── tests/
│
├── database/
│   ├── init.sql                   # Database initialization
│   ├── migrations/
│   └── Dockerfile.postgres
│
├── data/
│   ├── raw/                       # Raw stock data
│   ├── processed/                 # Processed candles
│   └── results/                   # Backtest results
│
├── configs/
│   ├── phase_1_config.yaml
│   ├── phase_2_config.yaml
│   ├── phase_3_config.yaml
│   ├── phase_4_config.yaml
│   ├── phase_5_config.yaml
│   └── phase_6_config.yaml
│
├── notebooks/
│   └── exploratory_analysis.ipynb
│
├── scripts/
│   ├── setup_environment.sh
│   ├── run_phase.py
│   └── deploy_aws.sh
│
└── tests/
    ├── integration/
    └── unit/
```

---

## Database Schema (PostgreSQL)

### Tables
```sql
-- Stock price data
CREATE TABLE stock_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    UNIQUE(symbol, date)
);

-- Generated candles (all types)
CREATE TABLE candles (
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
    UNIQUE(symbol, date, candle_type, aggregation_days)
);

-- Strategy configurations
CREATE TABLE strategy_configs (
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
    use_volume_filter BOOLEAN,
    use_rsi_filter BOOLEAN,
    use_trend_filter BOOLEAN,
    use_volatility_filter BOOLEAN,
    position_sizing VARCHAR(20),
    stop_loss_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters JSONB              -- Store all params as JSON
);

-- Backtest results
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id),
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
    
    -- Additional data
    equity_curve JSONB,
    trade_log JSONB,
    monthly_returns JSONB
);

-- Walk-forward results
CREATE TABLE walk_forward_results (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES strategy_configs(id),
    window_start DATE,
    window_end DATE,
    is_in_sample BOOLEAN,
    sharpe_ratio DECIMAL(10,4),
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    total_trades INT
);

-- Phase tracking
CREATE TABLE phase_execution (
    id SERIAL PRIMARY KEY,
    phase_number INT NOT NULL,
    phase_name VARCHAR(100),
    status VARCHAR(20),            -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    configs_tested INT,
    best_config_id INT REFERENCES strategy_configs(id),
    notes TEXT
);

-- Agent execution log
CREATE TABLE agent_logs (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50),
    phase INT,
    log_level VARCHAR(10),
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_data_symbol_date ON stock_data(symbol, date);
CREATE INDEX idx_candles_lookup ON candles(symbol, candle_type, aggregation_days, date);
CREATE INDEX idx_backtest_config ON backtest_results(config_id);
CREATE INDEX idx_phase_exec ON phase_execution(phase_number, status);
```

---

## Agent Specifications

### ORCHESTRATION AGENT

**Responsibilities:**
- Initialize the testing pipeline
- Load phase configurations from YAML
- Spawn and manage specialized agents
- Coordinate data flow between agents
- Monitor progress and handle failures
- Generate master reports
- Manage GitHub commits for each phase

**Key Files:**
- `orchestrator/main_orchestrator.py`
- `orchestrator/agent_manager.py`
- `orchestrator/state_manager.py`

**API:**
```python
class Orchestrator:
    def __init__(self, config_path: str)
    def run_pipeline(self, phases: List[int])
    def run_phase(self, phase_num: int)
    def get_phase_status(self, phase_num: int) -> Dict
    def aggregate_results(self) -> pd.DataFrame
    def generate_master_report(self)
```

---

### AGENT 1: Data & Candle Generation

**Responsibilities:**
- Load raw stock data from CSV/API
- Generate regular OHLC candles
- Generate Heiken Ashi candles
- Generate Linear Regression candles
- Create aggregated candles (2-5 day)
- Store all candles in database
- Validate data quality

**Key Algorithms:**

**Heiken Ashi:**
```python
HA_Close = (Open + High + Low + Close) / 4
HA_Open = (Previous HA_Open + Previous HA_Close) / 2
HA_High = max(High, HA_Open, HA_Close)
HA_Low = min(Low, HA_Open, HA_Close)
```

**Linear Regression Candles:**
```python
# For each period, fit linear regression to close prices
# LR_Close = predicted value from regression
# LR_Open = LR value from previous period
# LR_High/Low = max/min of actual high/low and LR values
```

**Deliverables:**
- All 13 candle type combinations in database
- Data quality report
- Candle visualization samples

**Files:**
- `agents/agent_1_data_candles/candle_generator.py`
- `agents/agent_1_data_candles/regular_candles.py`
- `agents/agent_1_data_candles/heiken_ashi.py`
- `agents/agent_1_data_candles/linear_regression.py`
- `agents/agent_1_data_candles/aggregator.py`

**API:**
```python
class CandleGenerator:
    def generate_regular_candles(self, symbol: str, df: pd.DataFrame)
    def generate_heiken_ashi(self, symbol: str, df: pd.DataFrame)
    def generate_linear_regression(self, symbol: str, df: pd.DataFrame, window: int = 5)
    def aggregate_candles(self, candles: pd.DataFrame, days: int)
    def save_to_database(self, candles: pd.DataFrame, candle_type: str, agg_days: int)
```

---

### AGENT 2: Strategy Core

**Responsibilities:**
- Implement base mean reversion strategy in Backtrader
- Create mean calculators (SMA, EMA, LinReg, VWAP)
- Implement standard deviation bands
- Build entry logic variations
- Build exit logic variations
- Implement filters (volume, RSI, trend, volatility)
- Create modular strategy components

**Key Components:**

**Mean Calculators:**
- Simple Moving Average
- Exponential Moving Average
- Linear Regression Line
- VWAP (Volume Weighted Average Price)

**Entry Logic Variations:**
- Close below lower band
- Touch lower band
- Consecutive periods below band

**Exit Logic Variations:**
- Return to mean (0 StdDev)
- Opposite band
- Fixed profit target (%)
- Time-based exit

**Files:**
- `agents/agent_2_strategy_core/base_strategy.py`
- `agents/agent_2_strategy_core/mean_calculators.py`
- `agents/agent_2_strategy_core/stddev_bands.py`
- `agents/agent_2_strategy_core/entry_logic.py`
- `agents/agent_2_strategy_core/exit_logic.py`
- `agents/agent_2_strategy_core/filters.py`

**API:**
```python
class MeanReversionStrategy(bt.Strategy):
    params = (
        ('candle_type', 'regular'),
        ('aggregation_days', 1),
        ('mean_type', 'SMA'),
        ('mean_lookback', 20),
        ('stddev_lookback', 20),
        ('entry_threshold', 2.0),
        ('exit_type', 'mean'),
        ('use_volume_filter', False),
        ('use_rsi_filter', False),
        ('use_trend_filter', False),
        ('position_size', 10000),
        ('stop_loss_pct', None),
    )
    
    def __init__(self)
    def next(self)
    def notify_order(self, order)
    def notify_trade(self, trade)
```

---

### AGENT 3: Optimization & Testing

**Responsibilities:**
- Execute grid search across parameter space
- Implement walk-forward validation
- Run parallel backtests across stocks
- Manage parameter combinations
- Store results in database
- Track phase progress
- Handle failures and retries

**Optimization Strategy:**

**Phase 1: Candle Baseline (13 tests)**
```python
candle_configs = [
    ('regular', 1),
    ('heiken_ashi', 1),
    ('linear_regression', 1),
    ('regular', 2), ('regular', 3), ('regular', 4), ('regular', 5),
    ('heiken_ashi', 2), ('heiken_ashi', 3), ('heiken_ashi', 4), ('heiken_ashi', 5),
    ('linear_regression', 2), ('linear_regression', 3), ('linear_regression', 4), ('linear_regression', 5),
]
fixed_params = {
    'mean_type': 'SMA',
    'mean_lookback': 20,
    'entry_threshold': 2.0,
    'exit_type': 'mean'
}
```

**Phase 2: Parameter Grid (400 tests)**
```python
# Top 5 candles from Phase 1
parameter_grid = {
    'mean_type': ['SMA', 'EMA', 'LinReg', 'VWAP'],
    'mean_lookback': [10, 20, 30, 50, 100],
    'entry_threshold': [1.5, 2.0, 2.5, 3.0]
}
# 5 candles × 4 × 5 × 4 = 400 combinations
```

**Walk-Forward Validation:**
- Training window: 2 years
- Test window: 1 year
- Step: 6 months
- Total windows: ~14 for 10-year dataset

**Files:**
- `agents/agent_3_optimization/grid_search.py`
- `agents/agent_3_optimization/walk_forward.py`
- `agents/agent_3_optimization/parallel_executor.py`
- `agents/agent_3_optimization/parameter_space.py`

**API:**
```python
class OptimizationEngine:
    def __init__(self, db_manager, strategy_class, stocks: List[str])
    def run_grid_search(self, param_grid: Dict, phase: int)
    def run_walk_forward(self, config: Dict, train_years: int = 2, test_years: int = 1)
    def parallel_backtest(self, configs: List[Dict], n_jobs: int = -1)
    def save_results(self, results: List[Dict])
    def get_top_configs(self, phase: int, n: int = 10, metric: str = 'sharpe_ratio')
```

---

### AGENT 4: Analysis & Reporting

**Responsibilities:**
- Calculate performance metrics
- Generate equity curves
- Create comparison visualizations
- Perform statistical analysis
- Generate phase reports
- Create final deliverables
- Sensitivity analysis

**Key Metrics:**

**Primary:**
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Calmar Ratio
- Total Return

**Secondary:**
- Profit Factor
- Win Rate
- Average Win/Loss
- Recovery Factor
- Value at Risk (VaR)

**Robustness Tests:**
- Parameter sensitivity (±10% changes)
- Regime analysis (bull/bear/sideways)
- Monte Carlo simulation
- Bootstrap resampling

**Files:**
- `agents/agent_4_analysis/metrics_calculator.py`
- `agents/agent_4_analysis/performance_stats.py`
- `agents/agent_4_analysis/visualization.py`
- `agents/agent_4_analysis/report_generator.py`

**API:**
```python
class AnalysisEngine:
    def __init__(self, db_manager)
    def calculate_metrics(self, equity_curve: pd.Series, trades: pd.DataFrame) -> Dict
    def generate_phase_report(self, phase: int, top_n: int = 10)
    def plot_equity_curves(self, config_ids: List[int])
    def plot_drawdown(self, config_id: int)
    def sensitivity_analysis(self, config_id: int, param: str, range_pct: float = 0.1)
    def monte_carlo_simulation(self, config_id: int, n_simulations: int = 1000)
    def generate_final_report(self, top_configs: List[int])
```

---

### AGENT 5: Infrastructure & Deployment

**Responsibilities:**
- Manage PostgreSQL database
- Handle Docker containers
- Load stock data
- Backup results
- AWS deployment scripts
- Environment setup
- Monitoring and logging

**Docker Setup:**

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  postgres:
    build:
      context: ./database
      dockerfile: Dockerfile.postgres
    container_name: mean_reversion_db
    environment:
      POSTGRES_DB: mean_reversion
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    container_name: mean_reversion_app
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: mean_reversion
      DB_USER: trader
      DB_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./data:/app/data
      - ./results:/app/results
    command: python orchestrator/main_orchestrator.py

volumes:
  postgres_data:
```

**Files:**
- `agents/agent_5_infrastructure/database_manager.py`
- `agents/agent_5_infrastructure/data_loader.py`
- `agents/agent_5_infrastructure/aws_deployment.py`
- `database/Dockerfile.postgres`
- `docker-compose.yml`

**API:**
```python
class DatabaseManager:
    def __init__(self, host: str, port: int, database: str, user: str, password: str)
    def connect(self)
    def execute_query(self, query: str, params: tuple = None)
    def load_stock_data(self, symbol: str) -> pd.DataFrame
    def save_candles(self, candles: pd.DataFrame, candle_type: str, agg_days: int)
    def save_strategy_config(self, config: Dict) -> int
    def save_backtest_results(self, config_id: int, results: Dict)
    def get_top_configs(self, phase: int, n: int, metric: str) -> List[Dict]
    def backup_database(self, backup_path: str)
```

---

## Execution Workflow

### Phase 1: Candle Type Baseline

**Objective:** Test all 13 candle combinations with fixed parameters

**Steps:**
1. **Orchestrator** loads `configs/phase_1_config.yaml`
2. **Agent 1** generates all candle types for 250 stocks
3. **Agent 2** prepares base strategy with fixed params
4. **Agent 3** runs 13 backtests (1 per candle type) across all stocks
5. **Agent 4** analyzes results and ranks by Sharpe ratio
6. **Agent 4** generates Phase 1 report with top 5 candle types
7. **Orchestrator** commits results to GitHub

**Expected Output:**
- Top 5 candle configurations
- Performance comparison table
- Equity curve visualizations
- Database populated with results

**Config File: `configs/phase_1_config.yaml`**
```yaml
phase: 1
name: "Candle Type Baseline"

candle_types:
  - type: "regular"
    aggregations: [1, 2, 3, 4, 5]
  - type: "heiken_ashi"
    aggregations: [1, 2, 3, 4, 5]
  - type: "linear_regression"
    aggregations: [1, 2, 3, 4, 5]

fixed_parameters:
  mean_type: "SMA"
  mean_lookback: 20
  stddev_lookback: 20
  entry_threshold: 2.0
  exit_type: "mean"
  position_size: 10000
  use_filters: false

stocks:
  count: 250
  data_path: "data/raw/stock_data.csv"

execution:
  parallel: true
  n_jobs: 8

success_criteria:
  min_trades: 100
  min_sharpe: 0.5
```

---

### Phase 2: Mean & StdDev Optimization

**Objective:** Optimize statistical parameters for top 5 candle types

**Steps:**
1. **Orchestrator** retrieves top 5 configs from Phase 1
2. **Agent 3** generates parameter grid (400 combinations)
3. **Agent 3** runs parallel backtests
4. **Agent 4** performs walk-forward validation on top 20
5. **Agent 4** generates Phase 2 report
6. **Orchestrator** commits results to GitHub

**Expected Output:**
- Top 20 configurations ranked by walk-forward Sharpe
- Parameter sensitivity analysis
- Walk-forward performance breakdown

**Config File: `configs/phase_2_config.yaml`**
```yaml
phase: 2
name: "Mean & StdDev Optimization"

parameter_grid:
  mean_type: ["SMA", "EMA", "LinReg", "VWAP"]
  mean_lookback: [10, 20, 30, 50, 100]
  stddev_lookback: [10, 20, 30, 50, 100]
  entry_threshold: [1.5, 2.0, 2.5, 3.0]

top_configs_from_phase: 1
top_n: 5

walk_forward:
  enabled: true
  train_years: 2
  test_years: 1
  step_months: 6

execution:
  parallel: true
  n_jobs: 16

success_criteria:
  min_sharpe_in_sample: 1.0
  min_sharpe_out_sample: 0.8
  max_drawdown: 0.30
```

---

### Phase 3: Entry/Exit Logic Refinement

**Objective:** Test entry and exit variations

**Steps:**
1. **Orchestrator** retrieves top 10 configs from Phase 2
2. **Agent 2** implements entry/exit variations
3. **Agent 3** tests all combinations
4. **Agent 4** analyzes and ranks
5. **Orchestrator** commits results to GitHub

**Config File: `configs/phase_3_config.yaml`**
```yaml
phase: 3
name: "Entry/Exit Logic Refinement"

top_configs_from_phase: 2
top_n: 10

entry_variations:
  - "close_below_band"
  - "touch_band"
  - "consecutive_2"
  - "consecutive_3"

exit_variations:
  - "return_to_mean"
  - "opposite_band"
  - "profit_target_5pct"
  - "profit_target_10pct"
  - "time_exit_10days"
  - "time_exit_20days"

execution:
  parallel: true
  n_jobs: 16
```

---

### Phase 4: Filter Integration

**Objective:** Add robustness filters

**Steps:**
1. **Orchestrator** retrieves top 20 configs from Phase 3
2. **Agent 2** implements filters
3. **Agent 3** tests filter combinations
4. **Agent 4** analyzes impact
5. **Orchestrator** commits results to GitHub

**Config File: `configs/phase_4_config.yaml`**
```yaml
phase: 4
name: "Filter Integration"

top_configs_from_phase: 3
top_n: 20

filters:
  volume:
    enabled: [true, false]
    threshold: 1.2  # 1.2x average volume
  
  rsi:
    enabled: [true, false]
    oversold: [25, 30, 35]
    overbought: [65, 70, 75]
  
  trend:
    enabled: [true, false]
    ma_period: 200
  
  volatility:
    enabled: [true, false]
    atr_percentile: [20, 50, 80]

execution:
  parallel: true
  n_jobs: 16
```

---

### Phase 5: Risk Management

**Objective:** Optimize position sizing and stops

**Steps:**
1. **Orchestrator** retrieves top 10 configs from Phase 4
2. **Agent 2** implements risk management variations
3. **Agent 3** tests combinations
4. **Agent 4** analyzes risk-adjusted returns
5. **Orchestrator** commits results to GitHub

**Config File: `configs/phase_5_config.yaml`**
```yaml
phase: 5
name: "Risk Management Optimization"

top_configs_from_phase: 4
top_n: 10

position_sizing:
  - type: "fixed"
    amount: 10000
  - type: "volatility_adjusted"
    base_amount: 10000
    atr_multiplier: 1.0
  - type: "kelly"
    max_allocation: 0.25

stop_loss:
  - type: "none"
  - type: "fixed_pct"
    pct: [0.02, 0.05, 0.08]
  - type: "atr"
    multiplier: [1.5, 2.0, 2.5]
  - type: "trailing"
    pct: [0.03, 0.05]

execution:
  parallel: true
  n_jobs: 16
```

---

### Phase 6: Final Validation

**Objective:** Stress test and validate top strategies

**Steps:**
1. **Orchestrator** retrieves top 10 configs from Phase 5
2. **Agent 3** runs Monte Carlo simulations
3. **Agent 3** performs extensive walk-forward
4. **Agent 4** tests on held-out stocks (20%)
5. **Agent 4** performs regime analysis
6. **Agent 4** generates final comprehensive report
7. **Orchestrator** packages deliverables and commits to GitHub

**Config File: `configs/phase_6_config.yaml`**
```yaml
phase: 6
name: "Final Validation & Stress Testing"

top_configs_from_phase: 5
top_n: 10

validation:
  monte_carlo:
    n_simulations: 1000
    resample_method: "bootstrap"
  
  walk_forward:
    train_years: 2
    test_years: 1
    step_months: 3
  
  out_of_sample:
    holdout_pct: 0.20
    random_seed: 42
  
  regime_analysis:
    regimes: ["bull", "bear", "sideways"]
    regime_definition:
      bull: "market_return > 0.10"
      bear: "market_return < -0.10"
      sideways: "abs(market_return) <= 0.10"
  
  transaction_costs:
    slippage_bps: [1, 5, 10]
    commission_per_trade: [0, 1, 5]

deliverables:
  - "final_report.pdf"
  - "top_10_strategies.csv"
  - "equity_curves.png"
  - "parameter_sensitivity.png"
  - "production_code/"

execution:
  parallel: true
  n_jobs: 8
```

---

## GitHub Repository Structure
```
Repository: mean-reversion-trading-framework

Branches:
├── main                    # Production-ready code
├── development            # Active development
├── phase-1                # Phase 1 development
├── phase-2                # Phase 2 development
├── phase-3                # Phase 3 development
├── phase-4                # Phase 4 development
├── phase-5                # Phase 5 development
└── phase-6                # Phase 6 development

Commit Strategy:
- Each phase gets its own branch
- Orchestrator commits after each phase completion
- Merge to development after validation
- Tag releases: v1.0-phase1, v1.0-phase2, etc.
```

---

## Instructions for Claude Code

### Setup Instructions

**Step 1: Initial Setup**
```bash
# Clone repository
git clone <repo-url>
cd mean-reversion-trading-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your database password

# Start Docker containers
docker-compose up -d

# Verify database connection
python scripts/verify_setup.py
```

**Step 2: Load Stock Data**
```bash
# Place your stock data CSV in data/raw/
# Format: symbol, date, open, high, low, close, volume

python agents/agent_5_infrastructure/data_loader.py \
  --input data/raw/stock_data.csv \
  --symbols-count 250
```

---

### Running the Pipeline

**Option 1: Run All Phases Sequentially**
```bash
python orchestrator/main_orchestrator.py --phases all
```

**Option 2: Run Specific Phase**
```bash
python orchestrator/main_orchestrator.py --phase 1
```

**Option 3: Run Phases 1-3**
```bash
python orchestrator/main_orchestrator.py --phases 1,2,3
```

---

### Agent-Specific Instructions

#### For Agent 1 (Data & Candles)

**Objective:** Generate all candle types

**Task:**
1. Read stock data from PostgreSQL `stock_data` table
2. Implement three candle generators:
   - Regular OHLC (passthrough)
   - Heiken Ashi (use formulas above)
   - Linear Regression (5-period window default)
3. Implement aggregation for 2-5 day candles
4. Store results in `candles` table
5. Create data quality report

**Validation:**
- Verify all 13 candle combinations exist for all stocks
- Visual spot-check: plot samples of each candle type
- No missing dates in continuous sequences

**Deliverable:**
```python
# Expected database state after Agent 1
# candles table should contain:
# 250 stocks × 13 candle types × ~2500 trading days = ~8.1M records
```

---

#### For Agent 2 (Strategy Core)

**Objective:** Build modular mean reversion strategy

**Task:**
1. Create Backtrader strategy class with configurable parameters
2. Implement 4 mean calculators as Backtrader indicators
3. Implement standard deviation bands
4. Create entry logic with 4 variations
5. Create exit logic with 6 variations
6. Implement 4 filter types
7. Ensure strategy can accept any candle type from database

**Key Implementation Notes:**
```python
# Strategy must fetch correct candle type from database
class MeanReversionStrategy(bt.Strategy):
    def __init__(self):
        # Load candles based on params
        candle_type = self.params.candle_type
        agg_days = self.params.aggregation_days
        
        # Fetch from database or dataframe
        # self.data will be the candle dataframe
        
        # Initialize mean calculator
        if self.params.mean_type == 'SMA':
            self.mean = bt.indicators.SMA(self.data.close, period=self.params.mean_lookback)
        elif self.params.mean_type == 'EMA':
            self.mean = bt.indicators.EMA(self.data.close, period=self.params.mean_lookback)
        # ... etc
        
        # Calculate standard deviation
        self.stddev = bt.indicators.StdDev(self.data.close, period=self.params.stddev_lookback)
        
        # Calculate bands
        self.upper_band = self.mean + (self.params.entry_threshold * self.stddev)
        self.lower_band = self.mean - (self.params.entry_threshold * self.stddev)
```

**Deliverable:**
- Working strategy that passes unit tests
- Documentation of all parameters
- Example backtests on 3 sample stocks

---

#### For Agent 3 (Optimization & Testing)

**Objective:** Run massive parallel optimization

**Task:**
1. Build parameter grid generator for each phase
2. Implement parallel executor using `multiprocessing` or `joblib`
3. For each parameter combination:
   - Create strategy config
   - Run backtest on all 250 stocks
   - Aggregate results
   - Store in database
4. Implement walk-forward validation
5. Track progress and handle failures

**Parallelization Strategy:**
```python
# Example structure
from joblib import Parallel, delayed

def run_single_backtest(symbol, config):
    """Run backtest for one stock with one config"""
    cerebro = bt.Cerebro()
    # Load data for this symbol
    data = load_candles_from_db(symbol, config['candle_type'], config['aggregation_days'])
    cerebro.adddata(data)
    cerebro.addstrategy(MeanReversionStrategy, **config)
    results = cerebro.run()
    return extract_metrics(results)

def run_config_across_portfolio(config, symbols):
    """Run one config across all stocks in parallel"""
    results = Parallel(n_jobs=-1)(
        delayed(run_single_backtest)(symbol, config) for symbol in symbols
    )
    return aggregate_results(results)

# Phase 1: Test 13 candle configs
for candle_config in candle_configs:
    config = {**candle_config, **fixed_params}
    portfolio_results = run_config_across_portfolio(config, all_symbols)
    save_to_database(config, portfolio_results)
```

**Deliverable:**
- Complete backtest results for all phases
- Performance comparison tables
- Top N configs for each phase stored in database

---

#### For Agent 4 (Analysis & Reporting)

**Objective:** Generate insights and reports

**Task:**
1. Query database for backtest results
2. Calculate all performance metrics
3. Generate visualizations:
   - Equity curves (top 10 configs)
   - Drawdown plots
   - Parameter heatmaps
   - Win rate distributions
4. Perform statistical tests
5. Generate phase reports (PDF + HTML)
6. Generate final deliverable package

**Report Template for Each Phase:**
```markdown
# Phase X Report: [Phase Name]

## Executive Summary
- Configurations tested: XXX
- Top configuration: [config name]
- Best Sharpe Ratio: X.XX
- Key findings: [bullet points]

## Top 10 Configurations
[Table with: Rank, Config, Sharpe, Return, Drawdown, Win Rate, Trades]

## Performance Analysis
[Equity curves chart]
[Drawdown chart]
[Monthly returns heatmap]

## Statistical Analysis
- Mean Sharpe across all configs: X.XX
- Std Dev of Sharpe: X.XX
- Configs passing criteria: XX / XXX

## Parameter Sensitivity
[Heatmap showing impact of each parameter]

## Next Steps
[Recommendations for next phase]
```

**Deliverable:**
- Phase reports (1-6)
- Final comprehensive report
- All visualizations
- CSV exports of top configs

---

#### For Agent 5 (Infrastructure & Deployment)

**Objective:** Manage infrastructure and deployment

**Task:**
1. Setup PostgreSQL database with schema
2. Create Docker Compose configuration
3. Implement database manager class
4. Load stock data from CSV to database
5. Create AWS deployment scripts
6. Implement backup procedures

**AWS Deployment Steps:**
```bash
# 1. Launch EC2 instance (t3.2xlarge recommended)
# 2. Install Docker and Docker Compose
# 3. Clone repository
# 4. Setup environment variables
# 5. Start containers
# 6. Optional: Use RDS for PostgreSQL instead of container
# 7. Optional: Store results in S3

# deployment script
./scripts/deploy_aws.sh \
  --instance-type t3.2xlarge \
  --region us-east-1 \
  --key-pair your-keypair
```

**Database Backup:**
```bash
# Automated backup script
docker exec mean_reversion_db pg_dump -U trader mean_reversion > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i mean_reversion_db psql -U trader mean_reversion < backup_20240101.sql
```

**Deliverable:**
- Working Docker setup
- Database fully initialized
- AWS deployment scripts
- Backup/restore procedures documented

---

## Success Criteria

### Per Phase Success Criteria

**Phase 1:**
- ✅ All 13 candle types generated
- ✅ At least 3 configs with Sharpe > 0.5
- ✅ Minimum 100 trades per config

**Phase 2:**
- ✅ At least 5 configs with in-sample Sharpe > 1.0
- ✅ At least 3 configs with out-of-sample Sharpe > 0.8
- ✅ Walk-forward validation complete

**Phase 3:**
- ✅ Improved Sharpe ratio vs Phase 2 (avg +10%)
- ✅ At least 10 configs with Sharpe > 1.2

**Phase 4:**
- ✅ At least 5 configs with filters improving Sharpe
- ✅ Reduced drawdown vs Phase 3 (avg -5%)

**Phase 5:**
- ✅ Calmar ratio > 1.5 for top configs
- ✅ Optimized risk-adjusted returns

**Phase 6:**
- ✅ Monte Carlo simulation shows 95% confidence > 0% return
- ✅ Positive returns in at least 7/10 years
- ✅ Out-of-sample validation successful
- ✅ Production-ready code delivered

---

## Final Deliverables

1. **Top 10 Strategy Configurations** (CSV + JSON)
2. **Comprehensive Final Report** (PDF, 30-50 pages)
3. **Production-Ready Code** (Python package)
4. **Complete Database** (PostgreSQL dump)
5. **Equity Curves & Visualizations** (PNG/PDF)
6. **Walk-Forward Results** (detailed breakdown)
7. **Parameter Sensitivity Analysis** (interactive HTML)
8. **Deployment Guide** (Markdown)
9. **Video Presentation** (optional, 15-min summary)

---

## Monitoring & Logging

### Orchestrator Dashboard
```python
# Real-time progress tracking
{
    "current_phase": 2,
    "phase_status": "running",
    "progress": "145/400 configs tested (36%)",
    "estimated_completion": "2024-01-15 18:30:00",
    "top_sharpe_so_far": 1.87,
    "active_agents": ["agent_3", "agent_4"]
}
```

### Logging Strategy
- All agents log to `agent_logs` table
- Orchestrator maintains master log file
- Error notifications sent to console
- Progress updates every 10 configs

---

## Estimated Resource Requirements

### Computational
- **CPU:** 16-32 cores recommended
- **RAM:** 32-64 GB
- **Storage:** 100 GB SSD (database + results)
- **Runtime:** ~1-2 weeks for full pipeline

### AWS Cost Estimate (if deploying to cloud)
- **EC2 t3.2xlarge:** ~$0.33/hour × 336 hours = $111
- **RDS PostgreSQL:** ~$100/month (optional)
- **S3 Storage:** ~$5/month
- **Total:** ~$200-250 for complete run

---

## Risk Mitigation

1. **Overfitting:** Walk-forward validation, out-of-sample testing
2. **Data Quality:** Automated quality checks by Agent 1
3. **Code Failures:** Retry logic, checkpointing, state management
4. **Infrastructure:** Docker ensures portability, easy recovery
5. **Version Control:** All phases committed to Git, tagged releases

---

## Questions for Claude Code

As you begin implementation, consider:

1. **Should we parallelize at the stock level or config level?**
   - Stock level: Run all configs on one stock in parallel
   - Config level: Run one config on all stocks in parallel
   - Recommendation: Config level (better load balancing)

2. **How should we handle agent communication?**
   - Message queue (RabbitMQ/Redis)
   - Shared database state
   - File-based handoffs
   - Recommendation: Database state + event logging

3. **Should agents be separate processes or threads?**
   - Recommendation: Separate processes for true parallelism

4. **How should we checkpoint progress?**
   - Every N configs tested
   - Every N minutes
   - Recommendation: Every 50 configs + every 30 minutes

---

## Getting Started with Claude Code

### Initial Deployment Steps

**Step 1: Repository Setup**
```bash
# Create GitHub repository
gh repo create mean-reversion-trading-framework --public
cd mean-reversion-trading-framework

# Initialize git
git init
git add .
git commit -m "Initial commit: Project structure"
git branch -M main
git push -u origin main
```

**Step 2: Spawn Agents**

Each agent can be developed in parallel by different Claude Code instances:

1. **Agent 1:** Focus on `agents/agent_1_data_candles/`
2. **Agent 2:** Focus on `agents/agent_2_strategy_core/`
3. **Agent 3:** Focus on `agents/agent_3_optimization/`
4. **Agent 4:** Focus on `agents/agent_4_analysis/`
5. **Agent 5:** Focus on `agents/agent_5_infrastructure/`
6. **Orchestrator:** Coordinates all agents

**Step 3: Integration Testing**
```bash
# Run integration tests
pytest tests/integration/

# Run end-to-end test with small dataset
python orchestrator/main_orchestrator.py \
  --phase 1 \
  --test-mode \
  --stocks 10 \
  --max-configs 5
```

---

## Conclusion

This blueprint provides a complete roadmap for building a sophisticated, scalable mean reversion testing framework. The multi-agent architecture allows for parallel development and efficient execution across hundreds of strategy configurations.

**Key Advantages:**
- ✅ Modular, maintainable codebase
- ✅ Scalable to cloud infrastructure
- ✅ Version-controlled with full audit trail
- ✅ Robust validation methodology
- ✅ Production-ready deliverables

**Next Steps:**
1. Review and approve this blueprint
2. Setup GitHub repository
3. Deploy database infrastructure
4. Begin Agent 1 development (data & candles)
5. Proceed through phases 1-6

Ready to begin implementation?