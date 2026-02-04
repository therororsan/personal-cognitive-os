# Backend

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create a `.env` file in this folder:

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/pcos
DEV_ONLY_BOOTSTRAP=true
PCOS_ENV=dev
```

## Database

- Start Postgres with docker:
  - `docker compose up -d`
- Run migrations:
  - `alembic upgrade head`

## Run API

- `uvicorn app.main:app --reload`

## Bootstrap (dev only)

- `POST /v1/admin/bootstrap`
- Returns an API key for testing. This endpoint is enabled only when `DEV_ONLY=true`.

## Run Digest Job

- `python -m jobs.run_digest`

## Run Episode Builder Job

- `python -m jobs.run_episode_builder`
