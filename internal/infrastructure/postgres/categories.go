package postgres

import (
	"context"

	"rpm/internal/domain"
)

func (r *Repository) CreateCategory(ctx context.Context, category domain.Category) (domain.Category, error) {
	row := r.db.QueryRow(ctx, `INSERT INTO categories (name) VALUES ($1) RETURNING id, name, created_at`, category.Name)
	return scanCategory(row)
}

func (r *Repository) ListCategories(ctx context.Context) ([]domain.Category, error) {
	rows, err := r.readDB.Query(ctx, `SELECT id, name, created_at FROM categories ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var categories []domain.Category
	for rows.Next() {
		category, err := scanCategory(rows)
		if err != nil {
			return nil, err
		}
		categories = append(categories, category)
	}
	return categories, rows.Err()
}

func (r *Repository) GetCategory(ctx context.Context, id int64) (domain.Category, error) {
	category, err := scanCategory(r.readDB.QueryRow(ctx, `SELECT id, name, created_at FROM categories WHERE id=$1`, id))
	return category, normalizeNoRows(err)
}

func (r *Repository) UpdateCategory(ctx context.Context, id int64, category domain.Category) (domain.Category, error) {
	row := r.db.QueryRow(ctx, `UPDATE categories SET name=$1 WHERE id=$2 RETURNING id, name, created_at`, category.Name, id)
	updated, err := scanCategory(row)
	return updated, normalizeNoRows(err)
}

func (r *Repository) DeleteCategory(ctx context.Context, id int64) error {
	tag, err := r.db.Exec(ctx, `DELETE FROM categories WHERE id=$1`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *Repository) CategoryEvents(ctx context.Context, categoryID int64) ([]domain.EventSummary, error) {
	rows, err := r.readDB.Query(ctx, `
		SELECT e.id, e.venue_id, e.title, e.status, e.starts_at, e.base_price, e.created_at, e.updated_at,
		       v.name, v.city,
		       COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), '{}') AS categories,
		       COUNT(DISTINCT b.id) AS bookings_count
		FROM events e
		JOIN venues v ON v.id = e.venue_id
		JOIN event_categories target_ec ON target_ec.event_id = e.id AND target_ec.category_id = $1
		LEFT JOIN event_categories ec ON ec.event_id = e.id
		LEFT JOIN categories c ON c.id = ec.category_id
		LEFT JOIN bookings b ON b.event_id = e.id
		GROUP BY e.id, v.id
		ORDER BY e.starts_at DESC`, categoryID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanEventSummaryRows(rows)
}
