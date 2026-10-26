"""Test setup.

Tests run against the database in TEST_DATABASE_URL (PostgreSQL in CI). Locally, if it
is not set, they fall back to an in-memory SQLite database so `pytest` works anywhere.
Each test gets fresh tables.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.security import hash_password

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

if TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    engine = create_engine(TEST_DATABASE_URL)

TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, email: str, role: Role) -> User:
    user = User(
        email=email, full_name=email.split("@")[0].title(), role=role, hashed_password=hash_password("password123")
    )
    db.add(user)
    db.commit()
    return user


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/token", data={"username": email, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client, db):
    _make_user(db, "admin@example.com", Role.admin)
    return _auth_headers(client, "admin@example.com")


@pytest.fixture()
def teacher_headers(client, db):
    _make_user(db, "teacher@example.com", Role.teacher)
    return _auth_headers(client, "teacher@example.com")
