# CLAUDE.md - AI Assistant Guide for Mean Reversion Strategy Framework

## Project Overview

This is a **multi-agent system for testing and optimizing mean reversion trading strategies**. The framework systematically tests strategy configurations across 250+ stocks using a 6-phase pipeline approach.

### Core Concept
Mean reversion strategy: Buy when price falls below lower band (mean - N×stddev), sell when price returns to the mean or target level.

## Quick Reference

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure database credentials
docker-compose up -d  # Start PostgreSQL (or use RDS)

# Run pipeline
python orchestrator/main_orchestrator.py --phase 1
python orchestrator/main_orchestrator.py --phases all

# Generate candles for a symbol
python agents/agent_1_data_candles/candle_generator.py --symbol AAPL

# Run tests
pytest tests/unit/
pytest tests/integration/
pytest --cov=. --cov-report=html
```

## Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│              Coordinates workflow execution                      │
└─────────────────────────────────────────────────────────────────┘
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Agent 1   │ │   Agent 2   │ │   Agent 3   │ │   Agent 4   │ │   Agent 5   │
│ Data/Candles│ │Strategy Core│ │Optimization │ │  Analysis   │ │Infrastructure│
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Agent Responsibilities

| Agent | Location | Purpose |
|-------|----------|---------|
| **Agent 1** | `agents/agent_1_data_candles/` | Generates Regular, Heiken Ashi, Linear Regression candles (13 combinations) |
| **Agent 2** | `agents/agent_2_strategy_core/` | Implements mean reversion strategy logic using Backtrader |
| **Agent 3** | `agents/agent_3_optimization/` | Runs parallel backtests and walk-forward validation |
| **Agent 4** | `agents/agent_4_analysis/` | Calculates metrics, generates reports |
| **Agent 5** | `agents/agent_5_infrastructure/` | Database management, data loading, deployment |

## Directory Structure

```
trade-strategies/
├── orchestrator/              # Main orchestration logic
│   └── __init__.py
├── agents/
│   ├── agent_1_data_candles/  # Candle generation
│   │   ├── candle_generator.py    # Main generator class
│   │   ├── regular_candles.py     # Standard OHLC aggregation
│   │   ├── heiken_ashi.py         # Heiken Ashi candles
│   │   └── linear_regression.py   # Linear regression candles
│   ├── agent_2_strategy_core/ # Strategy implementation
│   │   ├── base_strategy.py       # MeanReversionStrategy (Backtrader)
│   │   ├── mean_calculators.py    # SMA, EMA, LinReg, VWAP indicators
│   │   ├── stddev_bands.py        # Standard deviation bands
│   │   ├── entry_logic.py         # Entry conditions
│   │   └── exit_logic.py          # Exit conditions
│   ├── agent_3_optimization/  # Backtesting & optimization
│   ├── agent_4_analysis/      # Metrics & reporting
│   │   └── metrics_calculator.py
│   └── agent_5_infrastructure/ # Database & deployment
│       ├── database_manager.py    # PostgreSQL connection pool
│       └── data_loader.py         # Stock data loading
├── configs/                   # Phase configuration YAML files
│   ├── phase_1_config.yaml    # Candle type baseline (13 configs)
│   ├── phase_2_config.yaml    # Mean & StdDev optimization (400+ configs)
│   ├── phase_3_config.yaml    # Entry/Exit refinement
│   ├── phase_4_config.yaml    # Filter integration
│   ├── phase_5_config.yaml    # Risk management
│   └── phase_6_config.yaml    # Final validation
├── data/
│   ├── raw/                   # Raw stock CSV files (gitignored)
│   ├── processed/             # Generated candles (gitignored)
│   └── results/               # Backtest results (gitignored)
├── database/
│   ├── init.sql               # Database schema
│   └── migrations/            # Schema migrations
├── scripts/
│   └── load_stock_data.py     # Data loading utility
├── tests/
│   ├── unit/
│   └── integration/
├── mean_reversion/            # Strategy documentation
│   └── Mean Reversion Strategy Testing Framework.md
├── docker-compose.yml         # PostgreSQL + App containers
├── Dockerfile                 # Python 3.10 application image
├── requirements.txt           # Python dependencies
└── .env.example               # Environment variable template
```

## Database Schema

**PostgreSQL 17** (AWS RDS or Docker)

| Table | Purpose |
|-------|---------|
| `stock_data` | Raw OHLCV data (symbol, date, open, high, low, close, volume, adjusted_close) |
| `candles` | Generated candles with type and aggregation (13 types per symbol) |
| `strategy_configs` | Strategy parameters (candle_type, mean_type, lookbacks, thresholds, JSONB params) |
| `backtest_results` | Performance metrics (return, sharpe, max_drawdown, win_rate, etc.) |
| `walk_forward_results` | Walk-forward validation results |
| `monte_carlo_results` | Monte Carlo simulation results |
| `phase_execution` | Phase tracking (status, timestamps) |
| `agent_logs` | Agent execution logs |

### Key Relationships
- `backtest_results.config_id` → `strategy_configs.id`
- `walk_forward_results.config_id` → `strategy_configs.id`
- `monte_carlo_results.config_id` → `strategy_configs.id`

## 6-Phase Testing Pipeline

| Phase | Name | Configurations | Purpose |
|-------|------|----------------|---------|
| 1 | Candle Type Baseline | 13 | Test all candle combinations with fixed params |
| 2 | Mean & StdDev Optimization | 400+ | Grid search mean types & lookback periods |
| 3 | Entry/Exit Refinement | Variable | Optimize entry/exit logic |
| 4 | Filter Integration | Variable | Add volume, RSI, trend, volatility filters |
| 5 | Risk Management | Variable | Position sizing, stop losses |
| 6 | Final Validation | Top N | Walk-forward, Monte Carlo, stress testing |

## Key Classes and Patterns

### MeanReversionStrategy (Backtrader)
Location: `agents/agent_2_strategy_core/base_strategy.py`

```python
class MeanReversionStrategy(bt.Strategy):
    params = (
        ('candle_type', 'regular'),
        ('aggregation_days', 1),
        ('mean_type', 'SMA'),           # SMA, EMA, LinReg, VWAP
        ('mean_lookback', 20),
        ('stddev_lookback', 20),
        ('entry_threshold', 2.0),       # N standard deviations
        ('exit_type', 'mean'),          # mean, opposite_band, profit_target, time_based
        ('use_volume_filter', False),
        ('use_rsi_filter', False),
        ('position_sizing', 'fixed'),   # fixed, volatility_adjusted, kelly
        ('stop_loss_type', 'none'),     # none, fixed_pct, atr, trailing
        # ... more params
    )
```

### DatabaseManager
Location: `agents/agent_5_infrastructure/database_manager.py`

```python
db = DatabaseManager()  # Uses env vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Load stock data
df = db.load_stock_data('AAPL', start_date=date(2020,1,1))

# Save candles
db.save_candles(df, symbol='AAPL', candle_type='heiken_ashi', aggregation_days=2)

# Get top performing configs
top_configs = db.get_top_configs(phase=1, n=10, metric='sharpe_ratio')

# Log agent activity
db.log_agent_activity('candle_generator', phase=1, level='INFO', message='Done')
```

### CandleGenerator
Location: `agents/agent_1_data_candles/candle_generator.py`

```python
generator = CandleGenerator()

# Generate all 13 candle types for a symbol
results = generator.generate_all_candles('AAPL', save_to_db=True)

# Process all symbols
generator.generate_for_all_symbols(limit=10)  # limit for testing

# Get summary
summary = generator.get_candle_summary()
```

## Configuration

### Environment Variables (.env)
```bash
DB_HOST=mean-reversion-db.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=mean_reversion
DB_USER=trader
DB_PASSWORD=your_password

N_JOBS=-1                    # Parallel processing (-1 = all cores)
INITIAL_CAPITAL=100000
COMMISSION=0.001             # 0.1%
DATA_START_DATE=2010-01-01
DATA_END_DATE=2023-12-31
```

### Phase Config Structure (YAML)
```yaml
phase: 1
name: "Candle Type Baseline"

candle_types:
  - type: "regular"
    aggregations: [1, 2, 3, 4, 5]
  - type: "heiken_ashi"
    aggregations: [1, 2, 3, 4, 5]
  - type: "linear_regression"
    aggregations: [1, 2, 3]

fixed_parameters:
  mean_type: "SMA"
  mean_lookback: 20
  entry_threshold: 2.0
  exit_type: "mean"

execution:
  parallel: true
  n_jobs: 8
  start_date: "2010-01-01"
  end_date: "2023-12-31"

success_criteria:
  min_trades: 100
  min_sharpe: 0.5
  max_drawdown: 0.50
  top_n: 5
```

## Code Conventions

### Python Style
- **Formatter**: black (line length 88)
- **Linter**: flake8
- **Type checking**: mypy
- Python 3.10+ required

### Docstrings
Use Google-style docstrings:
```python
def function(arg1: str, arg2: int = 10) -> pd.DataFrame:
    """
    Short description.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When something is wrong
    """
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing {symbol}")
logger.error(f"Failed: {e}")
```

### Database Operations
- Always use context managers for connections
- Use parameterized queries (never string formatting for SQL)
- Handle `ON CONFLICT` for upserts

## AWS Infrastructure

### RDS PostgreSQL
- Instance: `mean-reversion-db.csta6s844r6m.us-east-1.rds.amazonaws.com`
- Port: 5432
- Database: mean_reversion
- Publicly accessible: Yes

### S3 Bucket
- Name: `kvh-trade-strategies-stock-data`
- Contains: Database dumps, stock data

### Restore Database from S3
```bash
# Download dump
curl -o mean_reversion.dump.gz "https://kvh-trade-strategies-stock-data.s3.us-east-1.amazonaws.com/mean_reversion.dump.gz"

# Restore to PostgreSQL
gunzip -c mean_reversion.dump.gz | pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME
```

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires database)
pytest tests/integration/ -v

# With coverage
pytest --cov=agents --cov-report=html

# Specific test file
pytest tests/unit/test_candle_generator.py -v
```

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run pipeline in container
docker-compose exec app python orchestrator/main_orchestrator.py --phase 1

# Stop services
docker-compose down
```

## Common Tasks for AI Assistants

### Adding a New Candle Type
1. Create new file in `agents/agent_1_data_candles/`
2. Implement `generate_<type>_candles(df, aggregation_days)` function
3. Update `CandleGenerator.CANDLE_TYPES` and `AGGREGATION_PERIODS`
4. Add to phase configs if needed

### Adding a New Filter
1. Add parameter to `MeanReversionStrategy.params`
2. Initialize indicator in `__init__` if `use_<filter>_filter`
3. Add check in `_check_filters()` method
4. Update phase 4 config

### Adding a New Exit Type
1. Add case in `_check_exit_conditions()` method
2. Update `exit_type` param options in docstring
3. Add to phase 3 config options

### Debugging Backtest Issues
1. Enable logging: `log_trades=True` in strategy params
2. Check `agent_logs` table for errors
3. Verify candle data exists: `SELECT * FROM candles WHERE symbol='AAPL' LIMIT 5`
4. Check strategy config: `SELECT * FROM strategy_configs WHERE id=<config_id>`

## Development Status

- [x] Project structure setup
- [x] Database schema (Agent 5)
- [x] Candle generation (Agent 1)
- [x] Strategy core implementation (Agent 2)
- [ ] Optimization engine (Agent 3)
- [ ] Analysis and reporting (Agent 4)
- [ ] Orchestrator integration
- [ ] Phase 1-6 execution

## Important Notes

1. **Data files are gitignored** - raw CSVs, processed candles, and results are not committed
2. **Never commit .env** - contains database credentials
3. **RDS access** - requires VPC/security group configuration for external access
4. **Large dataset** - 250 stocks × 13 candle types = 3,250 candle sets per run
5. **Parallel processing** - use `N_JOBS=-1` for all cores, or limit for memory constraints
