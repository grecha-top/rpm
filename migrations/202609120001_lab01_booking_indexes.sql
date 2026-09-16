-- +goose Up
CREATE INDEX idx_bookings_user_created_at_desc
    ON bookings(user_id, created_at DESC);

CREATE INDEX idx_bookings_event_status_created_at_desc
    ON bookings(event_id, status, created_at DESC);

-- +goose Down
DROP INDEX IF EXISTS idx_bookings_event_status_created_at_desc;
DROP INDEX IF EXISTS idx_bookings_user_created_at_desc;
