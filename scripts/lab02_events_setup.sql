-- Lab 02: experimental table for data growth research.
-- Uses a separate schema to avoid conflict with the service public.events table.
--
-- Run:
--   PGPASSWORD=postgres psql 'postgres://postgres:postgres@127.0.0.1:5432/rpm?sslmode=disable' \
--     -v ON_ERROR_STOP=1 -f scripts/lab02_events_setup.sql

DROP SCHEMA IF EXISTS lab02 CASCADE;
CREATE SCHEMA lab02;

CREATE TABLE lab02.events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE lab02.insert_no_indexes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE lab02.insert_with_indexes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_lab02_insert_with_user_id
    ON lab02.insert_with_indexes(user_id);

CREATE INDEX idx_lab02_insert_with_created_at
    ON lab02.insert_with_indexes(created_at);

CREATE INDEX idx_lab02_insert_with_user_created
    ON lab02.insert_with_indexes(user_id, created_at DESC);
