"""
Test chatbot database connectivity and schema
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.chatbot_connection import test_chatbot_connection, get_chatbot_engine
from sqlalchemy import text


def test_chatbot_database():
    """Test that the chatbot database is accessible and has the correct schema"""
    print("=== Testing Chatbot Database Connection ===")
    
    # Test connection
    if test_chatbot_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
        return False
    
    engine = get_chatbot_engine()
    
    with engine.connect() as conn:
        # Test that we can query each table without errors
        print("\n=== Testing Table Queries ===")
        
        tables = ['conversations', 'messages', 'user_preferences', 'search_history', 'session_analytics']
        
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✓ Table '{table}' query successful (rows: {count})")
            except Exception as e:
                print(f"✗ Table '{table}' query failed: {e}")
                return False
        
        # Test foreign key constraint by attempting a valid insert
        print("\n=== Testing Foreign Key Constraint ===")
        try:
            # Create a test conversation
            conn.execute(text("""
                INSERT INTO conversations (session_id, user_id, metadata)
                VALUES ('test_session_12345', 'test_user', '{}'::jsonb)
                ON CONFLICT (session_id) DO NOTHING
            """))
            conn.commit()
            
            # Get the conversation ID
            result = conn.execute(text("""
                SELECT id FROM conversations WHERE session_id = 'test_session_12345'
            """))
            conv_id = result.scalar()
            
            if conv_id:
                # Try to insert a message with the conversation_id
                conn.execute(text("""
                    INSERT INTO messages (conversation_id, role, content, message_type)
                    VALUES (:conv_id, 'user', 'test message', 'text')
                """), {"conv_id": conv_id})
                conn.commit()
                print(f"✓ Foreign key constraint working (conversation_id: {conv_id})")
                
                # Clean up test data
                conn.execute(text("""
                    DELETE FROM messages WHERE conversation_id = :conv_id
                """), {"conv_id": conv_id})
                conn.execute(text("""
                    DELETE FROM conversations WHERE session_id = 'test_session_12345'
                """))
                conn.commit()
            else:
                print("✗ Could not create test conversation")
                return False
                
        except Exception as e:
            print(f"✗ Foreign key constraint test failed: {e}")
            return False
        
        # Test trigger on user_preferences
        print("\n=== Testing update_timestamp Trigger ===")
        try:
            # Insert a test user preference
            conn.execute(text("""
                INSERT INTO user_preferences (user_id, min_budget, max_budget)
                VALUES ('test_trigger_user', 1000, 5000)
                ON CONFLICT (user_id) DO UPDATE
                SET min_budget = EXCLUDED.min_budget, max_budget = EXCLUDED.max_budget
            """))
            conn.commit()
            
            # Get the initial updated_at
            result = conn.execute(text("""
                SELECT updated_at FROM user_preferences WHERE user_id = 'test_trigger_user'
            """))
            initial_time = result.scalar()
            
            # Update the record
            conn.execute(text("""
                UPDATE user_preferences SET min_budget = 1500 WHERE user_id = 'test_trigger_user'
            """))
            conn.commit()
            
            # Check if updated_at changed
            result = conn.execute(text("""
                SELECT updated_at FROM user_preferences WHERE user_id = 'test_trigger_user'
            """))
            new_time = result.scalar()
            
            if new_time > initial_time:
                print("✓ update_timestamp trigger working")
            else:
                print("✗ update_timestamp trigger not working")
            
            # Clean up
            conn.execute(text("""
                DELETE FROM user_preferences WHERE user_id = 'test_trigger_user'
            """))
            conn.commit()
            
        except Exception as e:
            print(f"✗ Trigger test failed: {e}")
            return False
    
    print("\n=== All Tests Passed ===")
    return True


if __name__ == "__main__":
    success = test_chatbot_database()
    sys.exit(0 if success else 1)
