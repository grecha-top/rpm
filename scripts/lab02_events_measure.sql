-- Measure table size and query plans for lab02.events at the current row count.

\timing on

SELECT COUNT(*) AS rows_count FROM lab02.events;

SELECT
    pg_size_pretty(pg_relation_size('lab02.events')) AS table_size,
    pg_size_pretty(pg_total_relation_size('lab02.events')) AS total_size;

\echo 'SELECT by user_id'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab02.events
WHERE user_id = 123;

\echo 'SELECT by created_at range: 1 day'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '1 day';

\echo 'Filter + sort + limit'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab02.events
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 100;

\echo 'Aggregation: last 30 days grouped by event_type'
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    event_type,
    COUNT(*)
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_type;

\echo 'Aggregation: 365 days grouped by date'
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    DATE(created_at),
    COUNT(*)
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '365 days'
GROUP BY DATE(created_at);

\echo 'Index sizes'
SELECT
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'lab02'
  AND relname = 'events'
ORDER BY indexrelname;
