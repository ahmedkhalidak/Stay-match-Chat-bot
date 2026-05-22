-- Chatbot Database Schema (PostgreSQL - Neon)
-- Database: staymatch_chatbot_db

-- Conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active', -- active, archived, deleted
    metadata TEXT NULL, -- JSON for additional data
);

CREATE INDEX IX_conversations_session_id ON conversations(session_id);
CREATE INDEX IX_conversations_user_id ON conversations(user_id);
CREATE INDEX IX_conversations_last_activity ON conversations(last_activity);

-- Messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(50) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, file
    metadata TEXT NULL, -- JSON for additional data
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
);

CREATE INDEX IX_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IX_messages_created_at ON messages(created_at);
CREATE INDEX IX_messages_role ON messages(role);

-- User preferences table (for persistent user preferences)
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    min_budget INT NULL,
    max_budget INT NULL,
    preferred_location VARCHAR(255) NULL,
    tenant_type VARCHAR(50) NULL,
    gender VARCHAR(50) NULL,
    furnished BOOLEAN NULL,
    wifi BOOLEAN NULL,
    air_conditioning BOOLEAN NULL,
    balcony BOOLEAN NULL,
    private_bathroom BOOLEAN NULL,
    shared_room BOOLEAN NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

CREATE INDEX IX_user_preferences_user_id ON user_preferences(user_id);

-- Search history table (for analytics and improvement)
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NULL,
    search_type VARCHAR(50) NOT NULL, -- room, property, full, shared
    city VARCHAR(255) NULL,
    governorate VARCHAR(255) NULL,
    min_price INT NULL,
    max_price INT NULL,
    results_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filters TEXT NULL, -- JSON for complete filters
);

CREATE INDEX IX_search_history_session_id ON search_history(session_id);
CREATE INDEX IX_search_history_user_id ON search_history(user_id);
CREATE INDEX IX_search_history_created_at ON search_history(created_at);

-- Session analytics table (for tracking session metrics)
CREATE TABLE session_analytics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    total_messages INT DEFAULT 0,
    total_searches INT DEFAULT 0,
    no_results_count INT DEFAULT 0,
    avg_response_time DOUBLE PRECISION NULL,
);

CREATE INDEX IX_session_analytics_session_id ON session_analytics(session_id);
CREATE INDEX IX_session_analytics_user_id ON session_analytics(user_id);
