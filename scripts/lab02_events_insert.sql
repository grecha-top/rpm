-- Insert a configurable amount of rows into lab02.events.
--
-- Example:
--   psql "$LOCAL_DATABASE_URL" -v rows=100000 -f scripts/lab02_events_insert.sql

\if :{?rows}
\else
    \set rows 10000
\endif

INSERT INTO lab02.events (
    user_id,
    event_type,
    payload,
    created_at
)
SELECT
    (random() * 100000)::bigint,
    CASE
        WHEN random() < 0.4 THEN 'MESSAGE'
        WHEN random() < 0.7 THEN 'LOGIN'
        WHEN random() < 0.9 THEN 'PURCHASE'
        ELSE 'OTHER'
    END,
    '{}'::jsonb,
    NOW() - (random() * INTERVAL '365 days')
FROM generate_series(1, :rows);

ANALYZE lab02.events;
