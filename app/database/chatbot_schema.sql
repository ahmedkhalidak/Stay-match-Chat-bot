-- Chatbot Database Schema (Separate from Backend Database)
-- Database: staymatch_chatbot_db

-- Conversations table
CREATE TABLE conversations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(255) NOT NULL UNIQUE,
    user_id NVARCHAR(255) NULL,
    started_at DATETIME DEFAULT GETDATE(),
    last_activity DATETIME DEFAULT GETDATE(),
    message_count INT DEFAULT 0,
    status NVARCHAR(50) DEFAULT 'active', -- active, archived, deleted
    metadata NVARCHAR(MAX) NULL, -- JSON for additional data
);

CREATE INDEX IX_conversations_session_id ON conversations(session_id);
CREATE INDEX IX_conversations_user_id ON conversations(user_id);
CREATE INDEX IX_conversations_last_activity ON conversations(last_activity);

-- Messages table
CREATE TABLE messages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    conversation_id INT NOT NULL,
    role NVARCHAR(50) NOT NULL, -- user, assistant, system
    content NVARCHAR(MAX) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    message_type NVARCHAR(50) DEFAULT 'text', -- text, image, file
    metadata NVARCHAR(MAX) NULL, -- JSON for additional data
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
);

CREATE INDEX IX_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IX_messages_created_at ON messages(created_at);
CREATE INDEX IX_messages_role ON messages(role);

-- User preferences table (for persistent user preferences)
CREATE TABLE user_preferences (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id NVARCHAR(255) NOT NULL UNIQUE,
    min_budget INT NULL,
    max_budget INT NULL,
    preferred_location NVARCHAR(255) NULL,
    tenant_type NVARCHAR(50) NULL,
    gender NVARCHAR(50) NULL,
    furnished BIT NULL,
    wifi BIT NULL,
    air_conditioning BIT NULL,
    balcony BIT NULL,
    private_bathroom BIT NULL,
    shared_room BIT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE(),
);

CREATE INDEX IX_user_preferences_user_id ON user_preferences(user_id);

-- Search history table (for analytics and improvement)
CREATE TABLE search_history (
    id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(255) NOT NULL,
    user_id NVARCHAR(255) NULL,
    search_type NVARCHAR(50) NOT NULL, -- room, property, full, shared
    city NVARCHAR(255) NULL,
    governorate NVARCHAR(255) NULL,
    min_price INT NULL,
    max_price INT NULL,
    results_count INT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    filters NVARCHAR(MAX) NULL, -- JSON for complete filters
);

CREATE INDEX IX_search_history_session_id ON search_history(session_id);
CREATE INDEX IX_search_history_user_id ON search_history(user_id);
CREATE INDEX IX_search_history_created_at ON search_history(created_at);

-- Session analytics table (for tracking session metrics)
CREATE TABLE session_analytics (
    id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(255) NOT NULL UNIQUE,
    user_id NVARCHAR(255) NULL,
    started_at DATETIME DEFAULT GETDATE(),
    ended_at DATETIME NULL,
    total_messages INT DEFAULT 0,
    total_searches INT DEFAULT 0,
    no_results_count INT DEFAULT 0,
    avg_response_time FLOAT NULL,
);

CREATE INDEX IX_session_analytics_session_id ON session_analytics(session_id);
CREATE INDEX IX_session_analytics_user_id ON session_analytics(user_id);
