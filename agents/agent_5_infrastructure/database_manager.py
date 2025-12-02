"""
Database Manager for Mean Reversion Framework
Supports connection to AWS RDS PostgreSQL via MCP (Model Context Protocol)
"""

import os
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date
import pandas as pd
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection options
try:
    import psycopg2
    from psycopg2.extras import execute_values, RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    logging.warning("psycopg2 not installed - database features will be limited")


class DatabaseManager:
    """
    Database manager for the mean reversion framework.
    Connects to AWS RDS PostgreSQL instance.

    Supports connection via:
    1. Direct PostgreSQL connection (psycopg2)
    2. MCP (Model Context Protocol) - for AI agent access
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        min_connections: int = 1,
        max_connections: int = 10,
        use_mcp: bool = False
    ):
        """
        Initialize database connection.

        Args:
            host: Database host (default: from env DB_HOST)
            port: Database port (default: from env DB_PORT)
            database: Database name (default: from env DB_NAME)
            user: Database user (default: from env DB_USER)
            password: Database password (default: from env DB_PASSWORD)
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            use_mcp: Use MCP for database access (for AI agents)
        """
        # Load from environment if not provided
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.port = port or int(os.getenv('DB_PORT', 5432))
        self.database = database or os.getenv('DB_NAME', 'mean_reversion')
        self.user = user or os.getenv('DB_USER', 'trader')
        self.password = password or os.getenv('DB_PASSWORD', '')

        self.use_mcp = use_mcp
        self.logger = logging.getLogger(__name__)

        # Connection pool (for direct connections)
        self.pool = None

        if not use_mcp:
            self._init_connection_pool(min_connections, max_connections)

    def _init_connection_pool(self, min_conn: int, max_conn: int):
        """Initialize PostgreSQL connection pool"""
        if not HAS_PSYCOPG2:
            raise ImportError("psycopg2 is required for direct database connections")

        try:
            self.pool = SimpleConnectionPool(
                min_conn,
                max_conn,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.logger.info(f"Connected to PostgreSQL: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            self.logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        if self.use_mcp:
            # MCP connection logic here
            # Will be implemented when MCP is configured
            raise NotImplementedError("MCP connection not yet configured")

        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        """Context manager for database cursors"""
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            Query results if fetch=True, None otherwise
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            return None

    def execute_many(self, query: str, data: List[Tuple]) -> int:
        """
        Execute query with multiple parameter sets.

        Args:
            query: SQL query string
            data: List of parameter tuples

        Returns:
            Number of rows affected
        """
        with self.get_cursor() as cursor:
            execute_values(cursor, query, data)
            return cursor.rowcount

    # ========================================================================
    # STOCK DATA OPERATIONS
    # ========================================================================

    def load_stock_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Load stock data for a symbol.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            DataFrame with OHLCV data
        """
        query = """
            SELECT date, open, high, low, close, volume, adjusted_close
            FROM stock_data
            WHERE symbol = %s
        """
        params = [symbol]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date ASC"

        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()

        if not data:
            self.logger.warning(f"No data found for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        return df

    def save_stock_data(self, df: pd.DataFrame, symbol: str) -> int:
        """
        Save stock data to database.

        Args:
            df: DataFrame with columns: date, open, high, low, close, volume
            symbol: Stock ticker symbol

        Returns:
            Number of rows inserted
        """
        # Prepare data for insertion
        df = df.copy()
        if 'date' not in df.columns:
            df['date'] = df.index

        df['symbol'] = symbol

        # Convert to list of tuples
        columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        if 'adjusted_close' in df.columns:
            columns.append('adjusted_close')

        data = [tuple(row) for row in df[columns].values]

        # Build insert query
        placeholders = ','.join(['%s'] * len(columns))
        query = f"""
            INSERT INTO stock_data ({','.join(columns)})
            VALUES %s
            ON CONFLICT (symbol, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """

        if 'adjusted_close' in columns:
            query += ", adjusted_close = EXCLUDED.adjusted_close"

        return self.execute_many(query, data)

    def get_available_symbols(self) -> List[str]:
        """Get list of all symbols in database"""
        query = "SELECT DISTINCT symbol FROM stock_data ORDER BY symbol"
        results = self.execute_query(query)
        return [row[0] for row in results]

    # ========================================================================
    # CANDLE OPERATIONS
    # ========================================================================

    def load_candles(
        self,
        symbol: str,
        candle_type: str,
        aggregation_days: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Load generated candles.

        Args:
            symbol: Stock ticker symbol
            candle_type: 'regular', 'heiken_ashi', or 'linear_regression'
            aggregation_days: 1, 2, 3, 4, or 5
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            DataFrame with candle data
        """
        query = """
            SELECT date, open, high, low, close, volume
            FROM candles
            WHERE symbol = %s AND candle_type = %s AND aggregation_days = %s
        """
        params = [symbol, candle_type, aggregation_days]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date ASC"

        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        return df

    def save_candles(
        self,
        df: pd.DataFrame,
        symbol: str,
        candle_type: str,
        aggregation_days: int
    ) -> int:
        """
        Save generated candles to database.

        Args:
            df: DataFrame with columns: date, open, high, low, close, volume
            symbol: Stock ticker symbol
            candle_type: 'regular', 'heiken_ashi', or 'linear_regression'
            aggregation_days: 1, 2, 3, 4, or 5

        Returns:
            Number of rows inserted
        """
        df = df.copy()
        if 'date' not in df.columns:
            df['date'] = df.index

        df['symbol'] = symbol
        df['candle_type'] = candle_type
        df['aggregation_days'] = aggregation_days

        columns = ['symbol', 'date', 'candle_type', 'aggregation_days',
                   'open', 'high', 'low', 'close', 'volume']

        data = [tuple(row) for row in df[columns].values]

        query = """
            INSERT INTO candles (symbol, date, candle_type, aggregation_days,
                                 open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (symbol, date, candle_type, aggregation_days) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """

        return self.execute_many(query, data)

    # ========================================================================
    # STRATEGY CONFIGURATION OPERATIONS
    # ========================================================================

    def save_strategy_config(self, config: Dict[str, Any]) -> int:
        """
        Save strategy configuration.

        Args:
            config: Strategy configuration dictionary

        Returns:
            Configuration ID
        """
        query = """
            INSERT INTO strategy_configs (
                config_name, phase, candle_type, aggregation_days,
                mean_type, mean_lookback, stddev_lookback, entry_threshold,
                exit_type, position_sizing, position_size, parameters
            ) VALUES (
                %(config_name)s, %(phase)s, %(candle_type)s, %(aggregation_days)s,
                %(mean_type)s, %(mean_lookback)s, %(stddev_lookback)s, %(entry_threshold)s,
                %(exit_type)s, %(position_sizing)s, %(position_size)s, %(parameters)s
            )
            RETURNING id
        """

        # Store full config as JSON
        config['parameters'] = json.dumps(config)

        with self.get_cursor() as cursor:
            cursor.execute(query, config)
            return cursor.fetchone()[0]

    def get_strategy_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get strategy configuration by ID"""
        query = "SELECT * FROM strategy_configs WHERE id = %s"
        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(query, (config_id,))
            return cursor.fetchone()

    def get_top_configs(
        self,
        phase: int,
        n: int = 10,
        metric: str = 'sharpe_ratio'
    ) -> List[Dict[str, Any]]:
        """
        Get top N configurations for a phase.

        Args:
            phase: Phase number
            n: Number of configs to return
            metric: Metric to sort by (sharpe_ratio, total_return, calmar_ratio)

        Returns:
            List of configuration dictionaries
        """
        query = f"""
            SELECT * FROM get_top_configs(%s, %s, %s)
        """

        with self.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(query, (phase, n, metric))
            return cursor.fetchall()

    # ========================================================================
    # BACKTEST RESULTS OPERATIONS
    # ========================================================================

    def save_backtest_results(
        self,
        config_id: int,
        symbol: str,
        results: Dict[str, Any]
    ) -> int:
        """
        Save backtest results.

        Args:
            config_id: Strategy configuration ID
            symbol: Stock symbol or 'PORTFOLIO'
            results: Results dictionary with metrics

        Returns:
            Result ID
        """
        query = """
            INSERT INTO backtest_results (
                config_id, symbol, initial_capital, final_value, total_return,
                sharpe_ratio, sortino_ratio, calmar_ratio, max_drawdown,
                total_trades, winning_trades, losing_trades, win_rate,
                profit_factor, avg_win, avg_loss, avg_trade,
                equity_curve, trade_log, monthly_returns
            ) VALUES (
                %(config_id)s, %(symbol)s, %(initial_capital)s, %(final_value)s,
                %(total_return)s, %(sharpe_ratio)s, %(sortino_ratio)s,
                %(calmar_ratio)s, %(max_drawdown)s, %(total_trades)s,
                %(winning_trades)s, %(losing_trades)s, %(win_rate)s,
                %(profit_factor)s, %(avg_win)s, %(avg_loss)s, %(avg_trade)s,
                %(equity_curve)s, %(trade_log)s, %(monthly_returns)s
            )
            RETURNING id
        """

        # Convert complex data to JSON
        results['config_id'] = config_id
        results['symbol'] = symbol
        results['equity_curve'] = json.dumps(results.get('equity_curve', []))
        results['trade_log'] = json.dumps(results.get('trade_log', []))
        results['monthly_returns'] = json.dumps(results.get('monthly_returns', {}))

        with self.get_cursor() as cursor:
            cursor.execute(query, results)
            return cursor.fetchone()[0]

    # ========================================================================
    # LOGGING
    # ========================================================================

    def log_agent_activity(
        self,
        agent_name: str,
        phase: int,
        level: str,
        message: str,
        context: Optional[Dict] = None
    ):
        """Log agent activity to database"""
        query = """
            INSERT INTO agent_logs (agent_name, phase, log_level, message, context)
            VALUES (%s, %s, %s, %s, %s)
        """

        context_json = json.dumps(context) if context else None
        self.execute_query(query, (agent_name, phase, level, message, context_json), fetch=False)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def close(self):
        """Close all database connections"""
        if self.pool:
            self.pool.closeall()
            self.logger.info("Database connections closed")


# Convenience function to get database instance
def get_db() -> DatabaseManager:
    """Get database manager instance with environment configuration"""
    return DatabaseManager()
