-- Lab 03 experiment runner.

\timing on

\echo 'Range partitions distribution'
SELECT tableoid::regclass AS partition_name, COUNT(*)
FROM lab03.events
GROUP BY tableoid
ORDER BY partition_name;

\echo 'Insert outside existing range must fail'
\set ON_ERROR_STOP off
INSERT INTO lab03.events VALUES (999999999, 1, 'click', '{}', '2026-09-12 00:00:00');
\set ON_ERROR_STOP on

\echo 'Partition pruning by created_at'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab03.events
WHERE created_at >= '2026-09-10'
  AND created_at < '2026-09-11';

\echo 'No pruning by event_type only'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab03.events
WHERE event_type = 'click';

\echo 'Range partitioning by price'
SELECT tableoid::regclass AS partition_name, COUNT(*)
FROM lab03.products
GROUP BY tableoid
ORDER BY partition_name;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab03.products
WHERE price >= 100
  AND price < 500;

\echo 'List partitioning by customer_type'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab03.customers
WHERE customer_type = 'B2B';

\echo 'Unknown list value before and after DEFAULT partition'
\set ON_ERROR_STOP off
INSERT INTO lab03.customers VALUES (100, 'Test User', 'VIP');
\set ON_ERROR_STOP on
CREATE TABLE lab03.customers_default PARTITION OF lab03.customers DEFAULT;
INSERT INTO lab03.customers VALUES (100, 'Test User', 'VIP');
SELECT tableoid::regclass AS partition_name, COUNT(*)
FROM lab03.customers
GROUP BY tableoid
ORDER BY partition_name;

\echo 'Hash partitioning distribution'
SELECT tableoid::regclass AS partition_name, COUNT(*)
FROM lab03.user_events
GROUP BY tableoid
ORDER BY partition_name;

\echo 'Partitioning + index'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab03.events
WHERE created_at >= '2026-09-10'
  AND created_at < '2026-09-11'
  AND user_id = 12345;

\echo 'event_type with partitioning and index'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab03.events
WHERE event_type = 'click';

\echo 'Create future partitions job'
SELECT * FROM lab03.create_events_partitions('2026-09-11', 3);

\echo 'Health check OK'
SELECT * FROM lab03.partition_health_check('2026-09-11', 3);

\echo 'Simulate missed partition and alert'
DROP TABLE lab03.events_2026_09_14;
SELECT * FROM lab03.partition_health_check('2026-09-11', 3);
SELECT * FROM lab03.partition_health_check('2026-09-11', 3);
SELECT * FROM lab03.partition_alerts ORDER BY id;

\echo 'Recover partition and send recovery'
SELECT * FROM lab03.create_events_partition('2026-09-14');
SELECT * FROM lab03.partition_health_check('2026-09-11', 3);
SELECT * FROM lab03.partition_alerts ORDER BY id;

\echo 'Service partitioned bookings: date range pruning'
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM lab03.bookings_partitioned
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01';

\echo 'Service partitioned bookings: user pagination'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM lab03.bookings_partitioned
WHERE user_id = 123
  AND created_at >= '2026-01-01'
  AND created_at < '2027-01-01'
ORDER BY created_at DESC
LIMIT 50;

\echo 'Service partitioned bookings: aggregation'
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, COUNT(*), SUM(total)
FROM lab03.bookings_partitioned
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01'
GROUP BY event_id
ORDER BY SUM(total) DESC
LIMIT 20;
