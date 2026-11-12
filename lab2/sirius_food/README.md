# Сириус Еда backend

Учебный backend последовательно развивает Clean Architecture: JWT и RBAC, Redis Cache-Aside, фоновые задачи Celery, gRPC-микросервис доставки и событийное взаимодействие через RabbitMQ с Saga и Transactional Outbox.

## Архитектура

```text
Next.js ──REST──> FastAPI ──────────────> PostgreSQL
                    │                         │
                    ├── Redis Cache-Aside     ├── outbox_events
                    ├── Celery → Redis        └── processed_events
                    │       ├── Worker
                    │       ├── Beat
                    │       └── Flower
                    │
                    ├──gRPC──> Delivery Service
                    │
                    └── Outbox Publisher → RabbitMQ topic exchange
                                             ├── kitchen_queue
                                             ├── delivery_queue
                                             └── order_compensation_queue
```

Celery использует Redis и отвечает за технические фоновые эффекты одного приложения. RabbitMQ переносит доменные события между независимо запускаемыми компонентами.

## Быстрый запуск

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up --build
```

Compose запускает PostgreSQL, Redis, RabbitMQ, FastAPI, gRPC-сервис, Celery Worker, Beat, Flower, Outbox Publisher и три event consumer-а.

Интерфейсы:

- Swagger: `http://127.0.0.1:8000/docs`;
- Flower: `http://127.0.0.1:5555`;
- RabbitMQ Management: `http://127.0.0.1:15672`, логин и пароль `sirius`;
- gRPC: `localhost:50051`.
- Prometheus: `http://127.0.0.1:9090`;
- Grafana: `http://127.0.0.1:3000` (`admin` / `admin`);
- Jaeger: `http://127.0.0.1:16686`.

Если стандартные порты заняты, задайте `PROMETHEUS_PORT`, `GRAFANA_PORT`
и `JAEGER_UI_PORT` перед запуском `docker compose`.

Для запуска без контейнеризации приложения:

```bash
docker compose up -d db redis rabbitmq
alembic upgrade head
DEBUG=true python -m uvicorn app.main:app --reload
```

## Практическая работа 9 Observability

HTTP middleware принимает `X-Correlation-ID` или генерирует UUID, сохраняет его в `request.state` и `ContextVar`, возвращает в заголовке ответа. При оплате заказа ID попадает в envelope `OrderPaid`, затем в заголовок RabbitMQ и JSON-логи кухни. Все прикладные логи пишутся в stdout через `structlog`.

Prometheus автоматически получает RED-метрики FastAPI с `/metrics`, а также метрики RabbitMQ и Redis Exporter. Grafana datasource и дашборд с RPS, p95 latency, 5xx, длиной `kitchen_queue` и cache hit rate создаются автоматически из `grafana/`.

Проверка сквозного ID и единого distributed trace:

```bash
docker compose up --build -d
docker compose exec api python scripts/prepare_demo.py
docker compose exec api python scripts/demo_lab9_trace.py
docker compose logs api outbox-publisher kitchen-consumer | grep lab9-
curl -s http://127.0.0.1:8000/metrics | grep http_requests_total
```

Скрипт завершается успешно только если один trace содержит `sirius-api`,
`sirius-outbox` и `sirius-kitchen`. W3C `traceparent` сохраняется в Outbox,
восстанавливается publisher-ом и передаётся в RabbitMQ. OpenTelemetry включён в
Compose и отправляет spans в Jaeger по OTLP. Для запуска без Compose задайте
`OTEL_ENABLED=true` и `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces`.

Sentry не требует секрета для обычного запуска. Для демонстрации задайте
`SENTRY_DSN` в `.env`, пересоздайте API и вызовите контролируемую ошибку:

```bash
docker compose up -d --force-recreate api
curl -i http://127.0.0.1:8000/debug/sentry \
  -H 'X-Correlation-ID: sentry-demo-42'
```

В Sentry событие `Sirius Food observability demo error` содержит tag
`correlation_id=sentry-demo-42`. Ручка возвращает 404, если
`OBSERVABILITY_DEMO_ENABLED=false`.

## Лабораторная работа 10 Production testing

Интеграционные тесты поднимают чистую PostgreSQL 15 через Testcontainers, применяют все Alembic-миграции и откатывают внешнюю транзакцию после каждого теста:

```bash
pytest -v tests/integration
pytest -q tests/contract
pytest --cov=app --cov-report=html
```

Для запуска интеграционных тестов из контейнера на Docker Desktop:

```bash
docker compose run --rm --no-deps \
  -e TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal \
  -v /var/run/docker.sock:/var/run/docker.sock \
  api pytest -v tests/integration
```

Pact V4-контракт генерируется consumer-описанием кухни, а provider verification
вызывает настоящий `OrderService`:

```bash
python scripts/generate_order_paid_pact.py
pytest -q tests/contract
```

Mutation testing настроен в `setup.cfg`. Итоговый прогон: 45 мутаций, 44 убиты
тестами, одна остановлена timeout, выживших нет:

```bash
mutmut run
mutmut results
python scripts/check_mutation_results.py
```

Нагрузочный профиль Locust распределён как 70% меню, 20% карточка и 10%
создание заказа. Воспроизводимый прогон на 100 пользователей:

```bash
./scripts/run_lab10_load.sh
```

Скрипт сам готовит данные и токен, создаёт CSV/HTML и
`docs/lab10-load-report.md`. В контрольном прогоне на 100 пользователей было
1259 запросов без ошибок; bottleneck по p95 — `POST /orders/create` (440 мс).

Workflow `.github/workflows/lab2-tests.yml` запускает unit-, настоящий Pact
provider verification, Testcontainers и mutation gate на каждый push и pull
request, затрагивающий `lab2`. Чтобы красный CI блокировал merge, в GitHub
Settings → Branches нужно сделать checks `tests` и `mutation-tests` required.

## Лабораторная работа 5 Celery

После создания заказа слой `OrderService` вызывает порт `OrderTaskDispatcher`. Celery-адаптер ставит три независимые задачи:

- генерация PDF-чека;
- отправка email;
- отправка SMS.

Роутер не импортирует задачи и не содержит фоновой бизнес-логики. Все задачи используют JSON, late acknowledgement и `worker_prefetch_multiplier=1`.

### Результаты замера

| Режим | Выполняемая работа | Время |
|---|---|---:|
| Синхронно | PDF 2 с + email 1 с + SMS 1 с | 4,03 с |
| Celery | Постановка трёх сообщений в Redis | 0,087 с |

Постановка задач стала примерно в 46 раз быстрее синхронного выполнения имитаций. Для отчётного замера использовалась отдельная Redis DB, сообщения после проверки удалены.

Надёжность:

- email и SMS используют exponential backoff, jitter и три ретрая;
- после окончательного падения envelope задачи публикуется в очередь `dlq`;
- ключи `order:{id}:{effect}:completed` предотвращают повторный эффект;
- Redis lock создаётся атомарно через `SET NX EX`;
- Beat раз в минуту обновляет статистику заказов в Redis;
- Flower показывает состояние задач на порту `5555`.

Ручной запуск:

```bash
celery -A app.core.celery_app:celery_app worker -l info -Q default
celery -A app.core.celery_app:celery_app beat -l info
celery -A app.core.celery_app:celery_app flower --port=5555
```

## Практическая работа 6 gRPC

Контракт находится в `proto/delivery.proto`. Сгенерированные модули хранятся в `app/generated`, сервер — в `services/delivery`.

Поддержаны методы:

- `AssignCourier`, `CompleteDelivery`, `GetDelivery`;
- `ListCourierDeliveries` для сохранения HTTP API монолита;
- `TrackDelivery` с server streaming;
- `ChatWithCourier` с bidirectional streaming.

Монолит обращается к сети только через `DeliveryGrpcClient`. Клиент задаёт deadline и преобразует `NOT_FOUND`, `PERMISSION_DENIED`, `FAILED_PRECONDITION`, `UNAVAILABLE` и `DEADLINE_EXCEEDED` в прикладные ошибки и HTTP-коды.

```bash
python -m grpc_tools.protoc \
  -Iproto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  proto/delivery.proto

python -m services.delivery.server
python scripts/delivery_chat_client.py
```

После повторной генерации в `delivery_pb2_grpc.py` нужно сохранить package-import:

```python
from app.generated import delivery_pb2 as delivery__pb2
```

## Практическая работа 7 Event Driven Architecture

### События

- `OrderPaid`;
- `DeliveryFailed`;
- `OrderCancelled`.

Envelope содержит `event_id`, `event_type`, `event_version`, `occurred_at`, `correlation_id` и `payload`.

### Transactional Outbox

`POST /orders/{id}/pay` в одной транзакции:

1. списывает стоимость с баланса;
2. переводит заказ в `paid`;
3. сохраняет `OrderPaid` в `outbox_events`.

Outbox Publisher читает неопубликованные строки с `FOR UPDATE SKIP LOCKED`, публикует persistent-сообщение с publisher confirms и только после успеха заполняет `published_at`. При недоступном RabbitMQ заказ и событие остаются в PostgreSQL.

### Идемпотентность и DLQ

Consumer перед бизнес-изменением вставляет `(consumer_name, event_id)` в `processed_events`. Составной ключ нужен, потому что одно событие должны независимо обработать кухня и доставка.

Ошибка обрабатывается не более трёх раз. Счётчик хранится в заголовке `x-retry-count`; после исчерпания попыток сообщение отклоняется без requeue и RabbitMQ переносит его в `<queue>.dlq`.

### Saga

```text
OrderPaid
  └── Delivery consumer
      ├── курьер найден → Delivery(in_progress)
      └── курьера нет → DeliveryFailed
                            └── Compensation consumer
                                ├── status = cancelled
                                ├── возврат order.total
                                └── OrderCancelled
```

Компенсация идемпотентна: повторный `DeliveryFailed` с тем же `event_id` не возвращает деньги второй раз.

## Проверка

```bash
PYTHONPATH=. python -m pytest -q
docker compose config --quiet
alembic heads
```

Проверенный результат: 13 unit-тестов, валидный Compose и единственная голова миграций `0003_event_architecture`.

Основной end-to-end сценарий:

1. зарегистрировать пользователя и пополнить баланс;
2. создать блюдо и заказ;
3. оплатить `POST /orders/{id}/pay`;
4. проверить `outbox_events` и RabbitMQ exchange `sirius.events`;
5. убедиться, что кухня создала одну запись при повторной доставке события;
6. при отсутствии курьера проверить отмену и однократный возврат средств.

Во время реализации этот сценарий был проверен на реальных PostgreSQL и RabbitMQ: событие независимо доставлено в две очереди, повтор кухни пропущен, Saga вернула 250 рублей ровно один раз и создала `OrderCancelled`.
