#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T api python scripts/prepare_demo.py >/dev/null

token="$({ docker compose exec -T api python -c '
import httpx
response = httpx.post(
    "http://127.0.0.1:8000/auth/login",
    json={"email": "demo.admin@example.com", "password": "demo-password"},
)
response.raise_for_status()
print(response.json()["access_token"])
'; } | tr -d '\r')"

item_id="$({ docker compose exec -T api python -c '
import httpx
response = httpx.get("http://127.0.0.1:8000/menu/items")
response.raise_for_status()
print(response.json()[0]["id"])
'; } | tr -d '\r')"

LOCUST_ACCESS_TOKEN="$token" LOCUST_ITEM_ID="$item_id" \
  docker compose run --rm --build locust

docker compose run --rm --no-deps locust \
  python scripts/analyze_locust.py \
  results/lab10-current_stats.csv \
  docs/lab10-load-report.md

echo "Load report: docs/lab10-load-report.md"
