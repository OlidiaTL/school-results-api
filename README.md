# School Results API

![CI](https://github.com/OlidiaTL/school-results-api/actions/workflows/ci.yml/badge.svg)

A REST API for recording secondary-school assessment results and flagging students who need early support. Built with **Python, FastAPI and PostgreSQL**, containerised with **Docker**, and tested in CI against a real Postgres database.

It is a standalone, simplified take on a problem I work on at [EdAn Labs](https://www.edalyticslabs.com), an education analytics platform for secondary schools: helping teachers spot a student who is slipping *before* the exam, not after it. All data in this repo is fictional.

## What it does

- **Staff authentication** with JWT bearer tokens and two roles: `admin` (manages users, students, subjects) and `teacher` (records and reads results).
- **Students and subjects**: create, read, update, delete, with filtering, name search and pagination.
- **Results**: one score per student, per subject, per term, validated (score 0–100, term format `2026-T2`) and protected against duplicates.
- **Student summary**: per-subject and overall averages for one student.
- **At-risk report**: flags students whose latest term average is below a threshold (default 50%) **or** has dropped sharply since the previous term (default 10 points).

## Architecture

```mermaid
flowchart LR
    C[Client / Swagger UI] -->|HTTPS + JWT| R[FastAPI routers<br/>auth · students · subjects · results]
    R --> D[Dependencies<br/>DB session · current user · role check]
    R --> S[Analytics service<br/>SQL aggregation + window functions]
    R --> M[SQLAlchemy 2.0 models]
    S --> M
    M --> P[(PostgreSQL 16)]
    A[Alembic migrations] --> P
```

```
app/
  main.py            app factory, router registration, /health
  config.py          settings from environment variables (pydantic-settings)
  database.py        engine, session factory, get_db dependency
  models.py          SQLAlchemy models: User, Student, Subject, Result
  schemas.py         Pydantic request/response models and validation
  security.py        bcrypt password hashing, JWT create/decode
  deps.py            auth dependencies: current user, role-based access
  routers/           one module per resource
  services/
    analytics.py     student summary and at-risk queries
alembic/             database migrations
scripts/seed.py      demo data (12 fictional students, 3 terms)
tests/               pytest suite (26 tests)
```

## Design decisions

- **The database does the aggregation.** The at-risk report averages scores per student per term in SQL, then uses a `ROW_NUMBER()` window function to keep only each student's two most recent terms. It is one query regardless of how many students there are, instead of loading every result into Python or querying once per student (the N+1 problem).
- **Constraints live in the schema, not only in the code.** A unique constraint on `(student_id, subject_id, term)` and check constraints on score and form range mean bad data is rejected even if two teachers submit at the same moment. The API turns the database error into a clear `409 Conflict`.
- **Indexes match the queries.** A composite index on `results(student_id, term)` supports the per-term grouping; `students.form` and `students.student_number` are indexed for filtering and lookups.
- **Role checks are a reusable dependency.** `require_role(Role.admin)` keeps permission logic out of route bodies, so each endpoint states who may call it in its signature.
- **Migrations are checked in CI.** The pipeline runs `alembic upgrade`, `alembic check` (fails if the models and migrations drift apart) and `alembic downgrade` before the tests.

## Run it with Docker

```bash
docker compose up --build
```

The API starts on <http://localhost:8000> and applies migrations automatically. Interactive docs are at <http://localhost:8000/docs>.

Load the demo data:

```bash
docker compose exec api python -m scripts.seed
```

Then click **Authorize** in the docs and log in as `teacher@example.com` / `teacher12345` (or `admin@example.com` / `admin12345`). Try `GET /results/at-risk`.

## Run it locally (without Docker)

Requires Python 3.12+ and a running PostgreSQL.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit DATABASE_URL if needed
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

## Tests

```bash
pytest                                    # in-memory SQLite, no setup needed
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/school_results_test pytest   # real Postgres
```

CI (GitHub Actions) runs linting with Ruff, the migration checks and the full test suite against PostgreSQL 16 on every push, and builds the Docker image.

## API overview

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/token` | anyone | Log in, receive a JWT |
| GET | `/auth/me` | staff | Current user |
| POST | `/auth/users` | admin | Create a staff account |
| GET | `/students` | staff | List with `form`, `search`, `limit`, `offset` |
| POST | `/students` | admin | Create a student |
| GET / PATCH / DELETE | `/students/{id}` | staff / admin / admin | Read, update, delete |
| GET | `/students/{id}/summary` | staff | Per-subject and overall averages |
| GET / POST | `/subjects` | staff / admin | List or create subjects |
| POST | `/results` | staff | Record a result |
| GET | `/results` | staff | Filter by student, subject, term |
| GET | `/results/at-risk` | staff | Students needing support, most urgent first |
| GET | `/health` | anyone | Liveness and database check |

## Possible next steps

- Refresh tokens and account lockout after repeated failed logins
- Bulk CSV import of a term's results
- Async SQLAlchemy and connection-pool tuning under load testing
- Per-subject at-risk rules and configurable thresholds per school

## Author

**Olidia Lunga** · [LinkedIn](https://linkedin.com/in/olidia-lunga) · [GitHub](https://github.com/OlidiaTL)
