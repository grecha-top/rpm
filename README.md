# Event Booking API

Backend-сервис для бронирования мест на мероприятия. Проект подготовлен как база для модуля по масштабированию PostgreSQL: сначала обычная БД, затем анализ запросов, индексы, партиционирование, реплики и шардирование.

## Стек

- Go
- chi
- pgx
- PostgreSQL
- goose
- Docker Compose
- lol
## Запуск

Настройки приложения и PostgreSQL лежат в `.env`. Для первого запуска можно взять значения из `.env.example`.

```bash
docker compose up --build
```

API будет доступен на `http://localhost:8080`.

Проверка:

```bash
curl http://localhost:8080/health
```

## Архитектура

```text
Client
  -> internal/httpapi
  -> internal/application
  -> internal/domain
  -> internal/infrastructure/postgres
  -> PostgreSQL
```

Код разложен ближе к DDD:

- `internal/domain` - доменные модели, ошибки и интерфейс репозитория.
- `internal/application` - сервисный слой/use cases, зависит от интерфейса домена.
- `internal/httpapi` - transport-слой HTTP, разбит по ресурсам: users, venues, events, categories, bookings.
- `internal/infrastructure/postgres` - реализация репозитория на PostgreSQL, SQL разбит по сущностям.
- `internal/db` - подключение к PostgreSQL и запуск миграций.
- `internal/sharding` - shard router для лабораторной №5.

## Схема БД

- `users` - пользователи.
- `venues` - площадки мероприятий.
- `events` - мероприятия, связаны с `venues`.
- `categories` - категории мероприятий.
- `event_categories` - many-to-many связь `events` и `categories`.
- `bookings` - бронирования, связаны с `users` и `events`.

Основная сущность для масштабирования: `bookings`.

Почему она подходит: количество бронирований естественно быстро растет, по ней есть фильтрация по статусу, пользователю, мероприятию и диапазону `created_at`. Позже эта таблица удобна для экспериментов с индексами, партиционированием по времени и шардированием.

## Основные endpoints

- `GET /health`
- `GET /openapi.json`
- `GET|POST /api/users`
- `GET|PUT|DELETE /api/users/{id}`
- `GET /api/users/{id}/bookings`
- `GET|POST /api/venues`
- `GET|PUT|DELETE /api/venues/{id}`
- `GET /api/venues/{id}/events`
- `GET|POST /api/events`
- `GET|PUT|DELETE /api/events/{id}`
- `GET /api/events/{id}/bookings`
- `GET /api/events/{id}/stats`
- `POST /api/events/{id}/categories/{categoryID}`
- `GET|POST /api/categories`
- `GET|PUT|DELETE /api/categories/{id}`
- `GET /api/categories/{id}/events`
- `GET|POST /api/bookings`
- `GET|PUT|DELETE /api/bookings/{id}`

Примеры тел для `POST` и `PUT` запросов лежат в `docs/request-body-examples.md`.

## Pagination и Filtering

Пример:

```bash
curl "http://localhost:8080/api/bookings?page=1&pageSize=20&status=PAID&sort=-created_at"
```

Поддерживаются параметры:

- `page`
- `pageSize`
- `status`
- `user_id`
- `event_id`
- `from`
- `to`
- `sort=created_at`
- `sort=-created_at`

## Сложные SQL-запросы

JOIN-запрос 1: бронирования пользователя с пользователем, мероприятием и площадкой.

```sql
SELECT b.id, b.user_id, b.event_id, b.status, b.seats, b.total, b.created_at, b.updated_at,
       u.email, e.title, v.name, v.city, e.starts_at
FROM bookings b
JOIN users u ON u.id = b.user_id
JOIN events e ON e.id = b.event_id
JOIN venues v ON v.id = e.venue_id
WHERE b.user_id = $1
ORDER BY b.created_at DESC;
```

JOIN-запрос 2: мероприятия категории с площадкой, всеми категориями и количеством бронирований.

```sql
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
ORDER BY e.starts_at DESC;
```

Агрегирующий запрос: статистика бронирований по мероприятию.

```sql
SELECT $1::bigint AS event_id,
       COUNT(*) AS bookings,
       COALESCE(SUM(seats), 0) AS seats,
       COALESCE(SUM(total), 0) AS revenue,
       COALESCE(AVG(total), 0)::float AS average_total
FROM bookings
WHERE event_id = $1;
```

## Генерация данных

После запуска PostgreSQL и применения миграций можно сгенерировать данные:

```bash
set -a
source .env
set +a
DATABASE_URL="$LOCAL_DATABASE_URL" \
go run ./scripts/generate_data.go --users 100000 --venues 1000 --events 100000 --bookings 1000000
```

Данные пишутся напрямую в PostgreSQL, а не через API.

## Лабораторная работа №1

Материалы по индексам и `EXPLAIN ANALYZE`:

- отчет: `docs/lab-01-indexes.md`
- подготовка тестовой таблицы: `scripts/lab01_orders_setup.sql`
- эксперименты на тестовой таблице: `scripts/lab01_orders_experiments.sql`
- эксперименты на таблице сервиса `bookings`: `scripts/lab01_service_explain.sql`

Запуск учебной части:

```bash
set -a
source .env
set +a
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_setup.sql
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_experiments.sql | tee docs/lab-01-orders-output.txt
```

Запуск части по сервису:

```bash
DATABASE_URL="$LOCAL_DATABASE_URL" \
go run ./scripts/generate_data.go --users 100000 --venues 1000 --events 100000 --bookings 1000000

psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-before-output.txt
# применить migrations/202609120001_lab01_booking_indexes.sql
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-after-output.txt
```

## Лабораторная работа №2

Материалы по росту данных и случаям, когда индексов недостаточно:

- отчет: `docs/lab-02-growth.md`
- экспериментальная таблица: `scripts/lab02_events_setup.sql`
- генерация событий: `scripts/lab02_events_insert.sql`
- измерения событий: `scripts/lab02_events_measure.sql`
- индексы событий: `scripts/lab02_events_create_indexes.sql`
- стоимость вставки: `scripts/lab02_insert_cost.sql`
- измерения `bookings`: `scripts/lab02_bookings_measure.sql`
- рост `bookings` до целевого объема: `scripts/lab02_bookings_insert_to_target.sql`

## Лабораторная работа №3

Материалы по партиционированию:

- отчет: `docs/lab-03-partitioning.md`
- подготовка схемы и функций: `scripts/lab03_partitioning_setup.sql`
- эксперименты: `scripts/lab03_partitioning_experiments.sql`
- пример расписания pg_cron: `scripts/lab03_pg_cron.sql`
- вывод: `docs/lab-03-partitioning-output.txt`

Запуск:

```bash
set -a
source .env
set +a

psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_partitioning_setup.sql
psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_partitioning_experiments.sql \
  | tee docs/lab-03-partitioning-output.txt
psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_pg_cron.sql
```

В лабораторной реализованы `RANGE`, `LIST`, `HASH`, индексы на партиционированных таблицах, автоматическое создание будущих партиций, health-check и alert/recovery.
Для отправки partition alerts в Telegram добавлен worker `cmd/lab03-alertbot`.

Запуск Telegram alert worker:

```bash
set -a
source .env
set +a

GOCACHE="$PWD/.gocache" go run ./cmd/lab03-alertbot
```

Проверка без отправки:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab03-alertbot -dry-run
```

Просмотр активных cron-задач:

```sql
SELECT jobid, jobname, schedule, command, active
FROM cron.job
ORDER BY jobid;
```

Удаление cron-задачи:

```sql
SELECT cron.unschedule('lab03-create-events-partitions');
SELECT cron.unschedule('lab03-check-events-partitions');
```

## Лабораторная работа №4

Материалы по read scaling:

- отчет: `docs/lab-04-read-scaling.md`
- primary/replica стенд: `docker-compose.replica.yml`
- init-скрипт primary: `docker/postgres/primary-init/01-replication-user.sh`
- вывод проверок: `docs/lab-04-replication-output.txt`

Запуск primary и replica:

```bash
docker compose -f docker-compose.replica.yml up -d
```

Подключение сервиса к primary и replica:

```bash
PORT=18081 \
DATABASE_URL="postgres://postgres:postgres@127.0.0.1:55432/rpm?sslmode=disable" \
REPLICA_DATABASE_URL="postgres://postgres:postgres@127.0.0.1:55433/rpm?sslmode=disable" \
go run ./cmd/api
```

Primary доступна на `localhost:55432`, replica - на `localhost:55433`. Пользователь и пароль для приложения: `postgres` / `postgres`.

## Лабораторная работа №5

Материалы по шардированию:

- отчет: `docs/lab-05-sharding.md`
- вывод эксперимента: `docs/lab-05-sharding-output.txt`
- shard PostgreSQL стенд: `docker-compose.shards.yml`
- router: `internal/sharding/router.go`
- runner лабораторной: `cmd/lab05/main.go`

Запуск shard PostgreSQL:

```bash
docker compose -f docker-compose.shards.yml up -d
```

Запуск эксперимента на 100000 бронирований:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab05 -rows 100000 \
  | tee docs/lab-05-sharding-output.txt
```

Шарды доступны на `localhost:55440`, `localhost:55441`, `localhost:55442`, `localhost:55443`. Пользователь и пароль: `postgres` / `postgres`, база `rpm`.

## Лабораторная работа №6

Материалы по запросам и архитектуре после шардирования:

- отчет: `docs/lab-06-after-sharding.md`
- вывод/статус runner: `docs/lab-06-after-sharding-output.txt`
- runner лабораторной: `cmd/lab06/main.go`
- shard router: `internal/sharding/router.go`

Запуск стенда:

```bash
docker compose -f docker-compose.shards.yml up -d
```

Если данные на shard пустые, сначала загрузить лабораторную №5:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab05 -rows 100000 \
  | tee docs/lab-05-sharding-output.txt
```

Запуск анализа запросов после шардирования:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab06 -limit 10 \
  | tee docs/lab-06-after-sharding-output.txt
```
