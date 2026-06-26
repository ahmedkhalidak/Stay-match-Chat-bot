-- Chatbot Database Migration Script
-- Idempotent migration to synchronize existing database with current schema
-- This script can be executed multiple times safely

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- FUNCTIONS
-- ============================================

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

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Check and add session_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'session_id'
    ) THEN
        ALTER TABLE conversations ADD COLUMN session_id VARCHAR(255);
    END IF;

    -- Check and add user_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE conversations ADD COLUMN user_id VARCHAR(255);
    END IF;

    -- Check and add started_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'started_at'
    ) THEN
        ALTER TABLE conversations ADD COLUMN started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add last_activity if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'last_activity'
    ) THEN
        ALTER TABLE conversations ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add message_count if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'message_count'
    ) THEN
        ALTER TABLE conversations ADD COLUMN message_count INTEGER DEFAULT 0;
    END IF;

    -- Check and add status if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'status'
    ) THEN
        ALTER TABLE conversations ADD COLUMN status VARCHAR(50) DEFAULT 'active';
    END IF;

    -- Check and add metadata if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE conversations ADD COLUMN metadata JSONB;
    END IF;
END $$;

-- Add UNIQUE constraint on session_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'conversations' AND constraint_type = 'UNIQUE' AND constraint_name = 'conversations_session_id_key'
    ) THEN
        ALTER TABLE conversations ADD CONSTRAINT conversations_session_id_key UNIQUE (session_id);
    END IF;
END $$;

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
    metadata JSONB
);

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Check and add conversation_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'conversation_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN conversation_id UUID;
    END IF;

    -- Check and add role if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'role'
    ) THEN
        ALTER TABLE messages ADD COLUMN role VARCHAR(50);
    END IF;

    -- Check and add content if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'content'
    ) THEN
        ALTER TABLE messages ADD COLUMN content TEXT;
    END IF;

    -- Check and add created_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE messages ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add message_type if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'message_type'
    ) THEN
        ALTER TABLE messages ADD COLUMN message_type VARCHAR(50) DEFAULT 'text';
    END IF;

    -- Check and add metadata if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE messages ADD COLUMN metadata JSONB;
    END IF;
END $$;

-- Add NOT NULL constraints if they don't exist
DO $$
BEGIN
    -- conversation_id NOT NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'conversation_id' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE messages ALTER COLUMN conversation_id SET NOT NULL;
    END IF;

    -- role NOT NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'role' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE messages ALTER COLUMN role SET NOT NULL;
    END IF;

    -- content NOT NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'content' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE messages ALTER COLUMN content SET NOT NULL;
    END IF;
END $$;

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'messages' AND constraint_name = 'fk_messages_conversation'
    ) THEN
        ALTER TABLE messages
        ADD CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE;
    END IF;
END $$;

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

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Check and add user_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN user_id VARCHAR(255);
    END IF;

    -- Check and add min_budget if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'min_budget'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN min_budget DECIMAL(10, 2);
    END IF;

    -- Check and add max_budget if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'max_budget'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN max_budget DECIMAL(10, 2);
    END IF;

    -- Check and add preferred_location if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'preferred_location'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN preferred_location VARCHAR(255);
    END IF;

    -- Check and add tenant_type if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'tenant_type'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN tenant_type VARCHAR(50);
    END IF;

    -- Check and add gender if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'gender'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN gender VARCHAR(50);
    END IF;

    -- Check and add furnished if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'furnished'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN furnished BOOLEAN;
    END IF;

    -- Check and add wifi if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'wifi'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN wifi BOOLEAN;
    END IF;

    -- Check and add air_conditioning if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'air_conditioning'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN air_conditioning BOOLEAN;
    END IF;

    -- Check and add balcony if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'balcony'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN balcony BOOLEAN;
    END IF;

    -- Check and add private_bathroom if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'private_bathroom'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN private_bathroom BOOLEAN;
    END IF;

    -- Check and add shared_room if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'shared_room'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN shared_room BOOLEAN;
    END IF;

    -- Check and add created_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add updated_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE user_preferences ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Add NOT NULL constraint on user_id if it doesn't exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'user_id' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE user_preferences ALTER COLUMN user_id SET NOT NULL;
    END IF;
END $$;

-- Add UNIQUE constraint on user_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'user_preferences' AND constraint_type = 'UNIQUE' AND constraint_name = 'user_preferences_user_id_key'
    ) THEN
        ALTER TABLE user_preferences ADD CONSTRAINT user_preferences_user_id_key UNIQUE (user_id);
    END IF;
END $$;

-- ============================================
-- SEARCH HISTORY TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS search_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id VARCHAR(255),
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

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Check and add session_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'session_id'
    ) THEN
        ALTER TABLE search_history ADD COLUMN session_id VARCHAR(255);
    END IF;

    -- Check and add user_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE search_history ADD COLUMN user_id VARCHAR(255);
    END IF;

    -- Check and add search_type if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'search_type'
    ) THEN
        ALTER TABLE search_history ADD COLUMN search_type VARCHAR(50);
    END IF;

    -- Check and add city if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'city'
    ) THEN
        ALTER TABLE search_history ADD COLUMN city VARCHAR(255);
    END IF;

    -- Check and add governorate if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'governorate'
    ) THEN
        ALTER TABLE search_history ADD COLUMN governorate VARCHAR(255);
    END IF;

    -- Check and add min_price if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'min_price'
    ) THEN
        ALTER TABLE search_history ADD COLUMN min_price DECIMAL(10, 2);
    END IF;

    -- Check and add max_price if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'max_price'
    ) THEN
        ALTER TABLE search_history ADD COLUMN max_price DECIMAL(10, 2);
    END IF;

    -- Check and add results_count if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'results_count'
    ) THEN
        ALTER TABLE search_history ADD COLUMN results_count INTEGER;
    END IF;

    -- Check and add created_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE search_history ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add filters if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_history' AND column_name = 'filters'
    ) THEN
        ALTER TABLE search_history ADD COLUMN filters JSONB;
    END IF;
END $$;

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

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Check and add session_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'session_id'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN session_id VARCHAR(255);
    END IF;

    -- Check and add user_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN user_id VARCHAR(255);
    END IF;

    -- Check and add started_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'started_at'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

    -- Check and add ended_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'ended_at'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN ended_at TIMESTAMP;
    END IF;

    -- Check and add total_messages if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'total_messages'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN total_messages INTEGER DEFAULT 0;
    END IF;

    -- Check and add total_searches if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'total_searches'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN total_searches INTEGER DEFAULT 0;
    END IF;

    -- Check and add no_results_count if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'no_results_count'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN no_results_count INTEGER DEFAULT 0;
    END IF;

    -- Check and add avg_response_time if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'avg_response_time'
    ) THEN
        ALTER TABLE session_analytics ADD COLUMN avg_response_time DECIMAL(10, 2);
    END IF;
END $$;

-- Add NOT NULL constraint on session_id if it doesn't exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_analytics' AND column_name = 'session_id' AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE session_analytics ALTER COLUMN session_id SET NOT NULL;
    END IF;
END $$;

-- Add UNIQUE constraint on session_id if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'session_analytics' AND constraint_type = 'UNIQUE' AND constraint_name = 'session_analytics_session_id_key'
    ) THEN
        ALTER TABLE session_analytics ADD CONSTRAINT session_analytics_session_id_key UNIQUE (session_id);
    END IF;
END $$;

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

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS trigger_update_user_preferences_timestamp ON user_preferences;
CREATE TRIGGER trigger_update_user_preferences_timestamp
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
