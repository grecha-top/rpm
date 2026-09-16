package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type alert struct {
	ID        int64
	TableName string
	Status    string
	Message   string
	CreatedAt time.Time
}

func main() {
	databaseURL := flag.String("database-url", envOrDefault("LOCAL_DATABASE_URL", "postgres://postgres:postgres@127.0.0.1:5432/rpm?sslmode=disable"), "PostgreSQL URL")
	token := flag.String("telegram-token", os.Getenv("TELEGRAM_BOT_TOKEN"), "Telegram bot token")
	chatID := flag.String("telegram-chat-id", os.Getenv("TELEGRAM_CHAT_ID"), "Telegram chat id")
	limit := flag.Int("limit", envIntOrDefault("TELEGRAM_ALERT_LIMIT", 20), "max alerts per run")
	loop := flag.Bool("loop", envBoolOrDefault("TELEGRAM_ALERT_LOOP", false), "poll forever")
	interval := flag.Duration("interval", envDurationOrDefault("TELEGRAM_ALERT_INTERVAL", 30*time.Second), "poll interval in loop mode")
	dryRun := flag.Bool("dry-run", false, "print messages without sending them")
	flag.Parse()

	if *token == "" && !*dryRun {
		log.Fatal("TELEGRAM_BOT_TOKEN is required")
	}
	if *chatID == "" && !*dryRun {
		log.Fatal("TELEGRAM_CHAT_ID is required")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, *databaseURL)
	if err != nil {
		log.Fatalf("connect db: %v", err)
	}
	defer pool.Close()

	if err := setupState(ctx, pool); err != nil {
		log.Fatalf("setup telegram alert state: %v", err)
	}

	for {
		if err := sendPending(ctx, pool, *token, *chatID, *limit, *dryRun); err != nil {
			log.Printf("send pending alerts: %v", err)
		}
		if !*loop {
			return
		}
		time.Sleep(*interval)
	}
}

func setupState(ctx context.Context, pool *pgxpool.Pool) error {
	_, err := pool.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS lab03.telegram_alert_state (
			id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
			last_sent_alert_id BIGINT NOT NULL DEFAULT 0,
			updated_at TIMESTAMP NOT NULL DEFAULT now()
		);

		INSERT INTO lab03.telegram_alert_state (id, last_sent_alert_id)
		VALUES (TRUE, 0)
		ON CONFLICT (id) DO NOTHING;
	`)
	return err
}

func sendPending(ctx context.Context, pool *pgxpool.Pool, token string, chatID string, limit int, dryRun bool) error {
	lastID, err := lastSentID(ctx, pool)
	if err != nil {
		return err
	}

	alerts, err := loadAlerts(ctx, pool, lastID, limit)
	if err != nil {
		return err
	}
	if len(alerts) == 0 {
		log.Print("no pending alerts")
		return nil
	}

	for _, item := range alerts {
		text := formatAlert(item)
		if dryRun {
			log.Printf("[dry-run] %s", text)
			log.Printf("[dry-run] alert id=%d status=%s was not marked as sent", item.ID, item.Status)
		} else if err := sendTelegram(ctx, token, chatID, text); err != nil {
			return err
		} else {
			if err := saveLastSentID(ctx, pool, item.ID); err != nil {
				return err
			}
			log.Printf("sent alert id=%d status=%s", item.ID, item.Status)
		}
	}
	return nil
}

func lastSentID(ctx context.Context, pool *pgxpool.Pool) (int64, error) {
	var id int64
	err := pool.QueryRow(ctx, `SELECT last_sent_alert_id FROM lab03.telegram_alert_state WHERE id = TRUE`).Scan(&id)
	return id, err
}

func loadAlerts(ctx context.Context, pool *pgxpool.Pool, afterID int64, limit int) ([]alert, error) {
	rows, err := pool.Query(ctx, `
		SELECT id, table_name, status, message, created_at
		FROM lab03.partition_alerts
		WHERE id > $1
		ORDER BY id
		LIMIT $2`, afterID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []alert
	for rows.Next() {
		var item alert
		if err := rows.Scan(&item.ID, &item.TableName, &item.Status, &item.Message, &item.CreatedAt); err != nil {
			return nil, err
		}
		result = append(result, item)
	}
	return result, rows.Err()
}

func saveLastSentID(ctx context.Context, pool *pgxpool.Pool, id int64) error {
	_, err := pool.Exec(ctx, `
		UPDATE lab03.telegram_alert_state
		SET last_sent_alert_id = $1, updated_at = now()
		WHERE id = TRUE`, id)
	return err
}

func sendTelegram(ctx context.Context, token string, chatID string, text string) error {
	payload := map[string]string{
		"chat_id": chatID,
		"text":    text,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", token)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("telegram api status: %s", resp.Status)
	}
	return nil
}

func formatAlert(item alert) string {
	icon := "INFO"
	switch strings.ToUpper(item.Status) {
	case "CRITICAL":
		icon = "CRITICAL"
	case "OK":
		icon = "RECOVERY"
	}

	return fmt.Sprintf(
		"[%s] PostgreSQL partition alert\nTable: %s\nStatus: %s\nAlert ID: %d\nCreated at: %s\n\n%s",
		icon,
		item.TableName,
		item.Status,
		item.ID,
		item.CreatedAt.Format(time.RFC3339),
		item.Message,
	)
}

func envOrDefault(key string, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func envIntOrDefault(key string, fallback int) int {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envBoolOrDefault(key string, fallback bool) bool {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envDurationOrDefault(key string, fallback time.Duration) time.Duration {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := time.ParseDuration(value)
	if err != nil {
		return fallback
	}
	return parsed
}
