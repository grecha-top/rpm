package postgres

import (
	"context"

	"rpm/internal/domain"
)

func (r *Repository) CreateVenue(ctx context.Context, venue domain.Venue) (domain.Venue, error) {
	row := r.db.QueryRow(ctx, `
		INSERT INTO venues (name, city, address, capacity) VALUES ($1, $2, $3, $4)
		RETURNING id, name, city, address, capacity, created_at, updated_at`,
		venue.Name, venue.City, venue.Address, venue.Capacity)
	return scanVenue(row)
}

func (r *Repository) ListVenues(ctx context.Context) ([]domain.Venue, error) {
	rows, err := r.readDB.Query(ctx, `SELECT id, name, city, address, capacity, created_at, updated_at FROM venues ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var venues []domain.Venue
	for rows.Next() {
		venue, err := scanVenue(rows)
		if err != nil {
			return nil, err
		}
		venues = append(venues, venue)
	}
	return venues, rows.Err()
}

func (r *Repository) GetVenue(ctx context.Context, id int64) (domain.Venue, error) {
	venue, err := scanVenue(r.readDB.QueryRow(ctx, `SELECT id, name, city, address, capacity, created_at, updated_at FROM venues WHERE id=$1`, id))
	return venue, normalizeNoRows(err)
}

func (r *Repository) UpdateVenue(ctx context.Context, id int64, venue domain.Venue) (domain.Venue, error) {
	row := r.db.QueryRow(ctx, `
		UPDATE venues SET name=$1, city=$2, address=$3, capacity=$4, updated_at=now()
		WHERE id=$5
		RETURNING id, name, city, address, capacity, created_at, updated_at`,
		venue.Name, venue.City, venue.Address, venue.Capacity, id)
	updated, err := scanVenue(row)
	return updated, normalizeNoRows(err)
}

func (r *Repository) DeleteVenue(ctx context.Context, id int64) error {
	tag, err := r.db.Exec(ctx, `DELETE FROM venues WHERE id=$1`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *Repository) VenueEvents(ctx context.Context, venueID int64) ([]domain.Event, error) {
	rows, err := r.readDB.Query(ctx, `SELECT id, venue_id, title, status, starts_at, base_price, created_at, updated_at FROM events WHERE venue_id=$1 ORDER BY starts_at`, venueID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanEventRows(rows)
}
