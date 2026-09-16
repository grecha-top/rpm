package postgres

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Repository struct {
	db     *pgxpool.Pool
	readDB *pgxpool.Pool
}

func New(db *pgxpool.Pool) *Repository {
	return NewWithReadPool(db, db)
}

func NewWithReadPool(db, readDB *pgxpool.Pool) *Repository {
	if readDB == nil {
		readDB = db
	}
	return &Repository{db: db, readDB: readDB}
}

func (r *Repository) Ping(ctx context.Context) error {
	return r.db.Ping(ctx)
}
