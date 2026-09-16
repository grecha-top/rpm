package config

import "os"

type Config struct {
	Port          string
	DatabaseURL   string
	ReplicaURL    string
	MigrationsDir string
}

func Load() Config {
	return Config{
		Port:          getEnv("PORT", getEnv("APP_PORT", "8080")),
		DatabaseURL:   getEnv("DATABASE_URL", getEnv("LOCAL_DATABASE_URL", "")),
		ReplicaURL:    getEnv("REPLICA_DATABASE_URL", ""),
		MigrationsDir: getEnv("MIGRATIONS_DIR", "migrations"),
	}
}

func getEnv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
