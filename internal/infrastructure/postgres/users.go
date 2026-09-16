package postgres

import (
	"context"

	"rpm/internal/domain"
)

func (r *Repository) CreateUser(ctx context.Context, user domain.User) (domain.User, error) {
	row := r.db.QueryRow(ctx, `
		INSERT INTO users (email, full_name) VALUES ($1, $2)
		RETURNING id, email, full_name, created_at, updated_at`,
		user.Email, user.FullName)
	return scanUser(row)
}

func (r *Repository) ListUsers(ctx context.Context) ([]domain.User, error) {
	rows, err := r.readDB.Query(ctx, `SELECT id, email, full_name, created_at, updated_at FROM users ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []domain.User
	for rows.Next() {
		user, err := scanUser(rows)
		if err != nil {
			return nil, err
		}
		users = append(users, user)
	}
	return users, rows.Err()
}

func (r *Repository) GetUser(ctx context.Context, id int64) (domain.User, error) {
	user, err := scanUser(r.readDB.QueryRow(ctx, `SELECT id, email, full_name, created_at, updated_at FROM users WHERE id=$1`, id))
	return user, normalizeNoRows(err)
}

func (r *Repository) UpdateUser(ctx context.Context, id int64, user domain.User) (domain.User, error) {
	row := r.db.QueryRow(ctx, `
		UPDATE users SET email=$1, full_name=$2, updated_at=now()
		WHERE id=$3
		RETURNING id, email, full_name, created_at, updated_at`,
		user.Email, user.FullName, id)
	updated, err := scanUser(row)
	return updated, normalizeNoRows(err)
}

func (r *Repository) DeleteUser(ctx context.Context, id int64) error {
	tag, err := r.db.Exec(ctx, `DELETE FROM users WHERE id=$1`, id)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return domain.ErrNotFound
	}
	return nil
}
