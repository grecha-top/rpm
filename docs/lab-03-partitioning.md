# Лабораторная работа №3. Партиционирование PostgreSQL

## Цель

Проверить разные виды партиционирования PostgreSQL, увидеть partition pruning в `EXPLAIN ANALYZE`, автоматизировать создание будущих партиций и применить подход к таблице сервиса.

Файлы:

- `scripts/lab03_partitioning_setup.sql` - создание схемы, партиций, функций и тестовых данных.
- `scripts/lab03_partitioning_experiments.sql` - запуск экспериментов и `EXPLAIN ANALYZE`.
- `scripts/lab03_pg_cron.sql` - пример расписания через `pg_cron`.
- `docs/lab-03-partitioning-output.txt` - полный вывод выполнения.

## Запуск

```bash
set -a
source .env
set +a

psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_partitioning_setup.sql
psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_partitioning_experiments.sql \
  > docs/lab-03-partitioning-output.txt
```

## RANGE по дате

Создана таблица `lab03.events`, партиционированная по `created_at`, и три партиции:

- `events_2026_09_09`: `2026-09-09 <= created_at < 2026-09-10`
- `events_2026_09_10`: `2026-09-10 <= created_at < 2026-09-11`
- `events_2026_09_11`: `2026-09-11 <= created_at < 2026-09-12`

Распределение 300000 строк:

```text
lab03.events_2026_09_09 | 100186
lab03.events_2026_09_10 |  99738
lab03.events_2026_09_11 | 100076
```

Ответы:

- `2026-09-10 12:00:00` попадет в `events_2026_09_10`.
- `2026-09-11 00:00:00` попадет в `events_2026_09_11`, потому что верхняя граница `TO` не включается.
- `2026-09-12 00:00:00` без отдельной партиции не вставится: PostgreSQL вернет ошибку `no partition of relation ... found for row`.

Запрос по диапазону даты:

```sql
SELECT COUNT(*)
FROM lab03.events
WHERE created_at >= '2026-09-10'
  AND created_at < '2026-09-11';
```

План использовал только одну партицию:

```text
Seq Scan on events_2026_09_10
Execution Time: 8.408 ms
```

Это и есть partition pruning: PostgreSQL исключил ненужные партиции на этапе планирования.

## Когда партиционирование не помогает

Запрос только по `event_type`:

```sql
SELECT COUNT(*)
FROM lab03.events
WHERE event_type = 'click';
```

План:

```text
Append
  Bitmap Heap Scan on events_2026_09_09
  Bitmap Heap Scan on events_2026_09_10
  Bitmap Heap Scan on events_2026_09_11
Execution Time: 14.816 ms
```

Даже при индексе по `event_type` PostgreSQL обязан пройти все партиции, потому что ключ партиционирования - `created_at`, а не `event_type`. Индекс ускоряет поиск внутри каждой партиции, но не дает pruning.

## RANGE по числу

Таблица `lab03.products` партиционирована по `price`:

- `products_cheap`: `0 <= price < 100`
- `products_medium`: `100 <= price < 1000`
- `products_expensive`: `1000 <= price < MAXVALUE`

Запрос `price >= 100 AND price < 500` сканировал только `products_medium`:

```text
Seq Scan on products_medium
Execution Time: 0.005 ms
```

## LIST

Таблица `lab03.customers` партиционирована по `customer_type`:

- `customers_b2c`
- `customers_b2b`
- `customers_enterprise`

Запрос `customer_type = 'B2B'` сканировал только `customers_b2b`.

Вставка значения `VIP` сначала завершилась ошибкой, потому что не было подходящей партиции. После добавления `DEFAULT`-партиции строка попала в `customers_default`.

## HASH

Таблица `lab03.user_events` партиционирована по `user_id` на 4 hash-партиции.

Распределение 200000 строк:

```text
lab03.user_events_0 | 50266
lab03.user_events_1 | 49897
lab03.user_events_2 | 50023
lab03.user_events_3 | 49814
```

Hash-партиционирование подходит, когда данные нужно равномерно распределить по ключу, но нет естественных диапазонов.

## Выбор стратегий

- Таблица заказов по дате: `RANGE(created_at)`, потому что основные запросы обычно идут по периодам, а старые данные удобно архивировать целыми партициями.
- Пользователи по типу клиента: `LIST(customer_type)`, потому что набор значений фиксирован и семантически различим.
- События по `user_id` для равномерного распределения: `HASH(user_id)`.
- Логи по времени: `RANGE(created_at)` по дням или месяцам.
- Клиенты по стране: `LIST(country)` или `HASH(country)`, если стран слишком много и нет отдельных правил для каждой.

## Партиционирование и индексы

Для `lab03.events` созданы индексы:

```sql
CREATE INDEX idx_lab03_events_user_id ON lab03.events(user_id);
CREATE INDEX idx_lab03_events_event_type ON lab03.events(event_type);
```

PostgreSQL создал индексы на дочерних партициях. Запрос по дате и `user_id`:

```text
Bitmap Heap Scan on events_2026_09_10
  Bitmap Index Scan on events_2026_09_10_user_id_idx
Execution Time: 0.063 ms
```

Здесь работают оба механизма: partition pruning оставил одну партицию, а индекс быстро нашел строки внутри нее.

## Автоматизация партиций

Реализованы функции:

- `lab03.create_events_partition(partition_day date)` - создает дневную партицию, если ее еще нет.
- `lab03.create_events_partitions(required_from date, horizon_days int)` - создает набор будущих партиций.
- `lab03.check_events_partitions(required_from date, horizon_days int)` - проверяет наличие партиций на горизонт.
- `lab03.partition_health_check(required_from date, horizon_days int)` - пишет `OK`/`CRITICAL` в таблицу алертов только при смене состояния.

Результат создания будущих партиций:

```text
2026-09-11 | exists: lab03.events_2026_09_11
2026-09-12 | created: lab03.events_2026_09_12
2026-09-13 | created: lab03.events_2026_09_13
2026-09-14 | created: lab03.events_2026_09_14
```

Проверка health-check:

```text
OK       | все требуемые партиции существуют
CRITICAL | отсутствует events_2026_09_14
OK       | восстановление после повторного создания партиции
```

Повторный `CRITICAL` не создал дубликат алерта: в таблице остались только три события - `OK`, `CRITICAL`, `OK`.

Дополнительно подготовлен файл `scripts/lab03_pg_cron.sql` с расписанием для `pg_cron`:

```sql
SELECT cron.schedule(
    'lab03-create-events-partitions',
    '0 1 * * *',
    $$SELECT * FROM lab03.create_events_partitions(current_date, 3);$$
);

SELECT cron.schedule(
    'lab03-check-events-partitions',
    '5 1 * * *',
    $$SELECT * FROM lab03.partition_health_check(current_date, 3);$$
);
```

Для запуска `pg_cron` основной PostgreSQL собирается из `docker/postgres/pgcron/Dockerfile`. В `docker-compose.yml` включены параметры:

```text
shared_preload_libraries=pg_cron
cron.database_name=rpm
```

После запуска PostgreSQL расписание применяется командой:

```bash
psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/lab03_pg_cron.sql
```

Активные задачи можно посмотреть так:

```sql
SELECT jobid, jobname, schedule, command, active
FROM cron.job
ORDER BY jobid;
```

Удаление задач:

```sql
SELECT cron.unschedule('lab03-create-events-partitions');
SELECT cron.unschedule('lab03-check-events-partitions');
```

В DBeaver это удобно делать через обычный SQL Editor: открыть подключение к базе `rpm`, вставить запрос к `cron.job` или `cron.unschedule(...)` и выполнить его.

## Telegram Alerting

Для отправки алертов в Telegram добавлен worker `cmd/lab03-alertbot`.

Как работает цепочка:

```text
pg_cron
  -> lab03.partition_health_check(...)
  -> INSERT в lab03.partition_alerts при смене OK/CRITICAL
  -> cmd/lab03-alertbot читает новые строки
  -> Telegram Bot API отправляет сообщение в чат
```

Переменные окружения:

```text
TELEGRAM_BOT_TOKEN=token_from_botfather
TELEGRAM_CHAT_ID=telegram_chat_id
TELEGRAM_ALERT_LOOP=false
TELEGRAM_ALERT_INTERVAL=30s
TELEGRAM_ALERT_LIMIT=20
```

Одноразовая отправка всех новых алертов:

```bash
set -a
source .env
set +a

GOCACHE="$PWD/.gocache" go run ./cmd/lab03-alertbot
```

Запуск в режиме постоянного polling:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab03-alertbot -loop -interval 30s
```

Проверка без реальной отправки в Telegram:

```bash
GOCACHE="$PWD/.gocache" go run ./cmd/lab03-alertbot -dry-run
```

Worker сам создает служебную таблицу:

```sql
lab03.telegram_alert_state
```

В ней хранится последний отправленный `partition_alerts.id`, поэтому один и тот же алерт не отправляется повторно.

Для получения `TELEGRAM_CHAT_ID` можно написать боту любое сообщение и открыть:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

В ответе нужен `message.chat.id`.

## Применение к сервису

Для сервиса выбрана таблица `bookings`, потому что она быстро растет и часто фильтруется по `created_at`, `user_id`, `event_id` и `status`.

Создана учебная партиционированная копия `lab03.bookings_partitioned`:

- ключ: `created_at`
- стратегия: `RANGE`
- партиции: `bookings_2025`, `bookings_2026`, `bookings_2027`
- объем: до 1000000 строк из реальной таблицы `public.bookings`
- индексы: `(user_id, created_at DESC)` и `(created_at)`

Проверенные запросы:

1. Подсчет бронирований за 2026 год: сканировалась только `bookings_2026`, `Execution Time: 22.465 ms`.
2. Пагинация бронирований пользователя за 2026 год: использовались `bookings_2026` и индекс `bookings_2026_user_id_created_at_idx`, `Execution Time: 0.099 ms`.
3. Агрегация выручки по событиям за 2026 год: сканировалась только `bookings_2026`, `Execution Time: 151.268 ms`.

## Контрольные вопросы

Партиционирование делит одну логическую таблицу на физические части. Это полезно для больших таблиц, когда запросы часто ограничены ключом партиционирования, например датой.

Индекс ускоряет поиск внутри таблицы или партиции, но сам по себе не уменьшает число физических таблиц, которые надо проверить. Партиционирование может полностью исключить ненужные части данных.

`RANGE` подходит для дат и числовых диапазонов, `LIST` - для фиксированных категорий, `HASH` - для равномерного распределения по ключу.

Минусы партиционирования: сложнее схема, нужно заранее создавать партиции, уникальные ограничения должны учитывать ключ партиционирования, неверно выбранный ключ не даст ускорения.

Партиционирование не поможет, если запросы не фильтруют по ключу партиционирования. В нашем примере фильтр по `event_type` проходит все дневные партиции.
