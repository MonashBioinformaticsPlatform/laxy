# Non-Docker Development

This guide covers running the Laxy frontend and backend directly on your host machine,
without Docker. The recommended approach for most development is
[Docker Compose](../README.md#quickstart) -- use this guide if for some reason you need to run
services natively.

## Prerequisites

- Python 3.8+
- Node.js (LTS) and npm
- PostgreSQL 15+
- RabbitMQ (required if running Celery workers)

## Configuration

Copy the example environment file and edit as needed:

```bash
cp -n .env.example .env
```

Key variables to set for local development:

- `LAXY_DATABASE_URL` - PostgreSQL connection string
- `LAXY_BROKER_URL` - RabbitMQ URL (for Celery)
- `LAXY_SECRET_KEY` - Django secret key
- `LAXY_DEBUG=yes` - enable debug mode

To source `.env` into your shell:

```bash
export $(grep -v '^#' .env | xargs)
```

## Backend

### Database setup

Create a PostgreSQL user and database:

```sql
CREATE ROLE laxy WITH LOGIN PASSWORD 'your_password_here';
CREATE DATABASE laxy;
ALTER DATABASE laxy OWNER TO laxy;
GRANT ALL PRIVILEGES ON DATABASE laxy TO laxy;
```

Update `LAXY_DATABASE_URL` in your `.env` file to match, e.g.:

```
LAXY_DATABASE_URL=postgres://laxy:your_password_here@localhost:5432/laxy
```

### Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U -r requirements.txt
pip install -U -r requirements-dev.txt
```

### Database migrations

```bash
./manage.py migrate --no-input --run-syncdb
./manage.py migrate
./manage.py makemigrations laxy_backend
./manage.py migrate

./manage.py createsuperuser
./manage.py loaddata laxy_backend/fixtures.json
```

### Running Django

```bash
source venv/bin/activate
DEBUG=yes python3 manage.py runserver 0.0.0.0:8000
```

The API will be available at http://localhost:8000/api/v1/.

### Running Celery

If you need asynchronous task processing (not required if using `CELERY_ALWAYS_EAGER=True`):

```bash
celery -A laxy worker -B -E -Ofair -l info -Q celery,low-priority \
       --statedb=laxy_celery_worker.state
```

### Running Celery Flower (task monitoring)

```bash
FLOWER_BASIC_AUTH=user:pass celery -A laxy flower --port=5555
```

### Running tests

```bash
./manage.py test --noinput
```

Or with pytest:

```bash
pip install -U -r requirements-dev.txt
pytest
```

## Frontend

The frontend is a Vue.js single-page application built with webpack.

### Setup and development server

```bash
cd laxy_frontend
npm install --legacy-peer-deps
npm run build:dev
npm run server
```

The dev server will be available at http://localhost:8002/.

### Building for production

Create or update `.env` with the required `LAXY_FRONTEND_*` variables (see `.env.example`),
then:

```bash
cd laxy_frontend
npm run build:prod
```

Environment variables set in the shell override values from `.env`. These are substituted
by webpack (`dotenv-webpack`) at build time via `process.env.SOME_ENV_VAR` references.

## API documentation

When running the backend natively, the API docs are at:

- Swagger UI: http://localhost:8000/api/v1/schema/swagger-ui/
- ReDoc: http://localhost:8000/api/v1/schema/redoc/
- Schema (YAML): http://localhost:8000/api/v1/schema/?format=yaml
- Schema (JSON): http://localhost:8000/api/v1/schema/?format=json
