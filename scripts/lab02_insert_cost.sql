-- Compare INSERT cost with and without additional indexes.

\timing on

TRUNCATE lab02.insert_no_indexes;
TRUNCATE lab02.insert_with_indexes;

\echo 'INSERT without additional indexes'
EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO lab02.insert_no_indexes (
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
FROM generate_series(1, 100000);

\echo 'INSERT with additional indexes'
EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO lab02.insert_with_indexes (
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
FROM generate_series(1, 100000);
