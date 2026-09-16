-- Lab 03: pg_cron schedule for partition maintenance.
--
-- Prerequisites:
-- 1. PostgreSQL image contains pg_cron.
-- 2. PostgreSQL starts with shared_preload_libraries=pg_cron.
-- 3. cron.database_name points to the database where jobs must run.

CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Make the script repeatable: remove old jobs with the same names first.
DO $$
DECLARE
    existing_job RECORD;
BEGIN
    FOR existing_job IN
        SELECT jobid
        FROM cron.job
        WHERE jobname IN (
            'lab03-create-events-partitions',
            'lab03-check-events-partitions'
        )
    LOOP
        PERFORM cron.unschedule(existing_job.jobid);
    END LOOP;
END;
$$;

-- Create event partitions for today and the next 3 days every day at 01:00.
SELECT cron.schedule(
    'lab03-create-events-partitions',
    '0 1 * * *',
    $$SELECT * FROM lab03.create_events_partitions(current_date, 3);$$
);

-- Check partition health every day at 01:05 and write OK/CRITICAL alerts.
SELECT cron.schedule(
    'lab03-check-events-partitions',
    '5 1 * * *',
    $$SELECT * FROM lab03.partition_health_check(current_date, 3);$$
);

-- Useful checks:
-- SELECT * FROM cron.job ORDER BY jobid;
-- SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;
--
-- Unschedule if needed:
-- SELECT cron.unschedule('lab03-create-events-partitions');
-- SELECT cron.unschedule('lab03-check-events-partitions');
