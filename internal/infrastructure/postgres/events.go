package postgres

import (
	"context"

	"rpm/internal/domain"
)

func (r *Repository) CreateEvent(ctx context.Context, event domain.Event) (domain.Event, error) {
	row := r.db.QueryRow(ctx, `
		INSERT INTO events (venue_id, title, status, starts_at, base_price) VALUES ($1, $2, $3, $4, $5)
		RETURNING id, venue_id, title, status, starts_at, base_price, created_at, updated_at`,
		event.VenueID, event.Title, event.Status, event.StartsAt, event.BasePrice)
	return scanEvent(row)
}

func (r *Repository) ListEvents(ctx context.Context) ([]domain.Event, error) {
	rows, err := r.readDB.Query(ctx, `SELECT id, venue_id, title, status, starts_at, base_price, created_at, updated_at FROM events ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []domain.Event
	for rows.Next() {
		event, err := scanEvent(rows)
		if err != nil {
			return nil, err
		}
		events = append(events, event)
	}
	return events, rows.Err()
}

func (r *Repository) GetEvent(ctx context.Context, id int64) (domain.Event, error) {
	event, err := scanEvent(r.readDB.QueryRow(ctx, `SELECT id, venue_id, title, status, starts_at, base_price, created_at, updated_at FROM events WHERE id=$1`, id))
	return event, normalizeNoRows(err)
}

func (r *Repository) UpdateEvent(ctx context.Context, id int64, event domain.Event) (domain.Event, error) {
	row := r.db.QueryRow(ctx, `
		UPDATE events SET venue_id=$1, title=$2, status=$3, starts_at=$4, base_price=$5, updated_at=now()
		WHERE id=$6
		RETURNING id, venue_id, title, status, starts_at, base_price, created_at, updated_at`,
		event.VenueID, event.Title, event.Status, event.StartsAt, event.BasePrice, id)
	updated, err := scanEvent(row)
	return updated, normalizeNoRows(err)
}

func (r *Repository) DeleteEvent(ctx context.Context, id int64) error {
	tag, err := r.db.Exec(ctx, `DELETE FROM events WHERE id=$1`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *Repository) AddEventCategory(ctx context.Context, eventID, categoryID int64) error {
	_, err := r.db.Exec(ctx, `INSERT INTO event_categories (event_id, category_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`, eventID, categoryID)
	return err
}

func (r *Repository) EventBookings(ctx context.Context, eventID int64) ([]domain.BookingDetails, error) {
	rows, err := r.readDB.Query(ctx, `
		SELECT b.id, b.user_id, b.event_id, b.status, b.seats, b.total, b.created_at, b.updated_at,
		       u.email, e.title, v.name, v.city, e.starts_at
		FROM bookings b
		JOIN users u ON u.id = b.user_id
		JOIN events e ON e.id = b.event_id
		JOIN venues v ON v.id = e.venue_id
		WHERE b.event_id = $1
		ORDER BY b.created_at DESC`, eventID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanBookingDetailsRows(rows)
}

func (r *Repository) EventStats(ctx context.Context, eventID int64) (domain.EventStats, error) {
	var stats domain.EventStats
	err := r.readDB.QueryRow(ctx, `
		SELECT $1::bigint AS event_id,
		       COUNT(*) AS bookings,
		       COALESCE(SUM(seats), 0) AS seats,
		       COALESCE(SUM(total), 0) AS revenue,
		       COALESCE(AVG(total), 0)::float AS average_total
		FROM bookings
		WHERE event_id = $1`, eventID).
		Scan(&stats.EventID, &stats.Bookings, &stats.Seats, &stats.Revenue, &stats.AverageTotal)
	return stats, err
}
