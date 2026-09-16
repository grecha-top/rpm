-- Grow public.bookings up to a target number of rows.
--
-- Example:
--   psql "$LOCAL_DATABASE_URL" -v target=5000000 -f scripts/lab02_bookings_insert_to_target.sql

\if :{?target}
\else
    \set target 1000000
\endif

WITH current_state AS (
    SELECT COUNT(*)::bigint AS current_count
    FROM public.bookings
),
to_insert AS (
    SELECT GREATEST(:target::bigint - current_count, 0) AS rows_to_insert
    FROM current_state
)
INSERT INTO public.bookings (
    user_id,
    event_id,
    status,
    seats,
    total,
    created_at
)
SELECT
    1 + (random() * 99999)::bigint,
    1 + (random() * 99999)::bigint,
    (ARRAY['PENDING', 'PAID', 'CANCELLED'])[floor(random() * 3 + 1)],
    1 + (random() * 4)::int,
    1000 + (random() * 9000)::bigint,
    NOW() - (random() * INTERVAL '365 days')
FROM to_insert
CROSS JOIN LATERAL generate_series(1, to_insert.rows_to_insert);

ANALYZE public.bookings;
