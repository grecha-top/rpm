-- Lab 01: EXPLAIN ANALYZE experiments for the controlled orders table.
-- This script intentionally creates indexes step by step.
-- Recommended usage:
--   psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_setup.sql
--   psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_experiments.sql | tee docs/lab-01-orders-output.txt

\timing on

\echo 'Task 3: EXPLAIN without index'
EXPLAIN
SELECT * FROM orders WHERE user_id = 123;

\echo 'Task 4: EXPLAIN ANALYZE without index'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = 123;

\echo 'Task 5: Sequential Scan examples'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE amount > 0;

\echo 'Task 6: B-tree index by user_id'
CREATE INDEX IF NOT EXISTS idx_orders_user_id
    ON orders(user_id);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = 123;

\echo 'Task 7-8: low selectivity status index'
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders(status);
ANALYZE orders;

SELECT status, COUNT(*) AS rows_count
FROM orders
GROUP BY status
ORDER BY rows_count DESC;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE status = 'PAID';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE status = 'NEW';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE status = 'DELIVERED';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE status = 'CANCELLED';

\echo 'Task 9: range query by created_at'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days';

CREATE INDEX IF NOT EXISTS idx_orders_created_at
    ON orders(created_at);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '1 day';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '1 month';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '1 year';

\echo 'Task 10: Bitmap Scan candidate'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE amount BETWEEN 1000 AND 3000;

CREATE INDEX IF NOT EXISTS idx_orders_amount
    ON orders(amount);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE amount BETWEEN 1000 AND 3000;

\echo 'Task 11: multiple conditions with separate indexes'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
  AND status = 'PAID';

\echo 'Task 12: composite index'
CREATE INDEX IF NOT EXISTS idx_orders_user_status
    ON orders(user_id, status);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
  AND status = 'PAID';

\echo 'Task 13: column order in composite indexes'
CREATE INDEX IF NOT EXISTS idx_orders_user_created_at
    ON orders(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_orders_created_at_user
    ON orders(created_at, user_id);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = 123;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
  AND created_at > NOW() - INTERVAL '30 days';

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE created_at > NOW() - INTERVAL '30 days';

\echo 'Task 14-15: WHERE + ORDER BY + LIMIT'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
ORDER BY created_at DESC;

CREATE INDEX IF NOT EXISTS idx_orders_user_created_at_desc
    ON orders(user_id, created_at DESC);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
ORDER BY created_at DESC;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 20;

\echo 'Task 16: Index Only Scan and INCLUDE'
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, user_id FROM orders WHERE user_id = 123;

CREATE INDEX IF NOT EXISTS idx_orders_user_id_include
    ON orders(user_id) INCLUDE (id, status, created_at);
VACUUM (ANALYZE) orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, user_id FROM orders WHERE user_id = 123;

\echo 'Task 17: partial index'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE status = 'NEW'
ORDER BY created_at;

CREATE INDEX IF NOT EXISTS idx_orders_new
    ON orders(created_at)
    WHERE status = 'NEW';
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE status = 'NEW'
ORDER BY created_at;

\echo 'Task 18: expression index'
CREATE INDEX IF NOT EXISTS idx_lab_users_email
    ON lab_users(email);
ANALYZE lab_users;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM lab_users WHERE LOWER(email) = 'test@example.com';

CREATE INDEX IF NOT EXISTS idx_lab_users_lower_email
    ON lab_users(LOWER(email));
ANALYZE lab_users;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM lab_users WHERE LOWER(email) = 'test@example.com';

\echo 'Task 19: insert cost without indexes'
EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO orders_insert_no_indexes (user_id, status, amount, created_at)
SELECT
    (random() * 100000)::BIGINT,
    (ARRAY['NEW', 'PAID', 'DELIVERED', 'CANCELLED'])[floor(random() * 4 + 1)],
    random() * 10000,
    NOW() - (random() * INTERVAL '2 years')
FROM generate_series(1, 100000);

\echo 'Task 19: insert cost with indexes'
EXPLAIN (ANALYZE, BUFFERS)
INSERT INTO orders_insert_with_indexes (user_id, status, amount, created_at)
SELECT
    (random() * 100000)::BIGINT,
    (ARRAY['NEW', 'PAID', 'DELIVERED', 'CANCELLED'])[floor(random() * 4 + 1)],
    random() * 10000,
    NOW() - (random() * INTERVAL '2 years')
FROM generate_series(1, 100000);

\echo 'Task 20: index usage statistics'
SELECT
    schemaname,
    relname,
    indexrelname,
    idx_scan
FROM pg_stat_user_indexes
WHERE relname IN ('orders', 'lab_users', 'orders_insert_no_indexes', 'orders_insert_with_indexes')
ORDER BY idx_scan, relname, indexrelname;

\echo 'Task 21: final optimization query before and after final composite index'
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    id,
    amount,
    status,
    created_at
FROM orders
WHERE user_id = 123
  AND status = 'PAID'
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC
LIMIT 50;

CREATE INDEX IF NOT EXISTS idx_orders_user_status_created_at_desc
    ON orders(user_id, status, created_at DESC);
ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    id,
    amount,
    status,
    created_at
FROM orders
WHERE user_id = 123
  AND status = 'PAID'
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC
LIMIT 50;
