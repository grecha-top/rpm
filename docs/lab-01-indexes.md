# Лабораторная работа №1
# Индексы и EXPLAIN ANALYZE

## Цель

Исследовать планы выполнения SQL-запросов в PostgreSQL, проверить разные типы индексов и применить оптимизацию к реальному backend-сервису.

Главное правило: каждый индекс должен быть подтвержден измерением.

```text
EXPLAIN ANALYZE до
  -> изменение
  -> EXPLAIN ANALYZE после
  -> сравнение результата
```

## Подготовка

Запуск приложения и PostgreSQL:

```bash
docker compose up --build
```

Загрузка переменных окружения:

```bash
set -a
source .env
set +a
```

Учебная таблица `orders` создается отдельным скриптом:

```bash
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_setup.sql
```

Запуск всех экспериментов по учебной таблице:

```bash
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_orders_experiments.sql | tee docs/lab-01-orders-output.txt
```

Запуск экспериментов по реальному сервису:

```bash
DATABASE_URL="$LOCAL_DATABASE_URL" \
go run ./scripts/generate_data.go --users 100000 --venues 1000 --events 100000 --bookings 1000000

psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-before-output.txt
# применить migrations/202609120001_lab01_booking_indexes.sql
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-after-output.txt
```

Фактические полные выводы сохранены в:

- `docs/lab-01-orders-output.txt`
- `docs/lab-01-service-before-output.txt`
- `docs/lab-01-service-after-output.txt`

## Часть 1. Работа с тестовой таблицей `orders`

### Задание 1-2. Создание таблицы и генерация данных

Таблица `orders` и 1 000 000 строк создаются скриптом `scripts/lab01_orders_setup.sql`.

После вставки выполняется:

```sql
ANALYZE orders;
```

Это нужно, чтобы PostgreSQL обновил статистику таблицы и мог строить планы на основании актуального распределения данных.

### Задание 3. EXPLAIN

Запрос:

```sql
EXPLAIN
SELECT * FROM orders WHERE user_id = 123;
```

До создания индекса ожидаемый план - `Seq Scan`, потому что PostgreSQL не имеет структуры доступа по `user_id` и вынужден проверить строки таблицы.

### Задание 4. EXPLAIN ANALYZE

Запрос:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = 123;
```

`EXPLAIN` показывает ожидаемый план без выполнения запроса. `EXPLAIN ANALYZE` реально выполняет запрос и добавляет фактические значения: `actual time`, `actual rows`, `Planning Time`, `Execution Time`.

### Задание 5. Sequential Scan

Запросы:

```sql
SELECT * FROM orders;
SELECT * FROM orders WHERE amount > 0;
```

Ожидаемый результат - `Seq Scan`. Для чтения всей таблицы или почти всей таблицы последовательное сканирование обычно выгоднее индекса: меньше случайного чтения, проще доступ к страницам, индекс не дает сильного сокращения набора строк.

### Задание 6. Первый B-tree индекс

Индекс:

```sql
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

Проверяем:

```sql
SELECT * FROM orders WHERE user_id = 123;
```

Ожидаем переход от `Seq Scan` к `Index Scan` или `Bitmap Heap Scan`, потому что условие по `user_id` селективное.

| Метрика | До индекса | После индекса |
| --- | --- | --- |
| Тип Scan | `Parallel Seq Scan` | `Bitmap Heap Scan` + `Bitmap Index Scan` |
| Execution Time | `37.854 ms` | `0.105 ms` |
| Actual Rows | `7` | `7` |
| Используемый индекс | нет | `idx_orders_user_id` |

Вывод: индекс по `user_id` резко уменьшил время выполнения, потому что запрос выбирает только 7 строк из 1 000 000.

### Задание 7-8. Индекс и низкая селективность

Индекс:

```sql
CREATE INDEX idx_orders_status ON orders(status);
```

Запросы:

```sql
SELECT * FROM orders WHERE status = 'PAID';
SELECT * FROM orders WHERE status = 'NEW';
SELECT * FROM orders WHERE status = 'DELIVERED';
SELECT * FROM orders WHERE status = 'CANCELLED';
```

Распределение:

```sql
SELECT status, COUNT(*) FROM orders GROUP BY status;
```

Фактическое распределение:

| Status | Rows |
| --- | ---: |
| `NEW` | `250728` |
| `CANCELLED` | `250148` |
| `PAID` | `249737` |
| `DELIVERED` | `249387` |

PostgreSQL использовал `Bitmap Heap Scan` + `Bitmap Index Scan`, но запросы все равно возвращали примерно четверть таблицы. Это низкая селективность: индекс помогает найти TID строк, но читать приходится очень много heap-страниц.

### Задание 9. Range Query

Индекс:

```sql
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

Исследуем диапазоны:

```sql
created_at > NOW() - INTERVAL '1 day'
created_at > NOW() - INTERVAL '7 days'
created_at > NOW() - INTERVAL '1 month'
created_at > NOW() - INTERVAL '1 year'
```

Вывод: чем шире временной диапазон, тем меньше пользы от индекса. При очень широком диапазоне PostgreSQL может выбрать последовательное сканирование.

Фактические результаты:

| Диапазон | План | Execution Time |
| --- | --- | ---: |
| до индекса, 7 дней | `Parallel Seq Scan` | `59.410 ms` |
| 1 день | `Bitmap Heap Scan` | `1.683 ms` |
| 7 дней | `Bitmap Heap Scan` | `7.902 ms` |
| 1 месяц | `Bitmap Heap Scan` | `23.093 ms` |
| 1 год | `Seq Scan` | `190.196 ms` |

### Задание 10. Bitmap Scan

Кандидат:

```sql
SELECT * FROM orders WHERE amount BETWEEN 1000 AND 3000;
```

Индекс:

```sql
CREATE INDEX idx_orders_amount ON orders(amount);
```

`Bitmap Index Scan` собирает bitmap подходящих строк по индексу. `Bitmap Heap Scan` затем читает нужные страницы таблицы. Такой план удобен, когда строк больше, чем для точечного `Index Scan`, но меньше, чем для выгодного `Seq Scan`.

Фактически запрос `amount BETWEEN 1000 AND 3000` до индекса выполнялся через `Seq Scan` за `101.007 ms`, после создания `idx_orders_amount` - через `Bitmap Heap Scan` за `64.383 ms`.

### Задание 11-12. Несколько индексов и составной индекс

Запрос:

```sql
SELECT * FROM orders
WHERE user_id = 123
  AND status = 'PAID';
```

Сравниваются отдельные индексы `idx_orders_user_id`, `idx_orders_status` и составной индекс:

```sql
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
```

Составной индекс часто эффективнее для запроса, который одновременно фильтрует по обеим колонкам, но он не всегда заменяет отдельные индексы для других запросов.

Фактическое сравнение:

| Вариант | План | Execution Time |
| --- | --- | ---: |
| отдельные индексы | `Bitmap Heap Scan` по `idx_orders_user_id`, затем фильтр `status` | `0.114 ms` |
| составной индекс | `Index Scan using idx_orders_user_status` | `0.037 ms` |

### Задание 13. Порядок колонок в составном индексе

Индексы:

```sql
CREATE INDEX idx_orders_user_created_at ON orders(user_id, created_at);
CREATE INDEX idx_orders_created_at_user ON orders(created_at, user_id);
```

Порядок важен: индекс `(user_id, created_at)` хорошо подходит для фильтрации по `user_id` и затем по диапазону времени. Индекс `(created_at, user_id)` лучше подходит для запросов, где главным условием является диапазон времени.

### Задание 14-15. WHERE + ORDER BY + LIMIT

Запрос:

```sql
SELECT * FROM orders
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 20;
```

Индекс:

```sql
CREATE INDEX idx_orders_user_created_at_desc
ON orders(user_id, created_at DESC);
```

Такой индекс позволяет PostgreSQL быстро найти строки пользователя уже в нужном порядке и остановиться после `LIMIT 20`.

В данном наборе данных для `user_id = 123` нашлось всего 7 строк, поэтому PostgreSQL продолжил использовать `Bitmap Heap Scan` и дешевый `Sort`. Время осталось очень маленьким: `0.071 ms` до индекса и `0.051 ms` для варианта с `LIMIT 20`. Этот результат важен: индекс не обязан использоваться именно так, как мы ожидаем, если планировщик считает другой план дешевле.

### Задание 16. Index Only Scan

Запрос:

```sql
SELECT id, user_id FROM orders WHERE user_id = 123;
```

Дополнительный индекс:

```sql
CREATE INDEX idx_orders_user_id_include
ON orders(user_id) INCLUDE (id, status, created_at);
```

`Index Only Scan` возможен, если нужные колонки есть в индексе и visibility map позволяет не читать heap-страницы таблицы.

Фактически после `VACUUM (ANALYZE)` и индекса `idx_orders_user_id_include` PostgreSQL выбрал `Index Only Scan`, время уменьшилось с `0.109 ms` до `0.040 ms`.

### Задание 17. Partial Index

Запрос:

```sql
SELECT * FROM orders
WHERE status = 'NEW'
ORDER BY created_at;
```

Индекс:

```sql
CREATE INDEX idx_orders_new
ON orders(created_at)
WHERE status = 'NEW';
```

Partial index меньше обычного индекса и полезен, если запросы часто обращаются к небольшой подвыборке строк.

На равномерном распределении `status = 'NEW'` занимает около 25% таблицы, поэтому partial index не дал выигрыша: до него запрос занял `127.599 ms`, после - `159.660 ms`. Причина в том, что предикат оказался не маленькой подвыборкой, а большой частью таблицы.

### Задание 18. Expression Index

Запрос:

```sql
SELECT * FROM lab_users WHERE LOWER(email) = 'test@example.com';
```

Индекс:

```sql
CREATE INDEX idx_lab_users_lower_email
ON lab_users(LOWER(email));
```

Обычный индекс по `email` не обязан использоваться для `LOWER(email)`, потому что в запросе применяется выражение, а не исходное значение колонки.

Фактически обычный индекс `idx_lab_users_email` не помог: был `Seq Scan` по 100 000 строк за `24.301 ms`. После создания `idx_lab_users_lower_email` план стал `Index Scan`, время - `0.031 ms`.

### Задание 19. Цена индексов

Сравниваются вставки в две таблицы:

- `orders_insert_no_indexes`
- `orders_insert_with_indexes`

Вывод: индексы ускоряют чтение, но замедляют запись, потому что при `INSERT`, `UPDATE`, `DELETE` PostgreSQL должен поддерживать индексные структуры.

Фактическое измерение массовой вставки 100 000 строк:

| Таблица | Индексы | Execution Time |
| --- | --- | ---: |
| `orders_insert_no_indexes` | только PK | `366.586 ms` |
| `orders_insert_with_indexes` | PK + 3 дополнительных индекса | `911.779 ms` |

### Задание 20. Статистика индексов

Запрос:

```sql
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

`idx_scan = 0` не всегда означает, что индекс бесполезен: он мог быть создан недавно, использоваться редким критичным запросом или быть нужен для constraint.

Фактически часть новых индексов имела `idx_scan = 0`, потому что они были созданы во время лабораторной и не все запросы успели их использовать. Удалять индекс только по одному снимку `idx_scan` нельзя.

### Задание 21. Финальная оптимизация

Запрос:

```sql
SELECT id, amount, status, created_at
FROM orders
WHERE user_id = 123
  AND status = 'PAID'
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC
LIMIT 50;
```

Индекс:

```sql
CREATE INDEX idx_orders_user_status_created_at_desc
ON orders(user_id, status, created_at DESC);
```

Порядок колонок выбран так:

- `user_id` - точечный фильтр;
- `status` - второй точечный фильтр;
- `created_at DESC` - диапазон и сортировка.

Фактически до финального индекса использовался `idx_orders_user_created_at_desc`, а `status` применялся как фильтр. После создания `idx_orders_user_status_created_at_desc` все три условия вошли в `Index Cond`. На конкретном `user_id = 123` строк за последние 30 дней со статусом `PAID` не оказалось, поэтому время осталось микроскопическим: `0.037 ms` до и `0.058 ms` после. Главное изменение здесь - не время, а структура плана.

## Часть 2. Работа со своим сервисом

### Scaling Entity

Основная сущность для масштабирования: `bookings`.

`bookings` отвечает за бронирования пользователей на мероприятия. Эта таблица будет расти быстрее остальных, потому что каждое действие бронирования создает новую запись, а пользователи могут делать много бронирований на разные мероприятия.

Ожидаемый объем через год: от сотен тысяч до миллионов записей, в зависимости от числа пользователей и мероприятий.

Часто используемые поля:

- `user_id`
- `event_id`
- `status`
- `created_at`

### Исследуемые реальные запросы

Query 1:

```sql
SELECT *
FROM bookings
WHERE user_id = $1;
```

Query 2:

```sql
SELECT *
FROM bookings
WHERE event_id = $1
  AND status = $2;
```

Query 3:

```sql
SELECT *
FROM bookings
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 20;
```

### Базовое измерение

Результаты зафиксированы в двух файлах:

```bash
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-before-output.txt
psql "$LOCAL_DATABASE_URL" -f scripts/lab01_service_explain.sql | tee docs/lab-01-service-after-output.txt
```

| Запрос | Тип Scan | Execution Time | Используемые индексы |
| --- | --- | --- | --- |
| Query 1 до | `Bitmap Heap Scan` | `3.943 ms` | `idx_bookings_user_id` |
| Query 2 до | `Bitmap Heap Scan` | `0.041 ms` | `idx_bookings_event_id` + фильтр `status` |
| Query 3 до | `Index Scan Backward` | `0.704 ms` | `idx_bookings_created_at`, фильтр `user_id` |
| Query 1 после | `Bitmap Heap Scan` | `3.767 ms` | `idx_bookings_user_id` |
| Query 2 после | `Index Scan` | `0.071 ms` | `idx_bookings_event_status_created_at_desc` |
| Query 3 после | `Index Scan` | `0.050 ms` | `idx_bookings_user_created_at_desc` |

Перед финальным измерением был добавлен горячий сценарий: 50 000 дополнительных бронирований для `user_id = 123`. Это делает pagination-запрос реалистичным и показывает эффект составного индекса.

### Добавленные индексы сервиса

Индексы добавлены через goose-миграцию `migrations/202609120001_lab01_booking_indexes.sql`.

```sql
CREATE INDEX idx_bookings_user_created_at_desc
    ON bookings(user_id, created_at DESC);

CREATE INDEX idx_bookings_event_status_created_at_desc
    ON bookings(event_id, status, created_at DESC);
```

Первый индекс оптимизирует endpoint вида:

```http
GET /api/users/{id}/bookings
```

и pagination-запрос:

```sql
SELECT *
FROM bookings
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 20;
```

Второй индекс оптимизирует фильтрацию бронирований по мероприятию и статусу:

```sql
SELECT *
FROM bookings
WHERE event_id = $1
  AND status = $2;
```

### Повторное измерение

| Метрика | До | После |
| --- | --- | --- |
| Тип Scan | `Index Scan Backward` по `created_at` + фильтр `user_id` | `Index Scan` по `(user_id, created_at DESC)` |
| Execution Time | `0.704 ms` | `0.050 ms` |
| Actual Rows | `20` | `20` |
| Используемый индекс | `idx_bookings_created_at` | `idx_bookings_user_created_at_desc` |

Итог: pagination-запрос стал примерно в 14 раз быстрее. До оптимизации PostgreSQL шел по индексу времени и отбрасывал строки других пользователей. После оптимизации он сразу читает строки нужного пользователя в порядке `created_at DESC`.

## Почему нельзя индексировать всё?

Нельзя создать индексы на всех колонках и считать задачу решенной, потому что:

- каждый индекс занимает место на диске;
- индексы увеличивают стоимость хранения;
- при `INSERT` нужно добавить запись не только в таблицу, но и во все подходящие индексы;
- при `UPDATE` индексы могут перестраиваться, если изменились индексируемые колонки;
- при `DELETE` PostgreSQL должен учитывать удаление строк из индексных структур;
- лишние индексы замедляют запись;
- PostgreSQL все равно использует только те индексы, которые подходят под реальные запросы и достаточно селективны.

Индекс должен появляться из измеренной проблемы, а не из желания покрыть все колонки заранее.
