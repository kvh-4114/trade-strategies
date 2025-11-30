"""
Database Manager for Mean Reversion Trading Framework
Handles all database connections and operations with RDS PostgreSQL
"""

import os
import sys
import psycopg2
import boto3
import json
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor, execute_batch
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations
    Supports both direct password auth and AWS Secrets Manager
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_secrets_manager: bool = False,
        secret_name: Optional[str] = None,
        min_connections: int = 1,
        max_connections: int = 10,
        ssl_mode: str = 'require'
    ):
        """
        Initialize database manager

        Args:
            host: Database host (or load from env)
            port: Database port (or load from env)
            database: Database name (or load from env)
            user: Database user (or load from env)
            password: Database password (or load from env/secrets)
            use_secrets_manager: Whether to retrieve password from AWS Secrets Manager
            secret_name: Name of secret in Secrets Manager
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            ssl_mode: SSL mode (require, verify-full, disable)
        """
        # Load environment variables
        load_dotenv()

        # Get connection parameters
        self.host = host or os.getenv('DB_HOST')
        self.port = port or int(os.getenv('DB_PORT', 5432))
        self.database = database or os.getenv('DB_NAME')
        self.user = user or os.getenv('DB_USER')
        self.ssl_mode = ssl_mode or os.getenv('DB_SSL_MODE', 'require')

        # Get password
        if use_secrets_manager or os.getenv('USE_SECRETS_MANAGER', '').lower() == 'true':
            secret_name = secret_name or os.getenv('DB_SECRET_NAME')
            if not secret_name:
                raise ValueError("Secret name required when using Secrets Manager")
            credentials = self._get_credentials_from_secrets_manager(secret_name)
            self.password = credentials['password']
            # Override other params if provided in secret
            self.host = credentials.get('host', self.host)
            self.port = credentials.get('port', self.port)
            self.database = credentials.get('dbname', self.database)
            self.user = credentials.get('username', self.user)
        else:
            self.password = password or os.getenv('DB_PASSWORD')

        # Validate required parameters
        if not all([self.host, self.port, self.database, self.user, self.password]):
            raise ValueError(
                "Missing required database connection parameters. "
                "Provide via arguments or environment variables."
            )

        # Connection pool
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool: Optional[ThreadedConnectionPool] = None

        logger.info(f"Database manager initialized for {self.host}:{self.port}/{self.database}")

    def _get_credentials_from_secrets_manager(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve database credentials from AWS Secrets Manager

        Args:
            secret_name: Name of the secret

        Returns:
            Dictionary containing credentials
        """
        try:
            region = os.getenv('AWS_REGION', 'us-east-1')
            client = boto3.client('secretsmanager', region_name=region)

            logger.info(f"Retrieving credentials from Secrets Manager: {secret_name}")
            response = client.get_secret_value(SecretId=secret_name)

            if 'SecretString' in response:
                credentials = json.loads(response['SecretString'])
                logger.info("Successfully retrieved credentials from Secrets Manager")
                return credentials
            else:
                raise ValueError("Secret does not contain SecretString")

        except Exception as e:
            logger.error(f"Error retrieving credentials from Secrets Manager: {e}")
            raise

    def create_pool(self):
        """Create connection pool"""
        if self.pool:
            logger.warning("Connection pool already exists")
            return

        try:
            logger.info(f"Creating connection pool ({self.min_connections}-{self.max_connections} connections)")
            self.pool = ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode=self.ssl_mode
            )
            logger.info("Connection pool created successfully")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager)

        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        if not self.pool:
            self.create_pool()

        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """
        Get a cursor from a pooled connection (context manager)

        Args:
            cursor_factory: Cursor factory (RealDictCursor for dict results)

        Usage:
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True,
        fetch_one: bool = False
    ) -> Optional[List[Dict]]:
        """
        Execute a query and return results

        Args:
            query: SQL query
            params: Query parameters (for parameterized queries)
            fetch: Whether to fetch results
            fetch_one: Fetch only one row

        Returns:
            Query results as list of dictionaries (or None for non-SELECT queries)
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)

            if fetch:
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
            return None

    def execute_many(self, query: str, data: List[tuple], batch_size: int = 1000):
        """
        Execute a query multiple times with different parameters (batch insert)

        Args:
            query: SQL query with placeholders
            data: List of tuples containing parameters
            batch_size: Number of rows per batch
        """
        with self.get_cursor() as cursor:
            execute_batch(cursor, query, data, page_size=batch_size)
            logger.info(f"Inserted {len(data)} rows in batches of {batch_size}")

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("Testing database connection...")
            result = self.execute_query("SELECT version(), current_database(), current_user")
            if result:
                version = result[0]['version']
                database = result[0]['current_database']
                user = result[0]['current_user']
                logger.info(f"✓ Connected to PostgreSQL: {database} as {user}")
                logger.info(f"  Version: {version[:50]}...")
                return True
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict]:
        """
        Get information about a table

        Args:
            table_name: Name of the table

        Returns:
            List of column information
        """
        query = """
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        return self.execute_query(query, (table_name,))

    def list_tables(self) -> List[str]:
        """
        List all tables in the database

        Returns:
            List of table names
        """
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        results = self.execute_query(query)
        return [row['table_name'] for row in results]

    def count_rows(self, table_name: str) -> int:
        """
        Count rows in a table

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        # Use safe identifier quoting
        query = f'SELECT COUNT(*) as count FROM "{table_name}"'
        result = self.execute_query(query, fetch_one=True)
        return result['count'] if result else 0

    def close_pool(self):
        """Close all connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Connection pool closed")
            self.pool = None


# Convenience function for quick queries
def quick_query(query: str, params: Optional[tuple] = None) -> Optional[List[Dict]]:
    """
    Execute a quick query without managing connection pool

    Args:
        query: SQL query
        params: Query parameters

    Returns:
        Query results
    """
    db = DatabaseManager()
    try:
        return db.execute_query(query, params)
    finally:
        db.close_pool()


if __name__ == "__main__":
    # Test the database manager
    print("=" * 80)
    print("Database Manager Test")
    print("=" * 80)

    # Initialize manager
    db = DatabaseManager()

    # Test connection
    if db.test_connection():
        print("\n✓ Connection successful!")

        # List tables
        print("\nTables in database:")
        tables = db.list_tables()
        for table in tables:
            count = db.count_rows(table)
            print(f"  - {table}: {count:,} rows")

        print("\n✓ Database manager working correctly!")
    else:
        print("\n✗ Connection failed!")
        sys.exit(1)

    # Close pool
    db.close_pool()
    print("\n" + "=" * 80)
