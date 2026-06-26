"""
Execute chatbot database migration
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.chatbot_connection import get_chatbot_engine
from sqlalchemy import text


def run_migration():
    """Execute the migration SQL script"""
    engine = get_chatbot_engine()
    
    # Read the migration SQL file
    migration_path = Path(__file__).parent / "migrate_chatbot_schema.sql"
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    # Execute the migration as a single script
    with engine.connect() as conn:
        try:
            conn.execute(text(migration_sql))
            conn.commit()
            print("Migration executed successfully")
        except Exception as e:
            print(f"Error executing migration: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    run_migration()
