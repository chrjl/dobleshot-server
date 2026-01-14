# Dobleshot server

A GraphQL API &times; SQL backend for a coffee experience-centered social networking app.

## Development

### Set up python virtual environment

- Create virtual environment
- Enter virtual environment
- Install dependencies, editable install package

```console
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Set up a development database

Define database connection parameters in `.env`, or via environment variables. Required parameters:

- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT`
- `DB_HOST` (required for SQLAlchemy/Alembic only)
- `DB_DRIVER` (required for SQLAlchemy/Alembic only)

Spin up a Postgres server in a Docker container, with credentials set via environment variables defined in `.env`.

```console
docker compose up
```

Migrate tables and (optionally) seed initial entries

```console
alembic upgrade head
bin/seed.py --json sample-data.json
```
