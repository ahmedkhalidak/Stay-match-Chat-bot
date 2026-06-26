-- Chatbot PostgreSQL Schema
-- This schema contains only the chatbot-related tables

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB
);

-- ============================================
-- MESSAGES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(50) DEFAULT 'text',
    metadata JSONB,
    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE
);

-- ============================================
-- USER PREFERENCES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    min_budget DECIMAL(10, 2),
    max_budget DECIMAL(10, 2),
    preferred_location VARCHAR(255),
    tenant_type VARCHAR(50),
    gender VARCHAR(50),
    furnished BOOLEAN,
    wifi BOOLEAN,
    air_conditioning BOOLEAN,
    balcony BOOLEAN,
    private_bathroom BOOLEAN,
    shared_room BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SEARCH HISTORY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS search_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    search_type VARCHAR(50),
    city VARCHAR(255),
    governorate VARCHAR(255),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filters JSONB
);

-- ============================================
-- SESSION ANALYTICS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS session_analytics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    total_searches INTEGER DEFAULT 0,
    no_results_count INTEGER DEFAULT 0,
    avg_response_time DECIMAL(10, 2)
);

-- ============================================
-- INDEXES
-- ============================================

-- Conversations indexes
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- User preferences indexes
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- Search history indexes
CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history(session_id);
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);

-- Session analytics indexes
CREATE INDEX IF NOT EXISTS idx_session_analytics_session_id ON session_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_session_analytics_user_id ON session_analytics(user_id);

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger for user_preferences updated_at
CREATE TRIGGER IF NOT EXISTS trigger_update_user_preferences_timestamp
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
