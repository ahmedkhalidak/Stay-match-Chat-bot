"""
Test Suite for PostgreSQL Chatbot Database
Tests conversation and message repositories with PostgreSQL
"""

import pytest
import os
from datetime import datetime
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.database.chatbot_connection import get_chatbot_engine, test_chatbot_connection


@pytest.fixture(scope="module")
def db_connection():
    """Setup database connection for tests"""
    # Skip tests if DATABASE_URL not set
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    
    # Test connection
    if not test_chatbot_connection():
        pytest.skip("Could not connect to database")
    
    yield get_chatbot_engine()
    
    # Cleanup could be added here if needed


@pytest.fixture
def conversation_repo(db_connection):
    """Create conversation repository instance"""
    return ConversationRepository()


@pytest.fixture
def message_repo(db_connection):
    """Create message repository instance"""
    return MessageRepository()


def test_create_conversation(conversation_repo):
    """Test creating a new conversation"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    user_id = "test_user_123"
    metadata = {"test": "data"}
    
    conv_id = conversation_repo.create_conversation(
        session_id=session_id,
        user_id=user_id,
        metadata=metadata
    )
    
    assert conv_id is not None
    assert isinstance(conv_id, int)
    assert conv_id > 0
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_get_conversation_by_session(conversation_repo):
    """Test retrieving conversation by session ID"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    user_id = "test_user_456"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(
        session_id=session_id,
        user_id=user_id
    )
    
    # Retrieve conversation
    conversation = conversation_repo.get_conversation_by_session(session_id)
    
    assert conversation is not None
    assert conversation["id"] == conv_id
    assert conversation["session_id"] == session_id
    assert conversation["user_id"] == user_id
    assert conversation["message_count"] == 0
    assert conversation["status"] == "active"
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_update_last_activity(conversation_repo):
    """Test updating last activity timestamp"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Update last activity
    conversation_repo.update_last_activity(session_id, message_count=5)
    
    # Verify update
    conversation = conversation_repo.get_conversation_by_session(session_id)
    assert conversation["message_count"] == 5
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_increment_message_count(conversation_repo):
    """Test incrementing message count"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conversation_repo.create_conversation(session_id=session_id)
    
    # Increment message count
    conversation_repo.increment_message_count(session_id)
    conversation_repo.increment_message_count(session_id)
    
    # Verify increment
    conversation = conversation_repo.get_conversation_by_session(session_id)
    assert conversation["message_count"] == 2
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_delete_conversation(conversation_repo):
    """Test deleting a conversation"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conversation_repo.create_conversation(session_id=session_id)
    
    # Verify exists
    conversation = conversation_repo.get_conversation_by_session(session_id)
    assert conversation is not None
    
    # Delete conversation
    deleted = conversation_repo.delete_conversation(session_id)
    assert deleted is True
    
    # Verify deleted
    conversation = conversation_repo.get_conversation_by_session(session_id)
    assert conversation is None


def test_add_message(message_repo, conversation_repo):
    """Test adding a message to a conversation"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add message
    msg_id = message_repo.add_message(
        conversation_id=conv_id,
        role="user",
        content="Hello, this is a test message",
        message_type="text"
    )
    
    assert msg_id is not None
    assert isinstance(msg_id, int)
    assert msg_id > 0
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_get_conversation_messages(message_repo, conversation_repo):
    """Test retrieving messages for a conversation"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add multiple messages
    message_repo.add_message(conv_id, "user", "Hello")
    message_repo.add_message(conv_id, "assistant", "Hi there!")
    message_repo.add_message(conv_id, "user", "How are you?")
    
    # Retrieve messages
    messages = message_repo.get_conversation_messages(conv_id, limit=10)
    
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["content"] == "How are you?"
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_get_session_messages(message_repo, conversation_repo):
    """Test retrieving messages by session ID"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add messages
    message_repo.add_message(conv_id, "user", "Test message 1")
    message_repo.add_message(conv_id, "assistant", "Test response 1")
    
    # Retrieve by session
    messages = message_repo.get_session_messages(session_id, limit=10)
    
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test message 1"
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_get_recent_messages(message_repo, conversation_repo):
    """Test retrieving recent messages"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add multiple messages
    for i in range(5):
        message_repo.add_message(conv_id, "user", f"Message {i}")
    
    # Get recent 3 messages
    recent = message_repo.get_recent_messages(conv_id, n=3)
    
    assert len(recent) == 3
    # Should be in chronological order (reversed from DESC query)
    assert recent[0]["content"] == "Message 2"
    assert recent[1]["content"] == "Message 3"
    assert recent[2]["content"] == "Message 4"
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_message_with_metadata(message_repo, conversation_repo):
    """Test adding message with metadata"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add message with metadata
    metadata = {"tokens": 10, "model": "gpt-4"}
    msg_id = message_repo.add_message(
        conversation_id=conv_id,
        role="assistant",
        content="Response",
        metadata=metadata
    )
    
    # Retrieve and verify
    messages = message_repo.get_conversation_messages(conv_id, limit=1)
    assert len(messages) == 1
    assert messages[0]["metadata"] is not None
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_conversation_with_metadata(conversation_repo):
    """Test creating conversation with metadata"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    metadata = {"source": "web", "locale": "en-US"}
    
    conv_id = conversation_repo.create_conversation(
        session_id=session_id,
        user_id="test_user",
        metadata=metadata
    )
    
    # Retrieve and verify
    conversation = conversation_repo.get_conversation_by_session(session_id)
    assert conversation is not None
    assert conversation["metadata"] is not None
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


def test_delete_conversation_messages(message_repo, conversation_repo):
    """Test deleting all messages for a conversation"""
    session_id = f"test_session_{datetime.now().timestamp()}"
    
    # Create conversation
    conv_id = conversation_repo.create_conversation(session_id=session_id)
    
    # Add messages
    message_repo.add_message(conv_id, "user", "Message 1")
    message_repo.add_message(conv_id, "user", "Message 2")
    
    # Verify messages exist
    messages = message_repo.get_conversation_messages(conv_id)
    assert len(messages) == 2
    
    # Delete messages
    deleted = message_repo.delete_conversation_messages(conv_id)
    assert deleted is True
    
    # Verify deletion
    messages = message_repo.get_conversation_messages(conv_id)
    assert len(messages) == 0
    
    # Cleanup
    conversation_repo.delete_conversation(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
