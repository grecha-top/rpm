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

	"github.com/jackc/pgx/v5/pgxpool"
)

type shardClient struct {
	shard sharding.Shard
	pool  *pgxpool.Pool
}

type statusAgg struct {
	Status string
	Count  int64
	Seats  int64
	Total  int64
}

type topBooking struct {
	ShardName string
	ID        int64
	UserID    int64
	EventID   int64
	Status    string
	Total     int64
	CreatedAt time.Time
}

func main() {
	shardURLs := flag.String("shard-urls", envOrDefault("SHARD_DATABASE_URLS", defaultShardURLs()), "comma-separated shard PostgreSQL URLs")
	shardCount := flag.Int("shards", 3, "number of active shards to query")
	limit := flag.Int("limit", 10, "global ORDER BY/LIMIT size")
	flag.Parse()

	ctx := context.Background()
	urls := splitCSV(*shardURLs)
	if len(urls) < *shardCount {
		log.Fatalf("need at least %d shard urls, got %d", *shardCount, len(urls))
	}

	clients := make([]shardClient, 0, *shardCount)
	shards := make([]sharding.Shard, 0, *shardCount)
	for i, url := range urls[:*shardCount] {
		shard := sharding.Shard{Name: fmt.Sprintf("shard-%d", i), URL: url}
		pool, err := pgxpool.New(ctx, url)
		if err != nil {
			log.Fatalf("connect %s: %v", shard.Name, err)
		}
		defer pool.Close()
		clients = append(clients, shardClient{shard: shard, pool: pool})
		shards = append(shards, shard)
	}

	router := sharding.NewModuloRouter(shards)
	userID, err := pickSampleUser(ctx, clients)
	if err != nil {
		log.Fatalf("pick sample user: %v", err)
	}

	printHeader("Lab 06: queries after sharding")
	fmt.Printf("Entity: bookings\n")
	fmt.Printf("Shard key: user_id\n")
	fmt.Printf("Active shards: %d\n", len(clients))
	fmt.Printf("Sample user_id: %d\n\n", userID)

	if err := runSingleShardQuery(ctx, clients, router, userID); err != nil {
		log.Fatalf("single shard query: %v", err)
	}
	if err := runDistributedAggregation(ctx, clients); err != nil {
		log.Fatalf("distributed aggregation: %v", err)
	}
	if err := runDistributedTopN(ctx, clients, *limit); err != nil {
		log.Fatalf("distributed top n: %v", err)
	}
}

func runSingleShardQuery(ctx context.Context, clients []shardClient, router sharding.ModuloRouter, userID int64) error {
	printHeader("1. Single-shard query")
	target := router.ShardForKey(userID)
	client, ok := clientByName(clients, target.Name)
	if !ok {
		return fmt.Errorf("target shard %s not found", target.Name)
	}

	var count int64
	var total int64
	err := client.pool.QueryRow(ctx, `
		SELECT COUNT(*), COALESCE(SUM(total), 0)
		FROM bookings_sharded
		WHERE user_id = $1`, userID).Scan(&count, &total)
	if err != nil {
		return err
	}

	fmt.Printf("Query: bookings by user_id = %d\n", userID)
	fmt.Printf("Router result: %s\n", target.Name)
	fmt.Printf("SQL executed only on %s\n", target.Name)
	fmt.Printf("Result: count=%d total=%d\n\n", count, total)
	return nil
}

func runDistributedAggregation(ctx context.Context, clients []shardClient) error {
	printHeader("2. Distributed aggregation")
	merged := map[string]statusAgg{}

	for _, client := range clients {
		rows, err := client.pool.Query(ctx, `
			SELECT status, COUNT(*), COALESCE(SUM(seats), 0), COALESCE(SUM(total), 0)
			FROM bookings_sharded
			GROUP BY status
			ORDER BY status`)
		if err != nil {
			return fmt.Errorf("%s aggregation: %w", client.shard.Name, err)
		}

		fmt.Printf("%s partial result:\n", client.shard.Name)
		for rows.Next() {
			var item statusAgg
			if err := rows.Scan(&item.Status, &item.Count, &item.Seats, &item.Total); err != nil {
				rows.Close()
				return err
			}
			fmt.Printf("  %s count=%d seats=%d total=%d\n", item.Status, item.Count, item.Seats, item.Total)
			current := merged[item.Status]
			current.Status = item.Status
			current.Count += item.Count
			current.Seats += item.Seats
			current.Total += item.Total
			merged[item.Status] = current
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()
	}

	fmt.Printf("Merged in backend:\n")
	for _, item := range sortedAgg(merged) {
		fmt.Printf("  %s count=%d seats=%d total=%d\n", item.Status, item.Count, item.Seats, item.Total)
	}
	fmt.Println()
	return nil
}

func runDistributedTopN(ctx context.Context, clients []shardClient, limit int) error {
	printHeader("3. Distributed ORDER BY/LIMIT")
	candidates := make([]topBooking, 0, len(clients)*limit)

	for _, client := range clients {
		rows, err := client.pool.Query(ctx, `
			SELECT id, user_id, event_id, status, total, created_at
			FROM bookings_sharded
			ORDER BY created_at DESC
			LIMIT $1`, limit)
		if err != nil {
			return fmt.Errorf("%s top-n: %w", client.shard.Name, err)
		}

		count := 0
		for rows.Next() {
			var item topBooking
			item.ShardName = client.shard.Name
			if err := rows.Scan(&item.ID, &item.UserID, &item.EventID, &item.Status, &item.Total, &item.CreatedAt); err != nil {
				rows.Close()
				return err
			}
			candidates = append(candidates, item)
			count++
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()
		fmt.Printf("%s returned local top %d\n", client.shard.Name, count)
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].CreatedAt.After(candidates[j].CreatedAt)
	})
	if len(candidates) > limit {
		candidates = candidates[:limit]
	}

	fmt.Printf("Backend merged candidates and selected global top %d:\n", limit)
	for i, item := range candidates {
		fmt.Printf(
			"  #%d %s booking_id=%d user_id=%d status=%s total=%d created_at=%s\n",
			i+1,
			item.ShardName,
			item.ID,
			item.UserID,
			item.Status,
			item.Total,
			item.CreatedAt.Format(time.RFC3339),
		)
	}
	fmt.Println()
	return nil
}

func pickSampleUser(ctx context.Context, clients []shardClient) (int64, error) {
	var bestUserID int64
	var bestCount int64

	for _, client := range clients {
		var userID int64
		var count int64
		err := client.pool.QueryRow(ctx, `
			SELECT user_id, COUNT(*) AS bookings
			FROM bookings_sharded
			GROUP BY user_id
			ORDER BY bookings DESC, user_id
			LIMIT 1`).Scan(&userID, &count)
		if err != nil {
			return 0, fmt.Errorf("%s sample user: %w", client.shard.Name, err)
		}
		if count > bestCount {
			bestUserID = userID
			bestCount = count
		}
	}

	if bestUserID == 0 {
		return 0, fmt.Errorf("no bookings found")
	}
	return bestUserID, nil
}

func clientByName(clients []shardClient, name string) (shardClient, bool) {
	for _, client := range clients {
		if client.shard.Name == name {
			return client, true
		}
	}
	return shardClient{}, false
}

func sortedAgg(items map[string]statusAgg) []statusAgg {
	result := make([]statusAgg, 0, len(items))
	for _, item := range items {
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Status < result[j].Status
	})
	return result
}

func printHeader(title string) {
	fmt.Println(strings.Repeat("=", len(title)))
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", len(title)))
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
	}, ",")
}
