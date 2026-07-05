-- Table for social media content queue
CREATE TABLE IF NOT EXISTS social_media_queue (
    id SERIAL PRIMARY KEY,
    channel VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',  -- queued | in_progress | completed | failed
    script_path TEXT,
    video_path TEXT,
    metadata_path TEXT,
    thumbnail_path TEXT,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient querying by channel and status
CREATE INDEX IF NOT EXISTS idx_social_media_queue_channel_status ON social_media_queue (channel, status);

-- Partial unique index to prevent duplicate (channel, topic) for active items
-- Prevents duplicates for items that are not completed or failed
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_media_queue_unique_channel_topic
ON social_media_queue (channel, topic)
WHERE status NOT IN ('completed', 'failed');

-- Trigger to automatically update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_social_media_queue_updated_at ON social_media_queue;
CREATE TRIGGER update_social_media_queue_updated_at
    BEFORE UPDATE ON social_media_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();