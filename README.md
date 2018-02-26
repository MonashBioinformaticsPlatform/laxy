# Laxy Genomics Pipelines

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

# Copy the example settings environment and edit as required
cp .env_example .env
vi .env

./manage.py migrate
./manage.py makemigrations django_celery_results
./manage.py makemigrations laxy_backend
./manage.py migrate --fake-initial
./manage.py createinitialrevisions
./manage.py makemigrations
./manage.py migrate

./manage.py createsuperuser
```

### Run
```bash
source venv/bin/activate
DEBUG=yes python3.6 manage.py runserver 0.0.0.0:8000
```

OpenAPI / Swagger API (via drf_openapi): 
* Docs: http://localhost:8000/swagger/v1/
* JSON: http://localhost:8000/swagger/v1/?format=openapi

DRF CoreAPI docs: http://localhost:8000/coreapi/

### Docker

#### Development

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
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
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
