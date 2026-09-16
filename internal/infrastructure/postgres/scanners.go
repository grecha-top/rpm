package postgres

import (
	"errors"

	"rpm/internal/domain"

	"github.com/jackc/pgx/v5"
)

type scanner interface {
	Scan(dest ...any) error
}

func scanUser(s scanner) (domain.User, error) {
	var user domain.User
	err := s.Scan(&user.ID, &user.Email, &user.FullName, &user.CreatedAt, &user.UpdatedAt)
	return user, err
}

func scanVenue(s scanner) (domain.Venue, error) {
	var venue domain.Venue
	err := s.Scan(&venue.ID, &venue.Name, &venue.City, &venue.Address, &venue.Capacity, &venue.CreatedAt, &venue.UpdatedAt)
	return venue, err
}

func scanEvent(s scanner) (domain.Event, error) {
	var event domain.Event
	err := s.Scan(&event.ID, &event.VenueID, &event.Title, &event.Status, &event.StartsAt, &event.BasePrice, &event.CreatedAt, &event.UpdatedAt)
	return event, err
}

func scanCategory(s scanner) (domain.Category, error) {
	var category domain.Category
	err := s.Scan(&category.ID, &category.Name, &category.CreatedAt)
	return category, err
}

func scanBooking(s scanner) (domain.Booking, error) {
	var booking domain.Booking
	err := s.Scan(&booking.ID, &booking.UserID, &booking.EventID, &booking.Status, &booking.Seats, &booking.Total, &booking.CreatedAt, &booking.UpdatedAt)
	return booking, err
}

func scanEventRows(rows pgx.Rows) ([]domain.Event, error) {
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

func scanBookingDetailsRows(rows pgx.Rows) ([]domain.BookingDetails, error) {
	var result []domain.BookingDetails
	for rows.Next() {
		var item domain.BookingDetails
		err := rows.Scan(
			&item.ID, &item.UserID, &item.EventID, &item.Status, &item.Seats, &item.Total, &item.CreatedAt, &item.UpdatedAt,
			&item.UserEmail, &item.EventTitle, &item.VenueName, &item.VenueCity, &item.StartsAt,
		)
		if err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	return result, rows.Err()
}

func scanEventSummaryRows(rows pgx.Rows) ([]domain.EventSummary, error) {
	var result []domain.EventSummary
	for rows.Next() {
		var item domain.EventSummary
		err := rows.Scan(
			&item.ID, &item.VenueID, &item.Title, &item.Status, &item.StartsAt, &item.BasePrice, &item.CreatedAt, &item.UpdatedAt,
			&item.VenueName, &item.VenueCity, &item.Categories, &item.BookingsCount,
		)
		if err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	return result, rows.Err()
}

func normalizeNoRows(err error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.ErrNotFound
	}
	return err
}
