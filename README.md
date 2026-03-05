# Dobleshot server

A GraphQL API &times; SQL backend for a coffee experience-centered social networking app.

## Usage

### Set up python virtual environment

- Create virtual environment
- Enter virtual environment
- Install dependencies, editable install package

```console
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run the server

```console
APP_ENV=development python -m server.main
```

Application environment (e.g. `development`, `production`) is set by `APP_ENV` environment variable, defaults to `development`. The application loads from `dotenv` files specified by the environment (e.g. `.env.production`, `.env.development`) for database connection parameters, server options, etc.; development environment falls back to `.env`.

The following executable scripts are provided:

- `start`: runs the main server script
- `serve-dev`: ignores `APP_ENV` and runs the development server

## Development

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

### Set up an in-memory database for testing

- Create in-memory SQLite engine
- Import the SQLAlchemy `MetaData` object
- Create tables from the models stored in the `MetaData` object

```python
from db.models import Base

engine = sqlalchemy.create_engine("sqlite://", echo=True)
Base.metadata.create_all(engine)
```

# Attributions

- List of countries

  US Department of State, Bureau of Intelligence and Research  
  Independent States in the World Fact Sheet  
  Link: https://www.state.gov/independent-states-in-the-world/  
  Published: March 12, 2025  
  Accessed: January 30, 2026

- Information about coffee-growing countries, list of coffee-growing regions

  Cafe Imports  
  Link: https://www.cafeimports.com/north-america/blog/origins/  
  Accessed: January 31, 2026