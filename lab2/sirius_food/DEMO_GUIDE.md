# Демонстрация лабораторных работ 5–8

HTTP-запросы собраны в Postman-коллекции `postman/Sirius_Food_Labs_5_8.postman_collection.json`. В этом файле оставлены подготовка стенда и проверки, которые нельзя полноценно выполнить обычным Postman HTTP-запросом.

## 1. Поднять стенд и подготовить данные

```bash
cd /Users/ulyanagrechishnikova/study/rpm/lab2/sirius_food
docker compose up --build -d
docker compose exec api python scripts/prepare_demo.py
docker compose ps
```

Скрипт можно запускать повторно: он очищает предыдущие demo-заказы и возвращает базу в исходное состояние.

```text
Администратор: demo.admin@example.com
Курьер:        demo.courier@example.com
Пароль:        demo-password
Баланс:        10000 рублей
```

Интерфейсы:

| Компонент | Адрес | Доступ |
|---|---|---|
| Swagger | http://localhost:8000/docs | — |
| Next.js | http://localhost:3001/menu | — |
| Flower | http://localhost:5555 | — |
| RabbitMQ | http://localhost:15672 | `sirius` / `sirius` |
| gRPC | `localhost:50051` | через клиент |

## 2. Импорт и порядок работы в Postman

1. Нажать **Import**.
2. Выбрать `postman/Sirius_Food_Labs_5_8.postman_collection.json`.
3. Открыть коллекцию «Сириус Еда — лабораторные 5–8».
4. Выполнять запросы по номерам от 1 до 14.
5. После запросов №5 и №10 подождать 3–5 секунд: Outbox, RabbitMQ consumer-ы и Saga работают асинхронно.

Коллекция сама сохраняет `admin_token`, `courier_token`, `item_id`, `order1_id`, `order2_id` и `delivery_id`. Tracking первого заказа расположен после Saga специально: если завершить доставку раньше, курьер освободится и компенсация второго заказа не сработает.

При запуске через Collection Runner установите задержку между запросами не менее 1000 мс. Для защиты удобнее отправлять запросы вручную, чтобы параллельно показывать Flower, RabbitMQ и базу.

## 3. ЛР 5 — Flower, Celery Worker, идемпотентность и DLQ

После Postman-запроса №4 открыть Flower: http://localhost:5555. Там должны появиться:

- `orders.generate_pdf`;
- `orders.send_email`;
- `orders.send_sms`.

Логи Worker и Beat:

```bash
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 celery-beat
```

Проверка идемпотентности одной и той же фоновой задачи:

```bash
ORDER1=ID_ИЗ_ПЕРЕМЕННОЙ_POSTMAN_order1_id

docker compose exec api python -c \
  "from app.tasks.orders import generate_order_pdf; generate_order_pdf.delay($ORDER1); generate_order_pdf.delay($ORDER1)"

sleep 3
docker compose logs --tail=50 celery-worker
```

Обе задачи получит Worker, но повторная вернёт `pdf already completed`.

Ретраи и Celery DLQ:

```bash
docker compose exec api python -c \
  "from app.tasks.orders import send_order_email; print(send_order_email.delay(5000, 'fail@example.com').id)"

sleep 12
docker compose logs --tail=120 celery-worker
docker compose exec redis redis-cli -n 1 LLEN dlq
```

ID `5000` намеренно вызывает ошибку. После трёх ретраев envelope остаётся в очереди `dlq`.

## 4. ПР 7 — содержимое Outbox, обработанные события и RabbitMQ DLQ

После Postman-запроса №5 показать данные, которые не возвращаются HTTP API:

```bash
docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT event_type,routing_key,published_at,attempts FROM outbox_events ORDER BY created_at DESC LIMIT 10;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT consumer_name,event_id,processed_at FROM processed_events ORDER BY processed_at DESC LIMIT 10;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT * FROM kitchen_orders ORDER BY id DESC LIMIT 10;"
```

В RabbitMQ Management открыть:

- Exchanges → `sirius.events`;
- Queues → `kitchen_queue`;
- Queues → `delivery_queue`;
- Queues → `order_compensation_queue`;
- очереди `*.dlq`.

Проверка RabbitMQ DLQ битым сообщением требует прямой публикации в брокер:

```bash
docker compose exec api python -c \
  "import asyncio; from app.core.rabbitmq import publish_raw; asyncio.run(publish_raw('order.paid', b'not-json'))"

sleep 3
```

После трёх попыток сообщения появятся в `kitchen_queue.dlq` и `delivery_queue.dlq`.

## 5. ПР 6 — настоящий bidirectional gRPC streaming

Unary-вызовы и server streaming доступны через REST-фасад в Postman. Двунаправленный gRPC stream запускается отдельным клиентом:

```bash
docker compose exec api python scripts/delivery_chat_client.py
docker compose logs --tail=100 delivery-grpc
```

Ожидаются ответы вида `Курьер получил: Где заказ?`.

## 6. Saga — проверка компенсации в базе

После Postman-запроса №10 подождать 5 секунд, затем подставить переменные `order1_id` и `order2_id` из Postman:

```bash
ORDER1=ID_ПЕРВОГО_ЗАКАЗА
ORDER2=ID_ВТОРОГО_ЗАКАЗА

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT id,status,total FROM orders WHERE id IN ($ORDER1,$ORDER2) ORDER BY id;"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT email,balance FROM users WHERE email='demo.admin@example.com';"

docker compose exec -T db psql -U sirius -d sirius_food -c \
  "SELECT event_type,published_at FROM outbox_events ORDER BY created_at DESC LIMIT 10;"
```

Ожидается:

- первый заказ — `paid`;
- второй заказ — `cancelled`;
- баланс равен `9750`: оплачено только первое блюдо за 250, стоимость второго возвращена;
- присутствуют `DeliveryFailed` и `OrderCancelled`.

## 7. ПР 8 — визуальная разница SSR и CSR

Postman-запросы №12–14 анализируют HTML автоматически. Для визуальной демонстрации открыть в браузере:

```text
http://localhost:3001/menu
http://localhost:3001/menu-csr
```

Через **Просмотреть исходный код страницы** показать:

- в `/menu` названия блюд уже находятся в HTML;
- в `/menu-csr` блюда появляются только после выполнения JavaScript и клиентского `fetch`.

Для строгой защиты на 10 баллов открыть Chrome DevTools → Network/Performance и сравнить FCP и момент появления первой карточки.

## 8. Финальная проверка и остановка

```bash
docker compose exec api pytest -q
docker compose ps
```

Ожидается `13 passed`, все сервисы имеют статус `Up`.

Общий поток логов:

```bash
docker compose logs -f \
  api celery-worker celery-beat delivery-grpc \
  outbox-publisher kitchen-consumer delivery-consumer compensation-consumer frontend
```

Остановить контейнеры с сохранением данных:

```bash
docker compose stop
```

Вернуть без пересборки:

```bash
docker compose start
```
