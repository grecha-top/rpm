package postgres

import (
	"fmt"
	"strings"

	"rpm/internal/domain"
)

func bookingWhere(filter domain.BookingFilter) (string, []any) {
	clauses := make([]string, 0, 5)
	args := make([]any, 0, 5)
	add := func(query string, value any) {
		args = append(args, value)
		clauses = append(clauses, fmt.Sprintf(query, len(args)))
	}
	if filter.Status != "" {
		add("status = $%d", filter.Status)
	}
	if filter.UserID > 0 {
		add("user_id = $%d", filter.UserID)
	}
	if filter.EventID > 0 {
		add("event_id = $%d", filter.EventID)
	}
	if filter.From != nil {
		add("created_at >= $%d", *filter.From)
	}
	if filter.To != nil {
		add("created_at <= $%d", *filter.To)
	}
	if len(clauses) == 0 {
		return "", args
	}
	return "WHERE " + strings.Join(clauses, " AND "), args
}
