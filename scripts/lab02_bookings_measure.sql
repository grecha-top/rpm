-- Lab 02 measurements for the service scaling entity: public.bookings.

\timing on

ANALYZE public.bookings;

SELECT COUNT(*) AS bookings_count FROM public.bookings;

SELECT
    pg_size_pretty(pg_relation_size('public.bookings')) AS table_size,
    pg_size_pretty(pg_total_relation_size('public.bookings')) AS total_size;

\echo 'Query 1: lookup by user_id'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.bookings
WHERE user_id = 123;

\echo 'Query 2: date range'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.bookings
WHERE created_at >= NOW() - INTERVAL '30 days';

\echo 'Query 3: filter + sort + limit'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.bookings
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 50;

\echo 'Aggregation: event revenue'
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    event_id,
    COUNT(*) AS bookings,
    SUM(total) AS revenue
FROM public.bookings
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_id
ORDER BY revenue DESC
LIMIT 20;

\echo 'Booking index sizes'
SELECT
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND relname = 'bookings'
ORDER BY indexrelname;
