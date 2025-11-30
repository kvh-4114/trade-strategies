#!/usr/bin/env python3
"""
Test database connection to RDS
Run this after setting up RDS to verify connectivity
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database_manager import DatabaseManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection():
    """Test database connection and display information"""

    print("=" * 80)
    print("RDS CONNECTION TEST")
    print("=" * 80)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Display connection info (without password)
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    database = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')

    print(f"\nConnection Details:")
    print(f"  Host:     {host}")
    print(f"  Port:     {port}")
    print(f"  Database: {database}")
    print(f"  User:     {user}")
    print(f"  SSL Mode: {os.getenv('DB_SSL_MODE', 'require')}")

    # Test connection
    print("\n" + "-" * 80)
    print("Testing connection...")
    print("-" * 80)

    try:
        # Initialize database manager
        use_secrets = os.getenv('USE_SECRETS_MANAGER', '').lower() == 'true'

        if use_secrets:
            print("\nUsing AWS Secrets Manager for credentials...")
            db = DatabaseManager(use_secrets_manager=True)
        else:
            print("\nUsing environment variables for credentials...")
            db = DatabaseManager()

        # Test connection
        if not db.test_connection():
            print("\n✗ CONNECTION FAILED")
            return False

        print("\n" + "-" * 80)
        print("Database Information:")
        print("-" * 80)

        # Get database stats
        with db.get_cursor() as cursor:
            # Database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """)
            db_size = cursor.fetchone()['size']
            print(f"  Database Size: {db_size}")

            # Number of connections
            cursor.execute("""
                SELECT count(*) as connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            connections = cursor.fetchone()['connections']
            print(f"  Active Connections: {connections}")

            # PostgreSQL settings
            cursor.execute("""
                SELECT
                    name,
                    setting,
                    unit
                FROM pg_settings
                WHERE name IN ('max_connections', 'shared_buffers', 'work_mem', 'effective_cache_size')
                ORDER BY name
            """)
            print(f"\n  PostgreSQL Configuration:")
            for row in cursor.fetchall():
                unit = row['unit'] or ''
                print(f"    {row['name']}: {row['setting']} {unit}")

        # List tables
        print("\n" + "-" * 80)
        print("Tables:")
        print("-" * 80)

        tables = db.list_tables()
        if tables:
            total_rows = 0
            for table in tables:
                count = db.count_rows(table)
                total_rows += count
                print(f"  ✓ {table:30} {count:>10,} rows")
            print(f"\n  Total: {len(tables)} tables, {total_rows:,} rows")
        else:
            print("  No tables found (database not initialized yet)")
            print("\n  Run: python scripts/initialize_database.py")

        # Test a simple query
        print("\n" + "-" * 80)
        print("Testing Query Execution:")
        print("-" * 80)

        result = db.execute_query("""
            SELECT
                current_timestamp as time,
                inet_client_addr() as client_ip,
                inet_server_addr() as server_ip,
                version() as pg_version
        """, fetch_one=True)

        if result:
            print(f"  Current Time: {result['time']}")
            print(f"  Client IP: {result['client_ip'] or 'localhost'}")
            print(f"  Server IP: {result['server_ip'] or 'localhost'}")

        # Close pool
        db.close_pool()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED - Database is ready!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    success = test_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
