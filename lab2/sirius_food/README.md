# Лабораторная работа 2

Проект `Sirius.Food API` разложен из текста задания в рабочую структуру FastAPI-приложения.

## Что изменено

- Модуль `orders` вынесен в три слоя: `router.py`, `service.py`, `repository.py`.
- Модуль `users` также вынесен в три слоя как самостоятельная часть лабораторной работы.
- В `service.py` модулей `orders` и `users` нет импортов `fastapi` и `sqlalchemy`.
- Репозитории передаются в сервисы через конструктор.
- Добавлены unit-тесты для `users/service.py`, которые используют fake-репозиторий и не требуют запуска PostgreSQL.

## Путь запроса через слои

```text
HTTP request
    |
    v
router.py
    |
    | создает repository и service,
    | выполняет техническую HTTP-валидацию,
    | переводит исключения Python в HTTPException
    v
service.py
    |
    | выполняет бизнес-правила,
    | не знает о FastAPI и SQLAlchemy
    v
repository.py
    |
    | выполняет SQLAlchemy-запросы и транзакции
    v
PostgreSQL
```

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d db redis
uvicorn app.main:app --reload
```

Swagger UI будет доступен по адресу:

```text
http://127.0.0.1:8000/docs
```

## Тесты

```bash
pytest
```
