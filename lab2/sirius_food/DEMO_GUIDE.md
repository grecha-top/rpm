# Демонстрация лабораторных работ 5–8

Этот сценарий поднимает весь стенд одной командой и готовит повторяемые demo-данные, не удаляя существующие пользовательские записи.

## 1. Поднять всё сразу

Из каталога backend:

```bash
cd /Users/ulyanagrechishnikova/study/rpm/lab2/sirius_food
docker compose up --build -d
docker compose ps
```

Первый запуск скачивает образы и зависимости и может занять несколько минут. Должны работать PostgreSQL, Redis, RabbitMQ, FastAPI, Celery Worker, Beat, Flower, gRPC, event consumer-ы и Next.js.

Адреса:

| Компонент | Адрес | Доступ |
|---|---|---|
| Swagger | http://localhost:8000/docs | — |
| Next.js | http://localhost:3001/menu | — |
| Flower | http://localhost:5555 | — |
| RabbitMQ | http://localhost:15672 | `sirius` / `sirius` |
| gRPC | `localhost:50051` | через клиент |

Порт `3001` выбран потому, что `3000` занят другим локальным проектом.

## 2. Подготовить данные

```bash
docker compose exec api python scripts/prepare_demo.py
```

Скрипт можно запускать повторно. Он создаёт или обновляет только записи `demo.*@example.com`, очищает их старые заказы и оставляет одного свободного demo-курьера.

Данные:

```text
Администратор: demo.admin@example.com
Курьер:        demo.courier@example.com
Пароль:        demo-password
Баланс:        10000 рублей
```

Подготовить переменные терминала:

```bash
API=http://127.0.0.1:8000

ADMIN_TOKEN=$(curl -sS -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo.admin@example.com","password":"demo-password"}' \
  | jq -r '.access_token')

COURIER_TOKEN=$(curl -sS -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo.courier@example.com","password":"demo-password"}' \
  | jq -r '.access_token')

ITEM_ID=$(curl -sS "$API/menu/items" \
  | jq -r '.[] | select(.name=="Демо сырники с малиной") | .id')

echo "ITEM_ID=$ITEM_ID"
```

Если `jq` не установлен, те же действия можно выполнить через Swagger.

## 3. Лабораторная работа 5 Celery

Открыть Flower: http://localhost:5555

Создать первый заказ и сохранить ID:

```bash
time curl -sS -X POST "$API/orders/create" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"item_id\":$ITEM_ID,\"quantity\":1}" \
  | tee /tmp/sirius-order-1.json

ORDER1=$(jq -r '.order_id' /tmp/sirius-order-1.json)
echo "ORDER1=$ORDER1"
```

Показать:

```bash
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 celery-beat
```

В Flower должны появиться:

- `orders.generate_pdf`;
- `orders.send_email`;
- `orders.send_sms`.

Проверка идемпотентности PDF:

```bash
docker compose exec api python -c \
  "from app.tasks.orders import generate_order_pdf; generate_order_pdf.delay($ORDER1); generate_order_pdf.delay($ORDER1)"

sleep 3
docker compose logs --tail=50 celery-worker
```

Повторная задача вернёт `pdf already completed`, не создавая второй эффект.

Проверка ретраев и Celery DLQ:

```bash
docker compose exec api python -c \
  "from app.tasks.orders import send_order_email; print(send_order_email.delay(5000, 'fail@example.com').id)"

sleep 12
docker compose logs --tail=120 celery-worker
docker compose exec redis redis-cli -n 1 LLEN dlq
```

ID `5000` специально вызывает ошибку email. После трёх ретраев envelope остаётся в `dlq`.

Что сказать: API только ставит тяжёлые операции в Redis, Worker выполняет их после HTTP-ответа; Beat запускает периодическую статистику; `SET NX EX` защищает от дублей.

## 4. Практическая работа 7 RabbitMQ и Outbox

Оплатить первый заказ:

```bash
curl -sS -X POST "$API/orders/$ORDER1/pay" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

sleep 4
```

Показать Outbox и независимых consumer-ов:

```bash
docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT event_type,routing_key,published_at,attempts FROM outbox_events ORDER BY created_at DESC LIMIT 10;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT consumer_name,event_id,processed_at FROM processed_events ORDER BY processed_at DESC LIMIT 10;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT * FROM kitchen_orders ORDER BY id DESC LIMIT 10;"
```

В RabbitMQ открыть:

- Exchanges → `sirius.events`;
- Queues → `kitchen_queue`;
- Queues → `delivery_queue`;
- Queues → `order_compensation_queue`;
- очереди `*.dlq`.

Проверка RabbitMQ DLQ битым JSON:

```bash
docker compose exec api python -c \
  "import asyncio; from app.core.rabbitmq import publish_raw; asyncio.run(publish_raw('order.paid', b'not-json'))"

sleep 3
```

После трёх попыток сообщения появятся в `kitchen_queue.dlq` и `delivery_queue.dlq`.

Что сказать: изменение заказа и `OrderPaid` записываются одной транзакцией; Outbox Publisher публикует событие с publisher confirms; `(consumer_name, event_id)` обеспечивает идемпотентность при at-least-once delivery.

## 5. Практическая работа 6 gRPC

Первое `OrderPaid` назначает свободного demo-курьера. Показать доставку:

```bash
curl -sS "$API/delivery/my" \
  -H "Authorization: Bearer $COURIER_TOKEN" | jq

docker compose logs --tail=100 delivery-grpc
```

Bidirectional streaming:

```bash
docker compose exec api python scripts/delivery_chat_client.py
```

Пока не запускайте tracking: курьер должен остаться занят для следующего шага Saga.

Что сказать: HTTP-контракт монолита сохранён, но delivery выполняется отдельным процессом через Protobuf/gRPC; клиент обрабатывает deadline, `UNAVAILABLE`, `NOT_FOUND` и `PERMISSION_DENIED`.

## 6. Saga компенсация

Создать и оплатить второй заказ, пока единственный свободный demo-курьер занят первым:

```bash
ORDER2=$(curl -sS -X POST "$API/orders/create" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"item_id\":$ITEM_ID,\"quantity\":1}" \
  | jq -r '.order_id')

curl -sS -X POST "$API/orders/$ORDER2/pay" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

sleep 5
```

Проверить отмену и возврат:

```bash
docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT id,status,total FROM orders WHERE id IN ($ORDER1,$ORDER2) ORDER BY id;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT email,balance FROM users WHERE email='demo.admin@example.com';"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT event_type,published_at FROM outbox_events ORDER BY created_at DESC LIMIT 10;"
```

Ожидается:

- первый заказ — `paid`;
- второй — `cancelled`;
- баланс снова содержит стоимость второго заказа;
- есть `DeliveryFailed` и `OrderCancelled`.

Server streaming первого заказа:

```bash
curl -N "$API/delivery/track/$ORDER1" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Статусы приходят с интервалом: `in_progress → on_the_way → delivered`.

## 7. Практическая работа 8 Next.js

Frontend уже запущен Compose на http://localhost:3001/menu

SSR:

```bash
curl -s http://localhost:3001/menu | grep "Демо сырники с малиной"
```

CSR — блюдо отсутствует в исходном HTML:

```bash
curl -s http://localhost:3001/menu-csr | grep "Демо сырники с малиной"
```

Вторая команда не должна ничего вывести.

SEO:

```bash
curl -s "http://localhost:3001/menu/$ITEM_ID" \
  | grep -E '<title>|og:title|description'
```

В браузере показать `Ctrl+U` для `/menu` и `/menu-csr`.

Что сказать: `/menu` — Server Component, данные приходят в готовом HTML; `/menu-csr` получает их после JavaScript; ISR в production кеширует HTML на 60 секунд, а Redis отдельно кеширует backend-данные.

## 8. Финальная проверка

```bash
docker compose exec api pytest -q
docker compose ps
```

Ожидается `13 passed`, а все сервисы имеют статус `Up`.

Общий поток логов:

```bash
docker compose logs -f \
  api celery-worker celery-beat delivery-grpc \
  outbox-publisher kitchen-consumer delivery-consumer compensation-consumer frontend
```

## 9. Остановка

Остановить контейнеры, сохранив данные:

```bash
docker compose stop
```

Снова запустить:

```bash
docker compose start
```

Удалять volumes для обычной демонстрации не требуется.
