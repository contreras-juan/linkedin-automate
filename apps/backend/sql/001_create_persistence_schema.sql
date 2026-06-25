CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    source_url VARCHAR NOT NULL DEFAULT '',
    publishing_status VARCHAR NOT NULL DEFAULT 'draft',
    active_generation_id BIGINT,
    paper_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generations (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type VARCHAR NOT NULL DEFAULT 'linkedin_post',
    content_focus VARCHAR,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    hashtags JSONB NOT NULL DEFAULT '[]'::jsonb,
    paper_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id BIGSERIAL PRIMARY KEY,
    generation_id BIGINT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    agent_name VARCHAR NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_posts_active_generation_id'
    ) THEN
        ALTER TABLE posts
        ADD CONSTRAINT fk_posts_active_generation_id
        FOREIGN KEY (active_generation_id)
        REFERENCES generations(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_posts_title ON posts(title);
CREATE INDEX IF NOT EXISTS ix_posts_source_url ON posts(source_url);
CREATE INDEX IF NOT EXISTS ix_posts_publishing_status ON posts(publishing_status);
CREATE INDEX IF NOT EXISTS ix_posts_active_generation_id ON posts(active_generation_id);
CREATE INDEX IF NOT EXISTS ix_posts_updated_at ON posts(updated_at);

CREATE INDEX IF NOT EXISTS ix_generations_post_id ON generations(post_id);
CREATE INDEX IF NOT EXISTS ix_generations_content_type ON generations(content_type);
CREATE INDEX IF NOT EXISTS ix_generations_created_at ON generations(created_at);

CREATE INDEX IF NOT EXISTS ix_agent_logs_generation_id ON agent_logs(generation_id);
CREATE INDEX IF NOT EXISTS ix_agent_logs_sequence ON agent_logs(sequence);
CREATE INDEX IF NOT EXISTS ix_agent_logs_agent_name ON agent_logs(agent_name);
