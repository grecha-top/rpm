package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"math/rand/v2"
	"os"
	"time"

	"github.com/jackc/pgx/v5"
)

func main() {
	users := flag.Int("users", 1000, "number of users")
	venues := flag.Int("venues", 100, "number of venues")
	events := flag.Int("events", 5000, "number of events")
	bookings := flag.Int("bookings", 100000, "number of bookings")
	flag.Parse()

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		databaseURL = os.Getenv("LOCAL_DATABASE_URL")
	}
	if databaseURL == "" {
		log.Fatal("DATABASE_URL or LOCAL_DATABASE_URL must be set")
	}

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, databaseURL)
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close(ctx)

	insertUsers(ctx, conn, *users)
	insertVenues(ctx, conn, *venues)
	insertEvents(ctx, conn, *events, *venues)
	insertBookings(ctx, conn, *bookings, *users, *events)
	log.Printf("generated users=%d venues=%d events=%d bookings=%d", *users, *venues, *events, *bookings)
}

func insertUsers(ctx context.Context, conn *pgx.Conn, count int) {
	batch := &pgx.Batch{}
	for i := 1; i <= count; i++ {
		batch.Queue(`INSERT INTO users (email, full_name) VALUES ($1, $2) ON CONFLICT (email) DO NOTHING`,
			fmt.Sprintf("user%06d@example.com", i), fmt.Sprintf("User %06d", i))
	}
	sendBatch(ctx, conn, batch)
}

func insertVenues(ctx context.Context, conn *pgx.Conn, count int) {
	batch := &pgx.Batch{}
	for i := 1; i <= count; i++ {
		batch.Queue(`INSERT INTO venues (name, city, address, capacity) VALUES ($1, $2, $3, $4)`,
			fmt.Sprintf("Venue %04d", i), city(i), fmt.Sprintf("Address %04d", i), 200+rand.IntN(5000))
	}
	sendBatch(ctx, conn, batch)
}

func insertEvents(ctx context.Context, conn *pgx.Conn, count, venueCount int) {
	batch := &pgx.Batch{}
	base := time.Now()
	for i := 1; i <= count; i++ {
		batch.Queue(`INSERT INTO events (venue_id, title, status, starts_at, base_price) VALUES ($1, $2, $3, $4, $5)`,
			1+rand.IntN(venueCount), fmt.Sprintf("Event %06d", i), status([]string{"DRAFT", "PUBLISHED", "CANCELLED"}),
			base.Add(time.Duration(rand.IntN(365*24))*time.Hour), 1000+rand.Int64N(9000))
	}
	sendBatch(ctx, conn, batch)
}

func insertBookings(ctx context.Context, conn *pgx.Conn, count, userCount, eventCount int) {
	const chunk = 10000
	base := time.Now().AddDate(-1, 0, 0)
	for start := 0; start < count; start += chunk {
		batch := &pgx.Batch{}
		end := min(start+chunk, count)
		for i := start; i < end; i++ {
			seats := 1 + rand.IntN(5)
			total := int64(seats) * (1000 + rand.Int64N(9000))
			batch.Queue(`INSERT INTO bookings (user_id, event_id, status, seats, total, created_at) VALUES ($1, $2, $3, $4, $5, $6)`,
				1+rand.IntN(userCount), 1+rand.IntN(eventCount), status([]string{"PENDING", "PAID", "CANCELLED"}), seats, total,
				base.Add(time.Duration(rand.IntN(365*24))*time.Hour))
		}
		sendBatch(ctx, conn, batch)
		log.Printf("bookings inserted: %d/%d", end, count)
	}
}

func sendBatch(ctx context.Context, conn *pgx.Conn, batch *pgx.Batch) {
	results := conn.SendBatch(ctx, batch)
	defer results.Close()
	for i := 0; i < batch.Len(); i++ {
		if _, err := results.Exec(); err != nil {
			log.Fatal(err)
		}
	}
}

func city(i int) string {
	cities := []string{"Moscow", "Saint Petersburg", "Kazan", "Sochi", "Novosibirsk"}
	return cities[i%len(cities)]
}

func status(values []string) string {
	return values[rand.IntN(len(values))]
}
