-- Lab 01: EXPLAIN ANALYZE for real Event Booking API queries.
-- Run after migrations and test data generation:
--   set -a && source .env && set +a
--   DATABASE_URL="$LOCAL_DATABASE_URL" go run ./scripts/generate_data.go --users 100000 --venues 1000 --events 100000 --bookings 1000000
--   psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-before-output.txt
--   # apply migrations/202609120001_lab01_booking_indexes.sql
--   psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-after-output.txt

\timing on

ANALYZE users;
ANALYZE venues;
ANALYZE events;
ANALYZE bookings;

\echo 'Scaling entity'
SELECT COUNT(*) AS bookings_count FROM bookings;

\echo 'Existing booking indexes'
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'bookings'
ORDER BY indexname;

\echo 'Query 1: bookings by user_id'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM bookings
WHERE user_id = 123;

\echo 'Query 2: bookings by event_id and status'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM bookings
WHERE event_id = 123
  AND status = 'PAID';

\echo 'Query 3: pagination by user_id and created_at'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM bookings
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 20;

\echo 'Real API JOIN: user bookings with event and venue'
EXPLAIN (ANALYZE, BUFFERS)
SELECT b.id, b.user_id, b.event_id, b.status, b.seats, b.total, b.created_at, b.updated_at,
       u.email, e.title, v.name, v.city, e.starts_at
FROM bookings b
JOIN users u ON u.id = b.user_id
JOIN events e ON e.id = b.event_id
JOIN venues v ON v.id = e.venue_id
WHERE b.user_id = 123
ORDER BY b.created_at DESC;

\echo 'Real API aggregation: event stats'
EXPLAIN (ANALYZE, BUFFERS)
SELECT 123::bigint AS event_id,
       COUNT(*) AS bookings,
       COALESCE(SUM(seats), 0) AS seats,
       COALESCE(SUM(total), 0) AS revenue,
       COALESCE(AVG(total), 0)::float AS average_total
FROM bookings
WHERE event_id = 123;

\echo 'Index usage statistics'
SELECT
    schemaname,
    relname,
    indexrelname,
    idx_scan
FROM pg_stat_user_indexes
WHERE relname IN ('bookings', 'events', 'users', 'venues')
ORDER BY idx_scan, relname, indexrelname;
