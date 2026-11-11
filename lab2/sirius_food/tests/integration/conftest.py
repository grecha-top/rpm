"""Real PostgreSQL fixtures for integration tests."""
import os
import subprocess
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_engine():
    with PostgresContainer("postgres:15-alpine") as postgres:
        database_url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = database_url
        os.environ["CELERY_TASKS_SYNC"] = "true"
        os.environ["OTEL_ENABLED"] = "false"
        env = os.environ.copy()
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)

        import app.database as database

        database.engine.dispose()
        engine = create_engine(database_url)
        database.engine = engine
        database.SessionLocal.configure(bind=engine)
        yield engine
        engine.dispose()


@pytest.fixture
def db(postgres_engine):
    connection = postgres_engine.connect()
    outer_transaction = connection.begin()
    Session = sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = Session()
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@dataclass
class Scenario:
    client: TestClient
    user: object
    item: object


@pytest.fixture
def scenario(db, monkeypatch):
    from app.core.dependencies import get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import MenuItem, Role, User
    from app.tasks.dispatcher import CeleryOrderTaskDispatcher

    role = db.query(Role).filter_by(name="student").one()
    user = User(
        email="integration@example.com",
        password_hash="not-used",
        balance=1000.0,
        role_id=role.id,
    )
    item = MenuItem(name="Integration syrniki", price=150.0, is_available=True)
    db.add_all([user, item])
    db.flush()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(
        CeleryOrderTaskDispatcher,
        "dispatch_order_created",
        lambda *args, **kwargs: None,
    )
    with TestClient(app) as client:
        yield Scenario(client=client, user=user, item=item)
    app.dependency_overrides.clear()
