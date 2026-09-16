# Лабораторная работа №2
# Когда индексов недостаточно: производительность PostgreSQL при росте данных

## Цель

Исследовать, как рост объема данных влияет на производительность PostgreSQL: планы выполнения, время запросов, размер таблиц, размер индексов, операции `SELECT`, `INSERT`, агрегации и запросы реального сервиса.

Полные выводы `EXPLAIN ANALYZE` сохранены в файлах:

- `docs/lab-02-events-010k-before.txt`
- `docs/lab-02-events-100k-before.txt`
- `docs/lab-02-events-1m-before.txt`
- `docs/lab-02-events-5m-before.txt`
- `docs/lab-02-events-5m-after.txt`
- `docs/lab-02-insert-cost-output.txt`
- `docs/lab-02-bookings-current.txt`
- `docs/lab-02-bookings-5m.txt`

## Подготовка

Экспериментальная таблица создана в отдельной схеме `lab02`, чтобы не конфликтовать с таблицей `public.events` из сервиса.

```sql
CREATE SCHEMA lab02;

CREATE TABLE lab02.events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL
);
```

Скрипты лабораторной:

- `scripts/lab02_events_setup.sql`
- `scripts/lab02_events_insert.sql`
- `scripts/lab02_events_measure.sql`
- `scripts/lab02_events_create_indexes.sql`
- `scripts/lab02_insert_cost.sql`
- `scripts/lab02_bookings_measure.sql`
- `scripts/lab02_bookings_insert_to_target.sql`

## Часть A. Экспериментальная таблица `lab02.events`

### Задание 1-2. Создание таблицы и генерация данных

Данные генерировались через `generate_series()`.

Контрольные точки:

- 10 000 строк;
- 100 000 строк;
- 1 000 000 строк;
- 5 000 000 строк.

10 000 000 строк не создавались: для целей лабораторной хватило точки 5M, на которой уже видно влияние роста данных и ограничения индексов.

### Задание 3. Размер таблицы

| Количество строк | Размер таблицы | Общий размер до индексов | Общий размер после индексов |
| ---: | ---: | ---: | ---: |
| 10 000 | 672 kB | 944 kB | - |
| 100 000 | 6672 kB | 8912 kB | - |
| 1 000 000 | 65 MB | 87 MB | - |
| 5 000 000 | 326 MB | 433 MB | 724 MB |

Вывод: размер таблицы растет почти линейно с количеством строк. После создания индексов общий размер на 5M строк вырос с `433 MB` до `724 MB`.

### Задание 4. SELECT без дополнительного индекса

Запрос:

```sql
SELECT *
FROM lab02.events
WHERE user_id = 123;
```

| Количество строк | Scan | Actual Rows | Rows Removed by Filter | Execution Time |
| ---: | --- | ---: | ---: | ---: |
| 10 000 | `Seq Scan` | 0 | 10 000 | 0.232 ms |
| 100 000 | `Seq Scan` | 0 | 100 000 | 2.282 ms |
| 1 000 000 | `Parallel Seq Scan` | 6 | 999 993 | 12.403 ms |
| 5 000 000 | `Parallel Seq Scan` | 43 | 4 999 956 | 50.712 ms |

Вывод: без индекса PostgreSQL вынужден проверять всю таблицу. Время растет вместе с объемом данных.

### Задание 5. Добавление индекса

Индекс:

```sql
CREATE INDEX idx_lab02_events_user_id
ON lab02.events(user_id);
```

На 5M строк PostgreSQL использовал не отдельный `idx_lab02_events_user_id`, а составной `idx_lab02_events_user_created`, потому что его первый столбец тоже `user_id`.

| Объем | Без индекса | С индексом | Разница |
| ---: | ---: | ---: | ---: |
| 5 000 000 | 50.712 ms | 0.194 ms | примерно в 261 раз быстрее |

План изменился с `Parallel Seq Scan` на `Bitmap Heap Scan` + `Bitmap Index Scan`. Индекс сработал хорошо, потому что условие `user_id = 123` возвращает маленькую часть таблицы.

### Задание 6. Поиск по диапазону дат

Запрос:

```sql
SELECT *
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '1 day';
```

Индекс:

```sql
CREATE INDEX idx_lab02_events_created_at
ON lab02.events(created_at);
```

| Объем | План | Execution Time |
| ---: | --- | ---: |
| 5M без индекса | `Parallel Seq Scan` | 138.490 ms |
| 5M с индексом | `Bitmap Heap Scan` + `Bitmap Index Scan` | 45.472 ms |

Вывод: индекс полезен для небольшого диапазона. Но если диапазон возвращает большую часть таблицы, PostgreSQL все равно должен прочитать много heap-страниц, и индекс перестает быть радикальным решением.

### Задание 7. Фильтрация и сортировка

Запрос:

```sql
SELECT *
FROM lab02.events
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 100;
```

Индекс:

```sql
CREATE INDEX idx_lab02_events_user_created
ON lab02.events(user_id, created_at DESC);
```

| Объем | План | Sort | Execution Time |
| ---: | --- | --- | ---: |
| 5M без индекса | `Parallel Seq Scan` + `Sort` | есть | 54.554 ms |
| 5M с индексом | `Bitmap Heap Scan` + `Sort` | есть | 0.207 ms |

PostgreSQL все равно оставил `Sort`, потому что для `user_id = 123` найдено всего 43 строки и отсортировать их дешево. Но основная проблема исчезла: больше не нужно читать всю таблицу.

Порядок колонок важен: `user_id` стоит первым, потому что запрос сначала фильтрует по пользователю, а `created_at DESC` нужен для выдачи последних событий.

### Задание 8. Агрегация

Запрос:

```sql
SELECT event_type, COUNT(*)
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_type;
```

| Объем | План | Execution Time |
| ---: | --- | ---: |
| 10k | `Seq Scan` + `HashAggregate` | 1.904 ms |
| 100k | `Seq Scan` + `HashAggregate` | 8.062 ms |
| 1M | `Parallel Seq Scan` + `Partial HashAggregate` + `Finalize GroupAggregate` | 30.213 ms |
| 5M без индекса | `Parallel Seq Scan` + aggregate | 163.213 ms |
| 5M с индексом | `Parallel Bitmap Heap Scan` + aggregate | 84.512 ms |

Индекс на `created_at` уменьшил время, но не решил проблему полностью: PostgreSQL все равно должен обработать примерно 410 869 строк за 30 дней и сгруппировать их по `event_type`.

### Задание 9. Стоимость индексов для INSERT

Вставка 100 000 строк:

| Таблица | Индексы | Execution Time |
| --- | --- | ---: |
| `lab02.insert_no_indexes` | только primary key | 95.452 ms |
| `lab02.insert_with_indexes` | primary key + 3 дополнительных индекса | 311.814 ms |

Вывод: дополнительные индексы замедлили вставку примерно в 3.3 раза. При добавлении каждой строки PostgreSQL должен обновить не только таблицу, но и все индексные структуры.

### Задание 10. Размер индексов

На 5M строк:

| Индекс | Размер |
| --- | ---: |
| `events_pkey` | 107 MB |
| `idx_lab02_events_created_at` | 107 MB |
| `idx_lab02_events_user_created` | 150 MB |
| `idx_lab02_events_user_id` | 34 MB |

Вывод: размер индексов растет вместе с таблицей. Составной индекс крупнее одиночного, потому что хранит больше данных в ключе.

### Задание 11. Когда индекс уже не спасает

Запрос:

```sql
SELECT DATE(created_at), COUNT(*)
FROM lab02.events
WHERE created_at >= NOW() - INTERVAL '365 days'
GROUP BY DATE(created_at);
```

На 5M строк после создания индексов PostgreSQL выбрал `Seq Scan`, потому что запрос возвращает почти всю таблицу:

- обработано примерно `4 999 996` строк;
- `Execution Time: 861.342 ms`;
- операция: `Seq Scan` + `HashAggregate`.

Если таблица будет содержать 100M строк, индекс на `created_at` не сделает запрос мгновенным: нужно обработать почти весь год данных, вычислить `DATE(created_at)` для каждой строки и выполнить группировку.

Возможные решения:

- партиционирование по времени;
- материализованные агрегаты;
- отдельная таблица дневной статистики;
- инкрементальное обновление счетчиков;
- ограничение диапазона запроса;
- архивирование старых данных;
- read replica для аналитических запросов.

## Часть B. Собственный сервис

### Задание 12. Выбор сущности

Выбранная сущность: `bookings`.

Текущее количество записей до роста: `1 050 003`.

После увеличения объема: `5 000 000`.

Почему выбрана эта сущность:

- каждое бронирование создает новую строку;
- таблица естественно растет быстрее справочников `users`, `venues`, `categories`;
- по ней есть реальные API-запросы;
- используются фильтры по `user_id`, `event_id`, `status`, `created_at`;
- она уже была основной scaling entity в проекте.

### Задание 13. Реальные запросы сервиса

Query 1 - поиск по внешнему ключу:

```sql
SELECT *
FROM public.bookings
WHERE user_id = 123;
```

Query 2 - диапазон дат:

```sql
SELECT *
FROM public.bookings
WHERE created_at >= NOW() - INTERVAL '30 days';
```

Query 3 - фильтрация + сортировка + limit:

```sql
SELECT *
FROM public.bookings
WHERE user_id = 123
ORDER BY created_at DESC
LIMIT 50;
```

Query 4 - агрегация:

```sql
SELECT event_id, COUNT(*) AS bookings, SUM(total) AS revenue
FROM public.bookings
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_id
ORDER BY revenue DESC
LIMIT 20;
```

### Задание 14-16. Baseline и сравнение производительности

Размеры таблицы:

| Объем | Размер таблицы | Общий размер |
| ---: | ---: | ---: |
| 1 050 003 | 93 MB | 230 MB |
| 5 000 000 | 444 MB | 1312 MB |

Сравнение запросов:

| Запрос | Объем данных | Execution Time | Scan | Индекс |
| --- | ---: | ---: | --- | --- |
| Query 1 | 1 050 003 | 3.940 ms | `Bitmap Heap Scan` | `idx_bookings_user_id` |
| Query 1 | 5 000 000 | 6.161 ms | `Bitmap Heap Scan` | `idx_bookings_user_id` |
| Query 2 | 1 050 003 | 35.411 ms | `Bitmap Heap Scan` | `idx_bookings_created_at` |
| Query 2 | 5 000 000 | 219.302 ms | `Bitmap Heap Scan` | `idx_bookings_created_at` |
| Query 3 | 1 050 003 | 0.044 ms | `Index Scan` | `idx_bookings_user_created_at_desc` |
| Query 3 | 5 000 000 | 0.208 ms | `Index Scan` | `idx_bookings_user_created_at_desc` |
| Query 4 | 1 050 003 | 41.139 ms | `Bitmap Heap Scan` + `HashAggregate` | `idx_bookings_created_at` |
| Query 4 | 5 000 000 | 263.664 ms | `Bitmap Heap Scan` + `HashAggregate` | `idx_bookings_created_at` |

### Задание 17. Узкое место

Сильнее всего от роста данных зависит Query 4:

```sql
SELECT event_id, COUNT(*) AS bookings, SUM(total) AS revenue
FROM public.bookings
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY event_id
ORDER BY revenue DESC
LIMIT 20;
```

На 5M строк:

- `Execution Time: 263.664 ms`;
- обработано `410 296` строк за последние 30 дней;
- используется `Bitmap Heap Scan` по `idx_bookings_created_at`;
- затем выполняется `HashAggregate`;
- затем `Sort` по `SUM(total)` для top-N.

Проблемное место: индекс помогает найти строки за 30 дней, но агрегация все равно должна прочитать сотни тысяч строк и сгруппировать их по `event_id`.

### Задание 18. Попытка улучшения

Для Query 3 уже используется правильный индекс:

```sql
CREATE INDEX idx_bookings_user_created_at_desc
ON bookings(user_id, created_at DESC);
```

Этот индекс сохраняет быстрый план даже при росте таблицы до 5M строк: `0.208 ms`.

Для Query 4 одного индекса недостаточно. Возможное улучшение:

```sql
CREATE INDEX idx_bookings_created_at_event_id
ON bookings(created_at, event_id);
```

Но даже такой индекс не устранит необходимость читать все бронирования за период и считать `SUM(total)`. Более правильное решение для роста данных - предагрегация.

Например:

```sql
CREATE TABLE booking_daily_stats (
    stat_date DATE NOT NULL,
    event_id BIGINT NOT NULL,
    bookings BIGINT NOT NULL,
    revenue BIGINT NOT NULL,
    PRIMARY KEY (stat_date, event_id)
);
```

Тогда тяжелый запрос по сырым данным заменяется чтением уже агрегированной таблицы.

### Задание 19. Когда индексов становится недостаточно

На измерениях видно:

- точечный запрос по `user_id` масштабируется нормально: `3.940 ms` -> `6.161 ms`;
- pagination-запрос с хорошим составным индексом остается быстрым: `0.044 ms` -> `0.208 ms`;
- диапазонный запрос по 30 дням растет заметно: `35.411 ms` -> `219.302 ms`;
- агрегация по 30 дням растет еще сильнее: `41.139 ms` -> `263.664 ms`.

Вывод: индексов становится недостаточно, когда запрос должен обработать большую долю таблицы или выполнить агрегацию по большому числу строк. В нашем сервисе это видно на Query 4: индекс на `created_at` помогает найти диапазон, но при 5M строк PostgreSQL все равно обрабатывает `410 296` строк и выполняет `HashAggregate`.

Для таких сценариев нужны другие подходы:

- партиционирование по `created_at`;
- материализованные представления;
- таблицы агрегатов;
- read replica для аналитики;
- ограничение периода запроса;
- фоновые job'ы для пересчета статистики.

## Размер индексов `bookings`

| Индекс | 1 050 003 строк | 5 000 000 строк |
| --- | ---: | ---: |
| `bookings_pkey` | 23 MB | 107 MB |
| `idx_bookings_created_at` | 9432 kB | 128 MB |
| `idx_bookings_event_id` | 12 MB | 42 MB |
| `idx_bookings_event_status_created_at_desc` | 44 MB | 293 MB |
| `idx_bookings_status` | 6648 kB | 31 MB |
| `idx_bookings_user_created_at_desc` | 32 MB | 224 MB |
| `idx_bookings_user_id` | 12 MB | 43 MB |

Вывод: индексы занимают существенный объем. На 5M строк общий размер `bookings` вместе с индексами - `1312 MB`, хотя сама таблица занимает `444 MB`.

## Контрольные вопросы

1. Почему Seq Scan не всегда является плохим планом?

Если запрос возвращает большую часть таблицы, последовательное чтение может быть дешевле случайных обращений через индекс.

2. Почему PostgreSQL может не использовать существующий индекс?

Планировщик оценивает стоимость. Если индекс низкоселективен или запрос возвращает много строк, `Seq Scan` может быть дешевле.

3. Что происходит с индексом при INSERT?

PostgreSQL добавляет запись не только в таблицу, но и во все индексы, где участвуют значения новой строки.

4. Почему большое количество индексов может замедлять запись?

Каждый индекс нужно обновлять при `INSERT`, части `UPDATE` и `DELETE`.

5. Что такое селективность?

Это доля строк, которую возвращает условие. Чем меньше доля, тем выше селективность.

6. Почему индекс хорошо работает для поиска небольшой части таблицы?

Он позволяет быстро найти нужные строки без чтения всей таблицы.

7. Почему индекс может быть менее полезен, если запрос возвращает большую часть таблицы?

Потому что после поиска в индексе все равно нужно прочитать много heap-страниц.

8. Зачем нужен EXPLAIN ANALYZE?

Он показывает фактический план выполнения, реальные времена, количество строк и операции.

9. Что означает Rows Removed by Filter?

Количество строк, которые были прочитаны, но отброшены условием `WHERE`.

10. Что означает Index Cond?

Условие, которое PostgreSQL смог применить непосредственно при поиске по индексу.

11. Чем Index Scan отличается от Bitmap Index Scan?

`Index Scan` сразу идет по индексу и читает строки. `Bitmap Index Scan` сначала строит bitmap подходящих строк, затем `Bitmap Heap Scan` читает страницы таблицы.

12. Почему порядок колонок в составном индексе имеет значение?

Индекс эффективно используется слева направо. Для `(user_id, created_at)` запрос по `user_id` подходит лучше, чем запрос только по `created_at`.

13. Почему запрос с GROUP BY может оставаться дорогим даже при наличии индекса?

Индекс помогает найти строки, но группировка требует обработать все найденные строки и построить агрегаты.

14. Как статистика влияет на выбор плана?

PostgreSQL использует статистику распределения данных для оценки количества строк и стоимости планов.

15. Что происходит с производительностью при росте таблицы?

Запросы, которые читают большую часть таблицы, становятся медленнее. Точечные запросы с хорошими индексами растут значительно медленнее.

16. Почему нельзя создавать индексы на все колонки?

Они занимают место, замедляют запись и не гарантируют ускорение запросов.

17. Как определить размер таблицы в PostgreSQL?

```sql
SELECT pg_size_pretty(pg_relation_size('table_name'));
```

18. Как определить размер индекса?

```sql
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE relname = 'table_name';
```
