-- Lab 01: controlled test table for PostgreSQL index experiments.
-- Run from project root after starting PostgreSQL:
--   set -a && source .env && set +a
--   psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_setup.sql

DROP TABLE IF EXISTS orders_insert_with_indexes;
DROP TABLE IF EXISTS orders_insert_no_indexes;
DROP TABLE IF EXISTS lab_users;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

INSERT INTO orders (
    user_id,
    product_id,
    status,
    amount,
    created_at,
    updated_at
)
SELECT
    (random() * 100000)::BIGINT,
    (random() * 10000)::BIGINT,
    (
        ARRAY[
            'NEW',
            'PAID',
            'DELIVERED',
            'CANCELLED'
        ]
    )[floor(random() * 4 + 1)],
    random() * 10000,
    NOW() - (random() * INTERVAL '2 years'),
    NOW()
FROM generate_series(1, 1000000);

ANALYZE orders;

CREATE TABLE lab_users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

INSERT INTO lab_users (email)
SELECT
    CASE
        WHEN n = 12345 THEN 'test@example.com'
        ELSE 'user' || n || '@example.com'
    END
FROM generate_series(1, 100000) AS n;

ANALYZE lab_users;

CREATE TABLE orders_insert_no_indexes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE orders_insert_with_indexes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_orders_insert_with_indexes_user_id
    ON orders_insert_with_indexes(user_id);

CREATE INDEX idx_orders_insert_with_indexes_status
    ON orders_insert_with_indexes(status);

CREATE INDEX idx_orders_insert_with_indexes_created_at
    ON orders_insert_with_indexes(created_at);
