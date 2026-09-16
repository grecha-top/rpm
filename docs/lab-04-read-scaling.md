# Лабораторная работа №4. Read Scaling PostgreSQL

## Цель

Поднять primary-replica конфигурацию PostgreSQL, проверить streaming replication, убедиться, что запись идет в primary, чтение возможно с replica, а приложение умеет направлять read-only запросы в отдельный пул подключений.

Файлы:

- `docker-compose.replica.yml` - primary и replica PostgreSQL.
- `docker/postgres/primary-init/01-replication-user.sh` - создание replication-пользователя и правила `pg_hba.conf`.
- `docs/lab-04-replication-output.txt` - вывод проверок репликации.
- `internal/config/config.go` - переменная `REPLICA_DATABASE_URL`.
- `cmd/api/main.go` - подключение write/read пулов.
- `internal/repositories/repository.go` - разделение `db` и `readDB`.

## Запуск

```bash
docker compose -f docker-compose.replica.yml up -d
```

Подключения:

```text
Primary:
  host: localhost
  port: 55432
  database: rpm
  user: postgres
  password: postgres

Replica:
  host: localhost
  port: 55433
  database: rpm
  user: postgres
  password: postgres

Replication user:
  user: replicator
  password: replicator
```

Строки подключения:

```text
postgres://postgres:postgres@127.0.0.1:55432/rpm?sslmode=disable
postgres://postgres:postgres@127.0.0.1:55433/rpm?sslmode=disable
```

## Конфигурация Docker Compose

`postgres-primary` запускается с параметрами:

```text
wal_level=replica
max_wal_senders=10
max_replication_slots=10
hot_standby=on
```

`postgres-replica` при первом старте выполняет:

```bash
pg_basebackup -h postgres-primary -D /var/lib/postgresql/data \
  -U replicator -v -P -R -X stream -C -S rpm_replica_slot
```

Флаг `-R` записывает настройки подключения к primary, `-C -S rpm_replica_slot` создает physical replication slot.

## Проверка репликации

На primary выполнен запрос к `pg_stat_replication`:

```text
application_name | state     | sync_state | write_lsn | flush_lsn | replay_lsn
walreceiver      | streaming | async      | 0/30AB880 | 0/30AB880 | 0/30AB880
```

Вывод означает:

- replica подключена к primary;
- состояние `streaming` - WAL передается потоком;
- `async` - репликация асинхронная;
- одинаковые LSN в момент проверки означают, что заметного лага не было.

## Запись на primary и чтение с replica

На primary была вставлена строка:

```text
id | email                     | full_name
4  | replica-check@example.com | Replica Check
```

Затем та же строка была прочитана с replica:

```text
id | email                     | full_name
4  | replica-check@example.com | Replica Check
```

Попытка записи на replica завершилась ожидаемой ошибкой:

```text
ERROR: cannot execute INSERT in a read-only transaction
```

Это подтверждает, что replica используется только для чтения.

## Изменения в сервисе

В конфигурацию добавлена переменная:

```text
REPLICA_DATABASE_URL
```

Если она задана, приложение открывает второй `pgxpool.Pool` и передает его в репозиторий как read-подключение. Если переменная не задана, чтение и запись идут через основной пул, поэтому локальный запуск без реплики остается рабочим.

Ключевые места:

- `internal/config/config.go` - поле `ReplicaURL`.
- `cmd/api/main.go` - подключение к replica и лог `replica read connection enabled`.
- `internal/repositories/repository.go` - `db` используется для write-запросов, `readDB` для read-запросов.

Read-only методы, например `ListUsers`, `GetUser`, `ListBookings`, `UserBookings`, `EventStats`, выполняются через `r.readDB`. Методы `Create*`, `Update*`, `Delete*` используют `r.db`.

Проверка запуска сервиса с репликой:

```bash
PORT=18081 \
DATABASE_URL="postgres://postgres:postgres@127.0.0.1:55432/rpm?sslmode=disable" \
REPLICA_DATABASE_URL="postgres://postgres:postgres@127.0.0.1:55433/rpm?sslmode=disable" \
go run ./cmd/api
```

Лог:

```text
goose: no migrations to run. current version: 202609120001
replica read connection enabled
api listening on :18081
```

Проверки:

```bash
curl http://localhost:18081/health
curl http://localhost:18081/api/users
```

`/api/users` вернул пользователя `replica-check@example.com`, то есть реальный read-сценарий сервиса успешно прочитал данные через replica-подключение.

## Replication lag

Репликация настроена как асинхронная, поэтому между записью на primary и видимостью на replica возможна задержка. На локальной проверке лага не было видно, LSN совпали, но в реальной нагрузке replica может отставать.

Практические последствия:

- read-after-write запросы лучше отправлять на primary;
- для списков, каталогов и аналитики допустимо читать с replica;
- можно контролировать лаг через `pg_stat_replication` на primary и `pg_last_wal_replay_lsn()`/`pg_last_xact_replay_timestamp()` на replica;
- при большом лаге приложение может временно переключать критичные чтения на primary.

## CAP и read scaling

В схеме primary-replica запись принимает primary, а replica масштабирует чтение. При асинхронной репликации система выбирает доступность чтения и меньшую нагрузку на primary, но не гарантирует строгую консистентность чтения с replica сразу после записи.

Если нужна строгая консистентность, чтение после записи надо выполнять с primary или использовать синхронную репликацию. Синхронная репликация повышает согласованность, но может ухудшить доступность и задержки записи, если replica недоступна или медленная.

## Контрольные вопросы

Primary принимает запись и генерирует WAL. Replica получает WAL и применяет изменения у себя.

Streaming replication передает WAL почти сразу после появления, поэтому replica может обслуживать read-only запросы.

Replica в hot standby режиме доступна для чтения, но запись на нее запрещена.

Read scaling полезен, когда чтений больше, чем записей. Он разгружает primary, но требует учитывать replication lag.

Для нашего сервиса на replica логично отправлять списки пользователей, мероприятий, площадок, бронирований и статистику. Создание, обновление и удаление сущностей должны идти только на primary.
