# Koya Booking API - Server

Django 6 and Django REST Framework API for the clinic booking assessment. See the [project README](../README.md) for what it does and how it works.

## Setup

1. Install prerequisites (Python 3.13 and pipenv)

MacOS

```bash
brew install pipenv
```

Windows

```bash
pip install pipenv
```

2. Install dependencies

```bash
pipenv install --dev
```

3. Configure environment

```bash
cp .env.template .env
```

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Django secret key. Generate one with `pipenv run python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"` |
| `DEBUG` | `True` for local development. Anything else means off. |
| `ALLOWED_HOSTS` | Comma separated host names the API serves |
| `API_KEY` | The key clients send in `X-API-Key`. Comma separated, so the web page can have its own. |
| `CORS_ALLOWED_ORIGINS` | Comma separated origins allowed to call the API from a browser, for example `http://localhost:5173` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Postgres connection. Use a session-mode connection: row and advisory locks need it (Supabase's transaction pooler on port 6543 does not work). |

4. Run

```bash
make migrate
make run        # http://localhost:8001
```

## Tests

```bash
make db         # starts a Postgres container named koya-pg on port 5433
make test
```

`make test` points the tests at that container, whatever `.env` says. Without `make`, in PowerShell:

```powershell
$env:PIPENV_DONT_LOAD_ENV = "1"
$env:DB_HOST = "localhost"; $env:DB_PORT = "5433"; $env:DB_USER = "postgres"
$env:DB_PASSWORD = "pg"; $env:DB_NAME = "koya"
pipenv run pytest
```

## Other commands

```bash
make tidy           # autoflake, isort and black
make docker/build   # build the production image
```
