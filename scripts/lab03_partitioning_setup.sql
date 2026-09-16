-- Lab 03: PostgreSQL partitioning, automation and alerting.

DROP SCHEMA IF EXISTS lab03 CASCADE;
CREATE SCHEMA lab03;

CREATE TABLE lab03.events (
    id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload TEXT,
    created_at TIMESTAMP NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE lab03.events_2026_09_09 PARTITION OF lab03.events
    FOR VALUES FROM ('2026-09-09') TO ('2026-09-10');

CREATE TABLE lab03.events_2026_09_10 PARTITION OF lab03.events
    FOR VALUES FROM ('2026-09-10') TO ('2026-09-11');

CREATE TABLE lab03.events_2026_09_11 PARTITION OF lab03.events
    FOR VALUES FROM ('2026-09-11') TO ('2026-09-12');

INSERT INTO lab03.events (id, user_id, event_type, payload, created_at)
SELECT
    n,
    (random() * 50000)::bigint,
    (ARRAY['click', 'view', 'purchase'])[floor(random() * 3 + 1)],
    '{}',
    TIMESTAMP '2026-09-09' + (random() * INTERVAL '3 days')
FROM generate_series(1, 300000) AS n;

CREATE TABLE lab03.products (
    id BIGINT NOT NULL,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL
) PARTITION BY RANGE (price);

CREATE TABLE lab03.products_cheap PARTITION OF lab03.products
    FOR VALUES FROM (0) TO (100);
CREATE TABLE lab03.products_medium PARTITION OF lab03.products
    FOR VALUES FROM (100) TO (1000);
CREATE TABLE lab03.products_expensive PARTITION OF lab03.products
    FOR VALUES FROM (1000) TO (MAXVALUE);

INSERT INTO lab03.products VALUES
    (1, 'Notebook', 75),
    (2, 'Phone', 500),
    (3, 'Laptop', 1500),
    (4, 'Server', 5000);

CREATE TABLE lab03.customers (
    id BIGINT NOT NULL,
    name TEXT NOT NULL,
    customer_type VARCHAR(30) NOT NULL
) PARTITION BY LIST (customer_type);

CREATE TABLE lab03.customers_b2c PARTITION OF lab03.customers
    FOR VALUES IN ('B2C');
CREATE TABLE lab03.customers_b2b PARTITION OF lab03.customers
    FOR VALUES IN ('B2B');
CREATE TABLE lab03.customers_enterprise PARTITION OF lab03.customers
    FOR VALUES IN ('Enterprise');

INSERT INTO lab03.customers VALUES
    (1, 'Alice', 'B2C'),
    (2, 'Acme LLC', 'B2B'),
    (3, 'Mega Corp', 'Enterprise');

CREATE TABLE lab03.user_events (
    id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50),
    created_at TIMESTAMP NOT NULL
) PARTITION BY HASH (user_id);

CREATE TABLE lab03.user_events_0 PARTITION OF lab03.user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE lab03.user_events_1 PARTITION OF lab03.user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE lab03.user_events_2 PARTITION OF lab03.user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE lab03.user_events_3 PARTITION OF lab03.user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

INSERT INTO lab03.user_events (id, user_id, event_type, created_at)
SELECT
    n,
    (random() * 100000)::bigint,
    (ARRAY['click', 'view', 'login'])[floor(random() * 3 + 1)],
    NOW() - (random() * INTERVAL '30 days')
FROM generate_series(1, 200000) AS n;

CREATE INDEX idx_lab03_events_user_id ON lab03.events(user_id);
CREATE INDEX idx_lab03_events_event_type ON lab03.events(event_type);

CREATE TABLE lab03.partition_alert_state (
    table_name TEXT PRIMARY KEY,
    last_status TEXT NOT NULL,
    last_message TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE lab03.partition_alerts (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION lab03.create_events_partition(partition_day DATE)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    partition_name TEXT := 'events_' || to_char(partition_day, 'YYYY_MM_DD');
    full_name TEXT := 'lab03.' || partition_name;
BEGIN
    IF to_regclass(full_name) IS NOT NULL THEN
        RETURN 'exists: ' || full_name;
    END IF;

    EXECUTE format(
        'CREATE TABLE %I.%I PARTITION OF lab03.events FOR VALUES FROM (%L) TO (%L)',
        'lab03',
        partition_name,
        partition_day::timestamp,
        (partition_day + 1)::timestamp
    );

    RETURN 'created: ' || full_name;
END;
$$;

CREATE OR REPLACE FUNCTION lab03.create_events_partitions(required_from DATE, horizon_days INT)
RETURNS TABLE(partition_day DATE, result TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    d DATE;
BEGIN
    FOR d IN
        SELECT generate_series(required_from, required_from + horizon_days, INTERVAL '1 day')::date
    LOOP
        partition_day := d;
        result := lab03.create_events_partition(d);
        RETURN NEXT;
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION lab03.check_events_partitions(required_from DATE, horizon_days INT)
RETURNS TABLE(partition_day DATE, partition_name TEXT, partition_exists BOOLEAN)
LANGUAGE sql
AS $$
    SELECT
        d::date AS partition_day,
        'events_' || to_char(d::date, 'YYYY_MM_DD') AS partition_name,
        to_regclass('lab03.events_' || to_char(d::date, 'YYYY_MM_DD')) IS NOT NULL AS exists
    FROM generate_series(required_from, required_from + horizon_days, INTERVAL '1 day') AS d;
$$;

CREATE OR REPLACE FUNCTION lab03.partition_health_check(required_from DATE, horizon_days INT)
RETURNS TABLE(status TEXT, message TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    missing TEXT;
    current_status TEXT;
    current_message TEXT;
    previous_status TEXT;
BEGIN
    SELECT string_agg(partition_name, ', ' ORDER BY partition_name)
    INTO missing
    FROM lab03.check_events_partitions(required_from, horizon_days)
    WHERE NOT partition_exists;

    IF missing IS NULL THEN
        current_status := 'OK';
        current_message := format('Partition check OK. Table: events. All required partitions exist. Checked at: %s', now());
    ELSE
        current_status := 'CRITICAL';
        current_message := format('Partition alert. Table: events. Missing partitions: %s. Expected horizon: %s days. Checked at: %s', missing, horizon_days, now());
    END IF;

    SELECT last_status INTO previous_status
    FROM lab03.partition_alert_state
    WHERE table_name = 'events';

    IF previous_status IS DISTINCT FROM current_status THEN
        INSERT INTO lab03.partition_alerts (table_name, status, message)
        VALUES ('events', current_status, current_message);
    END IF;

    INSERT INTO lab03.partition_alert_state (table_name, last_status, last_message, updated_at)
    VALUES ('events', current_status, current_message, now())
    ON CONFLICT (table_name)
    DO UPDATE SET
        last_status = EXCLUDED.last_status,
        last_message = EXCLUDED.last_message,
        updated_at = EXCLUDED.updated_at;

    status := current_status;
    message := current_message;
    RETURN NEXT;
END;
$$;

CREATE TABLE lab03.bookings_partitioned (
    id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    event_id BIGINT NOT NULL,
    status TEXT NOT NULL,
    seats INTEGER NOT NULL,
    total BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE lab03.bookings_2025 PARTITION OF lab03.bookings_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE lab03.bookings_2026 PARTITION OF lab03.bookings_partitioned
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE lab03.bookings_2027 PARTITION OF lab03.bookings_partitioned
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

INSERT INTO lab03.bookings_partitioned
SELECT id, user_id, event_id, status, seats, total, created_at, updated_at
FROM public.bookings
WHERE created_at >= '2025-01-01'
  AND created_at < '2027-01-01'
LIMIT 1000000;

CREATE INDEX idx_lab03_bookings_user_created
    ON lab03.bookings_partitioned(user_id, created_at DESC);

CREATE INDEX idx_lab03_bookings_created_at
    ON lab03.bookings_partitioned(created_at);

ANALYZE lab03.events;
ANALYZE lab03.products;
ANALYZE lab03.customers;
ANALYZE lab03.user_events;
ANALYZE lab03.bookings_partitioned;
