"""
Verify chatbot database schema
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.chatbot_connection import get_chatbot_engine
from sqlalchemy import text


def verify_schema():
    """Verify the database schema"""
    engine = get_chatbot_engine()
    
    with engine.connect() as conn:
        # Check tables exist
        print("=== Checking Tables ===")
        tables = ['conversations', 'messages', 'user_preferences', 'search_history', 'session_analytics']
        
        for table in tables:
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """))
            exists = result.scalar()
            status = "✓" if exists else "✗"
            print(f"{status} Table '{table}': {'EXISTS' if exists else 'MISSING'}")
        
        # Check foreign key
        print("\n=== Checking Foreign Keys ===")
        fk_result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'messages'
                AND tc.constraint_type = 'FOREIGN KEY'
                AND tc.constraint_name = 'fk_messages_conversation'
            )
        """))
        fk_exists = fk_result.scalar()
        status = "✓" if fk_exists else "✗"
        print(f"{status} Foreign key 'fk_messages_conversation': {'EXISTS' if fk_exists else 'MISSING'}")
        
        # Check indexes
        print("\n=== Checking Indexes ===")
        indexes = [
            'idx_conversations_session_id',
            'idx_conversations_user_id',
            'idx_conversations_last_activity',
            'idx_messages_conversation_id',
            'idx_messages_created_at',
            'idx_messages_role',
            'idx_user_preferences_user_id',
            'idx_search_history_session_id',
            'idx_search_history_user_id',
            'idx_search_history_created_at',
            'idx_session_analytics_session_id',
            'idx_session_analytics_user_id'
        ]
        
        for index in indexes:
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = '{index}'
                )
            """))
            exists = result.scalar()
            status = "✓" if exists else "✗"
            print(f"{status} Index '{index}': {'EXISTS' if exists else 'MISSING'}")
        
        # Check trigger
        print("\n=== Checking Triggers ===")
        trigger_result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_name = 'trigger_update_user_preferences_timestamp'
            )
        """))
        trigger_exists = trigger_result.scalar()
        status = "✓" if trigger_exists else "✗"
        print(f"{status} Trigger 'trigger_update_user_preferences_timestamp': {'EXISTS' if trigger_exists else 'MISSING'}")
        
        # Check function
        print("\n=== Checking Functions ===")
        func_result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = 'update_timestamp'
            )
        """))
        func_exists = func_result.scalar()
        status = "✓" if func_exists else "✗"
        print(f"{status} Function 'update_timestamp': {'EXISTS' if func_exists else 'MISSING'}")


if __name__ == "__main__":
    verify_schema()
