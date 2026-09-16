-- Indexes for Lab 02 experimental table.

CREATE INDEX IF NOT EXISTS idx_lab02_events_user_id
    ON lab02.events(user_id);

CREATE INDEX IF NOT EXISTS idx_lab02_events_created_at
    ON lab02.events(created_at);

CREATE INDEX IF NOT EXISTS idx_lab02_events_user_created
    ON lab02.events(user_id, created_at DESC);

ANALYZE lab02.events;
