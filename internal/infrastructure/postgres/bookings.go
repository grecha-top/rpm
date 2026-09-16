package postgres

import (
	"context"
	"fmt"

	"rpm/internal/domain"
)

func (r *Repository) CreateBooking(ctx context.Context, booking domain.Booking) (domain.Booking, error) {
	row := r.db.QueryRow(ctx, `
		INSERT INTO bookings (user_id, event_id, status, seats, total) VALUES ($1, $2, $3, $4, $5)
		RETURNING id, user_id, event_id, status, seats, total, created_at, updated_at`,
		booking.UserID, booking.EventID, booking.Status, booking.Seats, booking.Total)
	return scanBooking(row)
}

func (r *Repository) ListBookings(ctx context.Context, filter domain.BookingFilter) ([]domain.Booking, error) {
	where, args := bookingWhere(filter)
	sort := "created_at DESC"
	if filter.Sort == "created_at" {
		sort = "created_at ASC"
	}
	limit := filter.PageSize
	offset := (filter.Page - 1) * filter.PageSize
	args = append(args, limit, offset)

	query := fmt.Sprintf(`
		SELECT id, user_id, event_id, status, seats, total, created_at, updated_at
		FROM bookings
		%s
		ORDER BY %s
		LIMIT $%d OFFSET $%d`, where, sort, len(args)-1, len(args))

	rows, err := r.readDB.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var bookings []domain.Booking
	for rows.Next() {
		booking, err := scanBooking(rows)
		if err != nil {
			return nil, err
		}
		bookings = append(bookings, booking)
	}
	return bookings, rows.Err()
}

func (r *Repository) GetBooking(ctx context.Context, id int64) (domain.Booking, error) {
	booking, err := scanBooking(r.readDB.QueryRow(ctx, `SELECT id, user_id, event_id, status, seats, total, created_at, updated_at FROM bookings WHERE id=$1`, id))
	return booking, normalizeNoRows(err)
}

func (r *Repository) UpdateBooking(ctx context.Context, id int64, booking domain.Booking) (domain.Booking, error) {
	row := r.db.QueryRow(ctx, `
		UPDATE bookings SET user_id=$1, event_id=$2, status=$3, seats=$4, total=$5, updated_at=now()
		WHERE id=$6
		RETURNING id, user_id, event_id, status, seats, total, created_at, updated_at`,
		booking.UserID, booking.EventID, booking.Status, booking.Seats, booking.Total, id)
	updated, err := scanBooking(row)
	return updated, normalizeNoRows(err)
}

func (r *Repository) DeleteBooking(ctx context.Context, id int64) error {
	tag, err := r.db.Exec(ctx, `DELETE FROM bookings WHERE id=$1`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *Repository) UserBookings(ctx context.Context, userID int64) ([]domain.BookingDetails, error) {
	rows, err := r.readDB.Query(ctx, `
		SELECT b.id, b.user_id, b.event_id, b.status, b.seats, b.total, b.created_at, b.updated_at,
		       u.email, e.title, v.name, v.city, e.starts_at
		FROM bookings b
		JOIN users u ON u.id = b.user_id
		JOIN events e ON e.id = b.event_id
		JOIN venues v ON v.id = e.venue_id
		WHERE b.user_id = $1
		ORDER BY b.created_at DESC`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanBookingDetailsRows(rows)
}
