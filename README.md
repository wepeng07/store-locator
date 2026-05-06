# Store Locator Service

Store Locator Service is a FastAPI backend for store discovery, role-based store administration, and bulk store onboarding.

Chinese version: [README.zh-CN.md](README.zh-CN.md)

## Why this project matters

- Improve store conversion by helping customers find the closest eligible store quickly.
- Support omnichannel operations such as pickup, returns, and service-based filtering.
- Reduce operations overhead with admin CRUD APIs, CSV onboarding, and role-based access control.
- Create a foundation for future store intelligence features such as SLA tracking, regional coverage, and service availability analytics.

## Features

- Public store search by address, postal code, or coordinates
- Radius, service, store type, and `open_now` filtering
- In-memory caching and API rate limiting for public search
- JWT login, refresh, logout, and RBAC helpers
- Admin store CRUD with optional geocoding
- CSV-based bulk import with validation and rollback behavior
- Alembic migrations, seed scripts, and end-to-end tests

## Tech stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic Settings
- HTTPX

## Project structure

```text
app/
  api/routes/         HTTP endpoints
  core/               config, auth, JWT, RBAC
  db/                 engine/session dependencies
  middlewares/        cross-cutting HTTP middleware
  models/             SQLAlchemy models
  services/           search, geocoding, cache helpers
  utils/              geo and business utility functions
alembic/              database migrations
scripts/              local seed and inspection scripts
tests/                end-to-end API coverage
docs/                 repository audit and delivery notes
```

## Quick start

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

3. Start PostgreSQL:

   ```bash
   docker compose up -d db
   ```

4. Run migrations and seed data:

   ```bash
   alembic upgrade head
   python scripts/seed.py
   python scripts/seed_services.py
   python scripts/seed_users.py
   ```

5. Start the API:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Run tests:

   ```bash
   pytest
   ```

## API surface

- `POST /api/stores/search`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/admin/ping`
- `POST /api/admin/stores`
- `GET /api/admin/stores`
- `GET /api/admin/stores/{store_id}`
- `PATCH /api/admin/stores/{store_id}`
- `DELETE /api/admin/stores/{store_id}`
- `POST /api/admin/stores/import`

## Notes

- `requirement.txt` is kept as a compatibility wrapper and points to `requirements.txt`.

