# Laxy Genomics Pipelines

```bash
git clone --recurse-submodules https://github.com/MonashBioinformaticsPlatform/laxy.git
```

## Fronted development server

```
cd laxy_frontend
npm install
npm start
open http://localhost:9997/
```

## Backend

### Setup

Dependencies:

* Python 3.6+

```bash
# Create a Python virtual environment, install package dependencies
python3.6 -m venv venv
source venv/bin/activate
python3.6 install -U -r requirements.txt
# For development
python3.6 install -U -r requirements-dev.txt
```

Create a user and database on Postgres (run `psql`):
```postgresql
CREATE ROLE laxy WITH LOGIN PASSWORD 'blablafooword';
CREATE DATABASE laxy;
ALTER DATABASE laxy OWNER TO laxy;
GRANT ALL PRIVILEGES ON DATABASE laxy TO laxy;
```

```bash
# Copy the example settings environment and edit as required,
# including the database name and password above. 
cp .env_example .env
vi .env
```

Initialize the database, create an admin user:
```bash
./manage.py migrate
./manage.py makemigrations django_celery_results
./manage.py makemigrations laxy_backend
./manage.py migrate --fake-initial
./manage.py createinitialrevisions
./manage.py makemigrations
./manage.py migrate

./manage.py createsuperuser

# You may want to prepopulate the database with some data
./manage.py loadata laxy_backend/fixtures.json
```

### Run
```bash
source venv/bin/activate
DEBUG=yes python3.6 manage.py runserver 0.0.0.0:8000
```

#### Run Celery
```bash
celery -A laxy worker -B -E -Ofair -l info \
       --statedb=laxy_celery_worker.state
```

#### Run Celery Flower to monitor work queue
```bash
FLOWER_BASIC_AUTH=user:pass celery -A laxy flower --port=5555
```

OpenAPI / Swagger API (via drf_openapi): 
* Docs: http://localhost:8000/swagger/v1/
* JSON: http://localhost:8000/swagger/v1/?format=openapi

DRF CoreAPI docs: http://localhost:8000/coreapi/

### Docker

#### Development

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# To manually create the admin user (docker-compose.dev.yml does this itself using
# the LAXY_ADMIN_USERNAME and LAXY_ADMIN_PASSWORD environment variables)
docker container exec -it laxy_django_1 \
  python manage.py shell -c "from django.contrib.auth.models import User; \
                             User.objects.get(username='admin') or \
                             User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')"
```

##### To manually restart just the `django` service without bringing the whole stack down/up
```bash
docker-compose restart django
```

## Creating the UML diagram(s) for the Django models

```bash
./manage.py graph_models --pygraphviz -g -o docs/models_uml.png laxy_backend
```

#### Production

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
