# Примеры тел запросов для Postman

Базовый URL:

```text
http://localhost:8080
```

В Postman для запросов с телом выбери:

```text
Body -> raw -> JSON
```

Для `GET` и `DELETE` тело не нужно.

## Users

### POST /api/users

URL:

```text
http://localhost:8080/api/users
```

Body:

```json
{
  "email": "user@example.com",
  "full_name": "Ulyana Grechishnikova"
}
```

### PUT /api/users/{id}

URL:

```text
http://localhost:8080/api/users/1
```

Body:

```json
{
  "email": "updated-user@example.com",
  "full_name": "Updated User"
}
```

## Venues

### POST /api/venues

URL:

```text
http://localhost:8080/api/venues
```

Body:

```json
{
  "name": "Main Hall",
  "city": "Moscow",
  "address": "Tverskaya 1",
  "capacity": 1200
}
```

### PUT /api/venues/{id}

URL:

```text
http://localhost:8080/api/venues/1
```

Body:

```json
{
  "name": "Updated Hall",
  "city": "Moscow",
  "address": "Arbat 10",
  "capacity": 1500
}
```

## Events

### POST /api/events

URL:

```text
http://localhost:8080/api/events
```

Body:

```json
{
  "venue_id": 1,
  "title": "PostgreSQL Scaling Meetup",
  "status": "PUBLISHED",
  "starts_at": "2026-10-01T19:00:00Z",
  "base_price": 2500
}
```

### PUT /api/events/{id}

URL:

```text
http://localhost:8080/api/events/1
```

Body:

```json
{
  "venue_id": 1,
  "title": "PostgreSQL Scaling Meetup: Updated",
  "status": "PUBLISHED",
  "starts_at": "2026-10-01T20:00:00Z",
  "base_price": 3000
}
```

### POST /api/events/{id}/categories/{categoryID}

URL:

```text
http://localhost:8080/api/events/1/categories/1
```

Body не нужен. `event_id` и `category_id` передаются в URL.

## Categories

### POST /api/categories

URL:

```text
http://localhost:8080/api/categories
```

Body:

```json
{
  "name": "Tech"
}
```

### PUT /api/categories/{id}

URL:

```text
http://localhost:8080/api/categories/1
```

Body:

```json
{
  "name": "Technology"
}
```

## Bookings

### POST /api/bookings

URL:

```text
http://localhost:8080/api/bookings
```

Body:

```json
{
  "user_id": 1,
  "event_id": 1,
  "status": "PAID",
  "seats": 2,
  "total": 5000
}
```

### PUT /api/bookings/{id}

URL:

```text
http://localhost:8080/api/bookings/1
```

Body:

```json
{
  "user_id": 1,
  "event_id": 1,
  "status": "CANCELLED",
  "seats": 2,
  "total": 5000
}
```
---
localhost:55440
localhost:55441
localhost:55442
localhost:55443