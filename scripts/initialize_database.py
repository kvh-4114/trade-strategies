#!/usr/bin/env python3
"""
Initialize the database schema
Runs the database/init.sql script to create tables, indexes, views, and functions
"""

import sys
import os
import subprocess
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database_manager import DatabaseManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database schema"""

    print("=" * 80)
    print("DATABASE SCHEMA INITIALIZATION")
    print("=" * 80)

    # Load environment variables
    load_dotenv()

    # Get connection details
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    if not all([host, database, user, password]):
        print("\n✗ Missing database connection details in .env file")
        print("  Required: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        return False

    # Locate init.sql file
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    init_sql = os.path.join(script_dir, 'database', 'init.sql')

    if not os.path.exists(init_sql):
        print(f"\n✗ init.sql not found at: {init_sql}")
        return False

    print(f"\nDatabase: {host}:{port}/{database}")
    print(f"User: {user}")
    print(f"Schema file: {init_sql}")

    # Test connection first
    print("\n" + "-" * 80)
    print("Testing connection...")
    print("-" * 80)

    try:
        db = DatabaseManager()
        if not db.test_connection():
            print("\n✗ Cannot connect to database")
            return False
        db.close_pool()
        print("✓ Connection successful")
    except Exception as e:
        print(f"\n✗ Connection error: {e}")
        return False

    # Run init.sql using psql
    print("\n" + "-" * 80)
    print("Initializing database schema...")
    print("-" * 80)

    try:
        # Set password in environment for psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password

        # Run psql command
        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-f', init_sql,
            '--echo-errors',
            '--quiet'
        ]

        print(f"\nRunning: psql -h {host} -p {port} -U {user} -d {database} -f {init_sql}")

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("\n✓ Schema initialized successfully!")

            # Show output if any
            if result.stdout.strip():
                print("\nOutput:")
                print(result.stdout)

        else:
            print(f"\n✗ Schema initialization failed (exit code {result.returncode})")
            if result.stderr:
                print("\nError output:")
                print(result.stderr)
            return False

    except FileNotFoundError:
        print("\n✗ 'psql' command not found")
        print("  Install PostgreSQL client:")
        print("    macOS: brew install postgresql@15")
        print("    Ubuntu: sudo apt-get install postgresql-client-15")
        print("    Amazon Linux: sudo yum install postgresql")
        return False
    except Exception as e:
        print(f"\n✗ Error running init.sql: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify schema
    print("\n" + "-" * 80)
    print("Verifying schema...")
    print("-" * 80)

    try:
        db = DatabaseManager()

        # List tables
        tables = db.list_tables()
        print(f"\n✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        # Check views
        views = db.execute_query("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        if views:
            print(f"\n✓ Created {len(views)} views:")
            for view in views:
                print(f"  - {view['table_name']}")

        # Check functions
        functions = db.execute_query("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """)
        if functions:
            print(f"\n✓ Created {len(functions)} functions:")
            for func in functions:
                print(f"  - {func['routine_name']}")

        # Check indexes
        indexes = db.execute_query("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname
        """)
        if indexes:
            print(f"\n✓ Created {len(indexes)} indexes:")
            for idx in indexes:
                print(f"  - {idx['indexname']}")

        db.close_pool()

        print("\n" + "=" * 80)
        print("✓ DATABASE INITIALIZED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Load stock data: python scripts/load_stock_data.py")
        print("  2. Generate candles: python agents/agent_1_data_candles/candle_generator.py")
        print("  3. Run backtests: python orchestrator/main_orchestrator.py --phase 1")
        print()

        return True

    except Exception as e:
        print(f"\n✗ Error verifying schema: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    success = initialize_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
