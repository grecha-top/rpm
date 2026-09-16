package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"sort"
	"strings"
	"time"

	"rpm/internal/sharding"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type bookingRow struct {
	ID        int64
	UserID    int64
	EventID   int64
	Status    string
	Seats     int
	Total     int64
	CreatedAt time.Time
	UpdatedAt time.Time
}

func main() {
	sourceURL := flag.String("source-url", envOrDefault("LOCAL_DATABASE_URL", "postgres://postgres:postgres@127.0.0.1:5432/rpm?sslmode=disable"), "source PostgreSQL URL")
	shardURLs := flag.String("shard-urls", envOrDefault("SHARD_DATABASE_URLS", defaultShardURLs()), "comma-separated shard PostgreSQL URLs")
	rowsLimit := flag.Int("rows", 100000, "number of bookings to route")
	virtualNodes := flag.Int("virtual-nodes", 128, "virtual nodes per shard for consistent hashing")
	flag.Parse()

	ctx := context.Background()
	urls := splitCSV(*shardURLs)
	if len(urls) < 4 {
		log.Fatalf("need at least 4 shard urls, got %d", len(urls))
	}

	source, err := pgxpool.New(ctx, *sourceURL)
	if err != nil {
		log.Fatalf("connect source: %v", err)
	}
	defer source.Close()

	shards4 := make([]sharding.Shard, 0, 4)
	pools := make(map[string]*pgxpool.Pool, 4)
	for i, url := range urls[:4] {
		shard := sharding.Shard{Name: fmt.Sprintf("shard-%d", i), URL: url}
		shards4 = append(shards4, shard)

		pool, err := pgxpool.New(ctx, url)
		if err != nil {
			log.Fatalf("connect %s: %v", shard.Name, err)
		}
		defer pool.Close()
		pools[shard.Name] = pool
	}

	for _, shard := range shards4 {
		if err := setupShard(ctx, pools[shard.Name]); err != nil {
			log.Fatalf("setup %s: %v", shard.Name, err)
		}
	}

	bookings, err := loadBookings(ctx, source, *rowsLimit)
	if err != nil {
		log.Fatalf("load bookings: %v", err)
	}
	if len(bookings) == 0 {
		log.Fatal("source bookings table is empty")
	}

	shards3 := shards4[:3]
	mod3 := sharding.NewModuloRouter(shards3)
	mod4 := sharding.NewModuloRouter(shards4)
	ring3 := sharding.NewConsistentHashRouter(shards3, *virtualNodes)
	ring4 := sharding.NewConsistentHashRouter(shards4, *virtualNodes)

	if err := distributeModulo(ctx, pools, mod3, bookings); err != nil {
		log.Fatalf("distribute modulo: %v", err)
	}

	keys := make([]int64, 0, len(bookings))
	for _, booking := range bookings {
		keys = append(keys, booking.UserID)
	}

	actualCounts, err := countShards(ctx, pools, shards3)
	if err != nil {
		log.Fatalf("count shards: %v", err)
	}
	moduloMoved := sharding.MovedCount(keys, mod3, mod4)
	consistentMoved := sharding.MovedCount(keys, ring3, ring4)

	printReport(len(bookings), actualCounts, moduloMoved, consistentMoved, sharding.Distribution(keys, ring3))
}

func setupShard(ctx context.Context, pool *pgxpool.Pool) error {
	_, err := pool.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS bookings_sharded (
			id BIGINT PRIMARY KEY,
			user_id BIGINT NOT NULL,
			event_id BIGINT NOT NULL,
			status TEXT NOT NULL,
			seats INTEGER NOT NULL,
			total BIGINT NOT NULL,
			created_at TIMESTAMPTZ NOT NULL,
			updated_at TIMESTAMPTZ NOT NULL
		);
		CREATE INDEX IF NOT EXISTS idx_bookings_sharded_user_id ON bookings_sharded(user_id);
		TRUNCATE bookings_sharded;
	`)
	return err
}

func loadBookings(ctx context.Context, source *pgxpool.Pool, limit int) ([]bookingRow, error) {
	rows, err := source.Query(ctx, `
		SELECT id, user_id, event_id, status, seats, total, created_at, updated_at
		FROM bookings
		ORDER BY id
		LIMIT $1`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var bookings []bookingRow
	for rows.Next() {
		var booking bookingRow
		if err := rows.Scan(
			&booking.ID,
			&booking.UserID,
			&booking.EventID,
			&booking.Status,
			&booking.Seats,
			&booking.Total,
			&booking.CreatedAt,
			&booking.UpdatedAt,
		); err != nil {
			return nil, err
		}
		bookings = append(bookings, booking)
	}
	return bookings, rows.Err()
}

func distributeModulo(ctx context.Context, pools map[string]*pgxpool.Pool, router sharding.ModuloRouter, bookings []bookingRow) error {
	byShard := make(map[string][]bookingRow)
	for _, booking := range bookings {
		shard := router.ShardForKey(booking.UserID)
		byShard[shard.Name] = append(byShard[shard.Name], booking)
	}

	for shardName, rows := range byShard {
		pool := pools[shardName]
		if pool == nil {
			return fmt.Errorf("pool for %s not found", shardName)
		}
		_, err := pool.CopyFrom(
			ctx,
			pgx.Identifier{"bookings_sharded"},
			[]string{"id", "user_id", "event_id", "status", "seats", "total", "created_at", "updated_at"},
			pgx.CopyFromSlice(len(rows), func(i int) ([]any, error) {
				row := rows[i]
				return []any{row.ID, row.UserID, row.EventID, row.Status, row.Seats, row.Total, row.CreatedAt, row.UpdatedAt}, nil
			}),
		)
		if err != nil {
			return fmt.Errorf("copy %s: %w", shardName, err)
		}
	}
	return nil
}

func countShards(ctx context.Context, pools map[string]*pgxpool.Pool, shards []sharding.Shard) (map[string]int, error) {
	counts := make(map[string]int)
	for _, shard := range shards {
		var count int
		if err := pools[shard.Name].QueryRow(ctx, `SELECT COUNT(*) FROM bookings_sharded`).Scan(&count); err != nil {
			return nil, err
		}
		counts[shard.Name] = count
	}
	return counts, nil
}

func printReport(total int, moduloCounts map[string]int, moduloMoved int, consistentMoved int, ringDistribution map[string]int) {
	fmt.Printf("Lab 05 sharding report\n")
	fmt.Printf("Entity: bookings\n")
	fmt.Printf("Shard key: user_id\n")
	fmt.Printf("Total records: %d\n\n", total)

	fmt.Printf("hash(user_id) %% 3 distribution loaded to PostgreSQL shards:\n")
	printCounts(moduloCounts, total)

	fmt.Printf("\nConsistent hashing distribution with 3 shards:\n")
	printCounts(ringDistribution, total)

	fmt.Printf("\n3 -> 4 shards movement:\n")
	fmt.Printf("hash(key) %% N moved: %d records (%.2f%%)\n", moduloMoved, percent(moduloMoved, total))
	fmt.Printf("Consistent hashing moved: %d records (%.2f%%)\n", consistentMoved, percent(consistentMoved, total))
}

func printCounts(counts map[string]int, total int) {
	names := make([]string, 0, len(counts))
	for name := range counts {
		names = append(names, name)
	}
	sort.Strings(names)

	for _, name := range names {
		count := counts[name]
		fmt.Printf("%s -> %d records (%.2f%%)\n", name, count, percent(count, total))
	}
}

func percent(value int, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(value) * 100 / float64(total)
}

func splitCSV(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part != "" {
			result = append(result, part)
		}
	}
	return result
}

func envOrDefault(key string, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func defaultShardURLs() string {
	return strings.Join([]string{
		"postgres://postgres:postgres@127.0.0.1:55440/rpm?sslmode=disable",
		"postgres://postgres:postgres@127.0.0.1:55441/rpm?sslmode=disable",
		"postgres://postgres:postgres@127.0.0.1:55442/rpm?sslmode=disable",
		"postgres://postgres:postgres@127.0.0.1:55443/rpm?sslmode=disable",
	}, ",")
}
