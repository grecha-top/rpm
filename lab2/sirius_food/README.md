# Sirius Food Labs 3 and 4

Проект продолжает лабораторную работу № 2 и добавляет безопасность API и production-подход к кешированию меню.

## Лабораторная работа № 3

Реализовано:

- bcrypt-хеширование паролей;
- JWT access-токены на 15 минут;
- refresh-токены на 7 дней с хранением хеша в PostgreSQL;
- refresh token rotation: использованный refresh-токен отзывается, повторное использование сбрасывает сессию пользователя;
- `get_current_user` для аутентификации запросов;
- RBAC для ролей `student`, `cook`, `courier`, `admin`;
- защита `orders`, `users`, `menu` и `delivery`;
- удаление `user_id` из payload создания заказа: пользователь берётся из JWT;
- IDOR-защита отмены заказа и завершения доставки в service/router boundary;
- Redis rate limiting для `/auth/login`;
- CORS из настроек и Swagger только при `DEBUG=true`;
- четыре security-теста без PostgreSQL.

Поток авторизации:

```text
POST /auth/login
    -> bcrypt verify
    -> JWT access + refresh
    -> Authorization: Bearer <access>
    -> get_current_user
    -> require_role (если нужен RBAC)
    -> Service проверяет права на конкретный объект
```

## Лабораторная работа № 4

Реализовано:

- Redis-клиент в `app/core/redis.py`;
- Cache-Aside для `GET /menu/items` с ключом `menu:all` и TTL 300 секунд;
- кеширование меню по категории `menu:category:{id}` с TTL 600 секунд;
- событийная инвалидация после создания и изменения блюда;
- Redis lock при заполнении кеша для защиты от cache stampede;
- прогрев `menu:all` при старте приложения;
- отказоустойчивый fallback: при недоступном Redis чтение продолжается из PostgreSQL;
- Locust-сценарий в `locustfile.py`.

Кеш находится в `MenuRepository`, потому что Redis является инфраструктурной деталью. `MenuService` знает только о методах репозитория и не импортирует Redis.

```text
GET /menu/items
    -> MenuService.get_items()
    -> MenuRepository.get_all()
       -> Redis hit: вернуть кеш
       -> Redis miss: PostgreSQL -> Redis SETEX -> вернуть данные
```

## Запуск

```bash
cd lab2/sirius_food
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d db redis
alembic upgrade head
DEBUG=true python -m uvicorn app.main:app --reload
```

Для текущего `docker-compose.yml` PostgreSQL доступен на `localhost:1432`, Redis на `localhost:6379`.

Swagger: `http://127.0.0.1:8000/docs`.

## Основные сценарии проверки

1. Зарегистрировать пользователя:

```bash
curl -X POST http://127.0.0.1:8000/users/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"strong-pass","phone":"+79991234567"}'
```

2. Получить токены:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"strong-pass"}'
```

3. Вызвать `GET /menu/items`: первый запрос создаёт кеш `menu:all`, следующие читают Redis.

4. Вызвать `POST /orders/create` без `user_id`, передав только `item_id` и `quantity` вместе с Bearer-токеном.

5. Проверить, что запрос без токена даёт `401`, неверная роль даёт `403`, а попытка отменить чужой заказ даёт `403`.

## Нагрузочное тестирование

Baseline выполняется до кеширования, повторный замер после него:

```bash
locust -f locustfile.py --host=http://127.0.0.1:8000
```

Открыть `http://localhost:8089`, выбрать 500 пользователей и spawn rate 10. В отчёте сравниваются RPS, средняя latency, p95 и число запросов к PostgreSQL.

| Метрика | До Redis | После Redis |
|---|---:|---:|
| RPS | заполнить по Locust | заполнить по Locust |
| Средняя latency | заполнить по Locust | заполнить по Locust |
| p95 latency | заполнить по Locust | заполнить по Locust |
| Нагрузка PostgreSQL | высокая | низкая после cache warm-up |

## Тесты

```bash
PYTHONPATH=. python -m pytest
```
