# Mean Reversion Strategy Testing Framework

A multi-agent system for systematically testing and optimizing mean reversion trading strategies across multiple stocks and parameter combinations.

## Overview

This framework implements a comprehensive 6-phase testing pipeline:

1. **Phase 1:** Candle Type Baseline (13 configurations)
2. **Phase 2:** Mean & StdDev Optimization (400+ configurations)
3. **Phase 3:** Entry/Exit Logic Refinement
4. **Phase 4:** Filter Integration
5. **Phase 5:** Risk Management Optimization
6. **Phase 6:** Final Validation & Stress Testing

## Architecture

The system uses a multi-agent architecture with specialized agents:

- **Orchestrator:** Coordinates workflow execution
- **Agent 1 (Data & Candles):** Generates regular, Heiken Ashi, and Linear Regression candles
- **Agent 2 (Strategy Core):** Implements mean reversion strategy logic
- **Agent 3 (Optimization):** Runs parallel backtests and walk-forward validation
- **Agent 4 (Analysis):** Calculates metrics and generates reports
- **Agent 5 (Infrastructure):** Manages database and deployment

## Technology Stack

- **Python:** 3.10+
- **Backtesting:** Backtrader
- **Database:** PostgreSQL 15 (Dockerized)
- **Parallelization:** Joblib, Multiprocessing
- **Visualization:** Matplotlib, Plotly
- **Containerization:** Docker & Docker Compose

## Project Structure

```
trade-strategies/
├── orchestrator/          # Main orchestration logic
├── agents/                # Specialized agents
│   ├── agent_1_data_candles/
│   ├── agent_2_strategy_core/
│   ├── agent_3_optimization/
│   ├── agent_4_analysis/
│   └── agent_5_infrastructure/
├── database/              # Database schema and migrations
├── data/                  # Stock data and results
│   ├── raw/              # Raw stock data CSV files
│   ├── processed/        # Generated candles
│   └── results/          # Backtest results
├── configs/               # Phase configuration files
├── scripts/               # Utility scripts
└── tests/                 # Test suites
```

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd trade-strategies
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup environment variables:**
```bash
cp .env.example .env
# Edit .env with your database password and configuration
```

5. **Start Docker containers:**
```bash
docker-compose up -d
```

6. **Verify database connection:**
```bash
python scripts/verify_setup.py
```

## Loading Stock Data

Place your stock data CSV files in `data/raw/` with the following format:
```
symbol,date,open,high,low,close,volume
AAPL,2020-01-02,300.35,301.00,298.50,300.95,32850000
```

Load data into the database:
```bash
python agents/agent_5_infrastructure/data_loader.py --input data/raw/stock_data.csv --symbols-count 250
```

## Running the Pipeline

### Run all phases sequentially:
```bash
python orchestrator/main_orchestrator.py --phases all
```

### Run specific phase:
```bash
python orchestrator/main_orchestrator.py --phase 1
```

### Run multiple phases:
```bash
python orchestrator/main_orchestrator.py --phases 1,2,3
```

## Configuration

Phase configurations are stored in `configs/` directory:
- `phase_1_config.yaml` - Candle type baseline
- `phase_2_config.yaml` - Parameter optimization
- `phase_3_config.yaml` - Entry/Exit refinement
- `phase_4_config.yaml` - Filter integration
- `phase_5_config.yaml` - Risk management
- `phase_6_config.yaml` - Final validation

## Development Status

- [x] Project structure setup
- [ ] Database schema and infrastructure (Agent 5)
- [ ] Candle generation (Agent 1)
- [ ] Strategy core implementation (Agent 2)
- [ ] Optimization engine (Agent 3)
- [ ] Analysis and reporting (Agent 4)
- [ ] Orchestrator integration
- [ ] Phase 1 execution
- [ ] Phases 2-6 implementation

## Testing

Run unit tests:
```bash
pytest tests/unit/
```

Run integration tests:
```bash
pytest tests/integration/
```

Run all tests with coverage:
```bash
pytest --cov=. --cov-report=html
```

## Database Schema

The PostgreSQL database includes the following main tables:
- `stock_data` - Raw OHLCV data
- `candles` - Generated candles (13 types)
- `strategy_configs` - Strategy parameter configurations
- `backtest_results` - Performance metrics and results
- `walk_forward_results` - Walk-forward validation results
- `phase_execution` - Phase tracking
- `agent_logs` - Agent execution logs

## Output & Results

Results are stored in:
- **Database:** All backtest results and metrics
- **Files:** `data/results/` for CSV exports
- **Reports:** Phase reports in PDF/HTML format
- **Visualizations:** Equity curves, drawdown plots, heatmaps

## Docker Deployment

The project is fully Dockerized for portability:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose build --no-cache
```

## AWS Deployment

Deploy to AWS EC2:
```bash
./scripts/deploy_aws.sh --instance-type t3.2xlarge --region us-east-1
```

## Contributing

This is a research project. For questions or contributions, please open an issue.

## License

Proprietary - All Rights Reserved

## Documentation

For detailed architecture and implementation details, see:
- `mean_reversion/Mean Reversion Strategy Testing Framework.md` - Complete blueprint
- `docs/` - Additional documentation (coming soon)

## Contact

For questions or support, please refer to the project documentation.
