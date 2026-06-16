-- Migration: Add UNIQUE constraint on conversations.session_id
-- This prevents duplicate conversations for the same session,
-- which was causing messages to be stored across different conversation IDs.

-- First, clean up any duplicate rows (keep the first conversation per session_id)
DELETE FROM conversations
WHERE id NOT IN (
    SELECT MIN(id)
    FROM conversations
    GROUP BY session_id
);

-- Then add the unique constraint
ALTER TABLE conversations
ADD CONSTRAINT uq_conversations_session_id UNIQUE (session_id);

-- Drop the old non-unique index (replaced by unique constraint)
DROP INDEX IF EXISTS idx_conversations_session_id;