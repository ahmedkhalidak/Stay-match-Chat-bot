"""
Chatbot Database Connection
Separate connection for chatbot database (conversations, messages, etc.)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.utils.logger import debug_log


# Chatbot database engine (separate from backend)
_chatbot_engine = None
_chatbot_session_factory = None


def get_chatbot_engine():
    """Get or create chatbot database engine"""
    global _chatbot_engine
    if _chatbot_engine is None:
        settings = Settings()
        _chatbot_engine = create_engine(
            settings.chatbot_db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=True
        )
        
        # Log chatbot database connection
        try:
            with _chatbot_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                # Parse connection string to extract database info
                db_url = settings.chatbot_db_url
                if "postgresql" in db_url:
                    debug_log("CHATBOT_DB_CONNECTED", f"PostgreSQL - URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
                else:
                    debug_log("CHATBOT_DB_CONNECTED", f"Database - URL: {db_url}")
        except Exception as e:
            debug_log("CHATBOT_DB_ERROR", f"Failed to connect: {str(e)}")
        
        debug_log("CHATBOT_DB", "Chatbot database engine created")
    return _chatbot_engine


def get_chatbot_session():
    """Get a new session for chatbot database"""
    global _chatbot_session_factory
    if _chatbot_session_factory is None:
        engine = get_chatbot_engine()
        _chatbot_session_factory = sessionmaker(bind=engine)
    return _chatbot_session_factory()


def test_chatbot_connection():
    """Test connection to chatbot database"""
    try:
        engine = get_chatbot_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            debug_log("CHATBOT_DB", "Connection test successful")
            return True
    except Exception as e:
        debug_log("CHATBOT_DB_ERROR", f"Connection test failed: {str(e)}")
        return False
