-- +goose Up
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE venues (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    address TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    venue_id BIGINT NOT NULL REFERENCES venues(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    starts_at TIMESTAMPTZ NOT NULL,
    base_price BIGINT NOT NULL CHECK (base_price >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE event_categories (
    event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, category_id)
);

CREATE TABLE bookings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    seats INTEGER NOT NULL CHECK (seats > 0),
    total BIGINT NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_venue_id ON events(venue_id);
CREATE INDEX idx_events_starts_at ON events(starts_at);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_event_id ON bookings(event_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_created_at ON bookings(created_at);

INSERT INTO users (email, full_name) VALUES
    ('alice@example.com', 'Alice Ivanova'),
    ('bob@example.com', 'Bob Petrov'),
    ('maria@example.com', 'Maria Sokolova');

INSERT INTO venues (name, city, address, capacity) VALUES
    ('Main Hall', 'Moscow', 'Tverskaya 1', 500),
    ('Open Stage', 'Saint Petersburg', 'Nevsky 20', 1200);

INSERT INTO events (venue_id, title, status, starts_at, base_price) VALUES
    (1, 'Go Backend Night', 'PUBLISHED', now() + interval '10 days', 3000),
    (2, 'Database Scaling Workshop', 'PUBLISHED', now() + interval '20 days', 5000);

INSERT INTO categories (name) VALUES
    ('Technology'),
    ('Education'),
    ('Conference');

INSERT INTO event_categories (event_id, category_id) VALUES
    (1, 1),
    (1, 3),
    (2, 1),
    (2, 2);

INSERT INTO bookings (user_id, event_id, status, seats, total) VALUES
    (1, 1, 'PAID', 2, 6000),
    (2, 1, 'PENDING', 1, 3000),
    (3, 2, 'PAID', 3, 15000);

-- +goose Down
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS event_categories;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS venues;
DROP TABLE IF EXISTS users;
