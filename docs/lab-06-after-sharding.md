# Лабораторная работа №6. Запросы и архитектура после шардирования

## Цель

Понять, как меняется backend-сервис после шардирования: какие запросы остаются single-shard, какие становятся distributed, где нужен merge в приложении, что происходит с JOIN, `ORDER BY LIMIT`, отказом shard и hot shard.

Файлы:

- `cmd/lab06/main.go` - runner для демонстрации запросов после шардирования.
- `docs/lab-06-after-sharding-output.txt` - команда запуска и статус текущего прогона.
- `internal/sharding/router.go` - router, который выбирает shard по `user_id`.
- `docker-compose.shards.yml` - shard PostgreSQL стенд.

В лабораторной используется результат лабораторной №5: сущность `bookings` распределяется по shard key `user_id`.

## Архитектура после шардирования

До шардирования backend отправлял SQL-запросы в один PostgreSQL. После шардирования появляется router:

```text
Backend
  -> Router by user_id
    -> Shard 0
    -> Shard 1
    -> Shard 2
```

Router нужен, чтобы по shard key определить, в какую БД идти.

Для нашей схемы:

```text
shard = hash(user_id) % 3
```

## Single-Shard Query

Пример single-shard запроса в сервисе:

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

Endpoint:

```text
GET /api/users/{id}/bookings
```

Почему это single-shard:

- shard key - `user_id`;
- в запросе есть `WHERE b.user_id = $1`;
- router может вычислить shard до выполнения SQL;
- остальные shard не нужны.

В `cmd/lab06` этот сценарий демонстрируется запросом:

```sql
SELECT COUNT(*), COALESCE(SUM(total), 0)
FROM bookings_sharded
WHERE user_id = $1;
```

Фактический прогон:

```text
Sample user_id: 36697
Router result: shard-1
SQL executed only on shard-1
Result: count=9 total=209462
```

## Агрегирующий запрос

В сервисе есть агрегирующий запрос:

```sql
SELECT $1::bigint AS event_id,
       COUNT(*) AS bookings,
       COALESCE(SUM(seats), 0) AS seats,
       COALESCE(SUM(total), 0) AS revenue,
       COALESCE(AVG(total), 0)::float AS average_total
FROM bookings
WHERE event_id = $1;
```

Endpoint:

```text
GET /api/events/{id}/stats
```

После шардирования по `user_id` этот запрос не является single-shard, потому что `event_id` не совпадает с shard key. Бронирования одного мероприятия могут лежать на всех shard.

Правильная схема:

```text
Shard 0 -> partial COUNT/SUM
Shard 1 -> partial COUNT/SUM
Shard 2 -> partial COUNT/SUM
        -> backend merge
        -> final COUNT/SUM/AVG
```

Где объединяются результаты: в backend-сервисе или в отдельном query/aggregation layer.

Что происходит со временем выполнения:

- каждый shard выполняет свою часть параллельно или последовательно;
- появляется сетевой overhead;
- backend тратит время на merge;
- итоговая задержка зависит от самого медленного shard.

В `cmd/lab06` distributed aggregation показан на:

```sql
SELECT status, COUNT(*), SUM(seats), SUM(total)
FROM bookings_sharded
GROUP BY status;
```

Каждый shard возвращает частичный результат, backend суммирует строки с одинаковым `status`.

Фактический merged result:

```text
CANCELLED count=33504 seats=100119 total=549288943
PAID      count=33342 seats=100638 total=552809090
PENDING   count=33154 seats=99363  total=547587851
```

## JOIN между shard

В сервисе есть JOIN:

```sql
SELECT b.id, b.user_id, b.event_id, b.status, b.seats, b.total, b.created_at, b.updated_at,
       u.email, e.title, v.name, v.city, e.starts_at
FROM bookings b
JOIN users u ON u.id = b.user_id
JOIN events e ON e.id = b.event_id
JOIN venues v ON v.id = e.venue_id
WHERE b.user_id = $1;
```

Если `bookings` шардированы по `user_id`, то бронирования пользователя находятся на одном shard. Но связанные данные могут быть устроены по-разному:

- `users` можно шардировать по `id`, тогда пользователь и его bookings могут быть co-located;
- `events` и `venues` лучше держать как reference data и реплицировать на все shard;
- если `events` тоже шардировать отдельно, JOIN `bookings -> events` может стать cross-shard.

Что если связанные записи на разных shard:

- обычный SQL JOIN внутри одного PostgreSQL не сработает;
- backend должен сходить в несколько shard и соединить данные сам;
- либо нужны replicated reference tables;
- либо нужна отдельная distributed SQL система.

Можно ли выбрать shard key так, чтобы JOIN чаще был локальным: да. Для пользовательских запросов `user_id` хороший ключ, потому что `users` и `bookings` можно co-locate по пользователю. Для запросов по мероприятиям лучше подошел бы `event_id`, но тогда хуже стали бы пользовательские запросы.

## ORDER BY + LIMIT

В сервисе есть список бронирований:

```sql
SELECT id, user_id, event_id, status, seats, total, created_at, updated_at
FROM bookings
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;
```

Endpoint:

```text
GET /api/bookings?sort=-created_at&page=1&pageSize=20
```

Если в запросе нет `user_id`, router не может выбрать один shard. Нужно обращаться ко всем shard:

```text
Shard 0 -> local top 20
Shard 1 -> local top 20
Shard 2 -> local top 20
        -> backend merge by created_at
        -> global top 20
```

Почему недостаточно взять первые 20 с одного shard: самые свежие записи могут находиться на любом shard. Если смотреть только один shard, результат будет неправильным глобально.

В `cmd/lab06` этот сценарий реализован так: каждый shard возвращает local top N, backend сортирует общий список candidates и выбирает global top N.

Фактический прогон:

```text
shard-0 returned local top 10
shard-1 returned local top 10
shard-2 returned local top 10
Backend merged candidates and selected global top 10
```

## Отказ одного shard

Ситуация:

```text
Shard 0 - OK
Shard 1 - OK
Shard 2 - DOWN
```

Что становится недоступно:

- все `bookings`, чей `user_id` маршрутизируется на `shard-2`;
- single-shard запросы по этим пользователям;
- часть результатов глобальных запросов.

Какие endpoint перестанут работать полностью или частично:

- `GET /api/users/{id}/bookings` - не работает для пользователей на упавшем shard;
- `GET /api/bookings?user_id=...` - не работает, если user_id ведет на упавший shard;
- `POST /api/bookings` - не работает для user_id, который должен записаться в упавший shard;
- `GET /api/events/{id}/stats` - либо ошибка, либо partial result без данных с упавшего shard;
- `GET /api/bookings` без user_id - partial result или ошибка.

Продолжит ли работать остальная часть сервиса: да, для пользователей и данных, которые находятся на живых shard. Но distributed queries должны явно уметь работать с partial failure.

Что должен делать backend:

- быстро определять недоступный shard;
- возвращать понятную ошибку для single-shard запроса;
- для distributed query решать: fail whole request или вернуть partial result с предупреждением;
- логировать ошибку;
- иметь timeout и circuit breaker.

Как повысить отказоустойчивость:

- реплика на каждый shard;
- automatic failover;
- backups;
- health-check shard;
- retry с лимитом;
- read replicas для read-only нагрузки;
- consistent hashing с контролируемой миграцией при замене shard.

## Hot Shard

Пример:

```text
Shard 0 -> 10% запросов
Shard 1 -> 15% запросов
Shard 2 -> 75% запросов
```

Причины:

- популярный пользователь создает много запросов;
- неудачный shard key;
- данные распределены ровно, но нагрузка нет;
- один тип запросов чаще попадает в один диапазон ключей;
- отдельный tenant стал крупнее остальных.

Почему равное количество строк не гарантирует равную нагрузку:

- разные пользователи имеют разную активность;
- одна строка может читаться тысячу раз, другая ни разу;
- тяжелые запросы могут концентрироваться на одном shard;
- размер строк и индексов может отличаться.

Что делать:

- мониторить QPS/latency per shard;
- добавить virtual nodes;
- вынести hot user/tenant отдельно;
- поменять shard key;
- добавить caching;
- разделить чтение и запись;
- использовать replica для hot shard.

## Итоговый анализ shard key

Выбранный shard key `user_id` подходит для сервиса частично хорошо.

Плюсы:

- эффективны запросы бронирований пользователя;
- запись бронирования сразу маршрутизируется по `user_id`;
- пользовательские сценарии не требуют fan-out;
- распределение в лабораторной №5 получилось ровным: около 33% на shard.

Минусы:

- статистика по мероприятию становится distributed;
- список бронирований без `user_id` требует fan-out;
- запросы по `event_id` не попадают в один shard;
- JOIN с `events` и `venues` требует replicated reference data или merge в backend.

Проблемные операции:

- `JOIN` - сложно, если связанные таблицы не co-located;
- `aggregation` - нужны partial aggregates и merge;
- `ORDER BY LIMIT` - нужен global merge;
- `migration` - при изменении shard count данные надо переносить;
- `backup` - нужно согласовывать несколько БД;
- `restore` - восстановление одного shard влияет на часть пользователей;
- `balancing` - нужно следить не только за строками, но и за нагрузкой.

Если проектировать систему заново, я бы оставила `user_id` как shard key для booking-сервиса, потому что основной пользовательский сценарий - посмотреть и создать бронирования пользователя. Но для аналитики по мероприятиям я бы сразу проектировала отдельный read model или analytics pipeline, потому что `event_id`-агрегации плохо ложатся на шардирование по `user_id`.

## Вопросы для самопроверки

Single-shard query выполняется на одном shard, потому что содержит shard key. Distributed query требует обращения к нескольким shard.

JOIN между shard сложнее обычного JOIN, потому что один PostgreSQL не видит таблицы другого PostgreSQL.

`COUNT(*)` по всем shard выполняется как partial count на каждом shard плюс сумма в backend.

`ORDER BY LIMIT` требует объединения результатов, потому что top N может находиться на любом shard.

При отказе одного shard недоступна часть данных, соответствующая ключам этого shard.

Hot shard - shard, который получает непропорционально большую нагрузку.

Выбор shard key влияет на JOIN, потому что связанные данные могут оказаться co-located или разнесены по разным БД.

Плохо подходят для распределенных данных: cross-shard JOIN, global aggregation, global sort, transactions across shards.

При изменении количества shard часть данных нужно перенести. Для `hash % N` переносится много данных, для consistent hashing меньше.

Шардирование делит данные между БД, а репликация копирует одни и те же данные на другие узлы.

Шардирование может ускорить отдельный запрос, если он стал single-shard и работает по меньшему объему данных. Но distributed query может стать медленнее из-за fan-out и merge.
