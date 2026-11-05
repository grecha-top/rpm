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

Для запуска без контейнеризации приложения:

```bash
docker compose up -d db redis rabbitmq
alembic upgrade head
DEBUG=true python -m uvicorn app.main:app --reload
```

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
