# Laxy

![Docker test](https://github.com/MonashBioinformaticsPlatform/laxy/workflows/Docker%20test/badge.svg?branch=master)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3767371.svg)](https://doi.org/10.5281/zenodo.3767371)

_Laxy_ is a web application designed to simplify launching routine genomic pipeline analyses.

![Job Page Screenshot](docs/screenshots/job_page.png)

## Quickstart

Laxy can be run under Docker Compose for local development and testing.

```bash
git clone --recurse-submodules https://github.com/MonashBioinformaticsPlatform/laxy.git
cd laxy
docker compose -f docker-compose.yml -f docker-compose.local-dev.yml build
docker compose --compatibility -f docker-compose.yml -f docker-compose.local-dev.yml up -d

# Wait for services to come online
# In particular, the frontend can take a few minutes to build upon startup - you can monitor the logs using:
#
# docker compose logs -f dev-frontend-server
# 
# docker compose logs -f django

# Frontend is at: http://localhost:8002
# Django admin is at: http://localhost:8001/admin
# Default username/password is: admin/adminpass
```

## Frontend

The Laxy frontend is a Vue Single-Page Application that runs in the browser and communicates with a Laxy backend server.

### Development

```bash
cp -n .env.example .env
cd laxy_frontend
npm install
npm run build:dev
npm run server
open http://localhost:8002/
```

### Building for production

Create `.env` (see `.env.example`), change frontend variables as required (eg `LAXY_FRONTEND_*`).
Environment variables (eg as seen via the `env` shell command) will override variables read from `.env`.

```bash
npm run build:prod
```

These variables are used by the Webpack (`dotenv-webpack`) build to substitute references to `process.env.SOME_ENV_VAR`.

## Backend

The Laxy backend is a RESTful web service for managing pipeline jobs across various compute resources.
It is based on Django and Celery.

### Setup

Dependencies:

- Python 3.6+

```bash
# Create a Python virtual environment, install package dependencies
python3.6 -m venv venv
source venv/bin/activate
pip install -U -r requirements.txt
# For development
pip install -U -r requirements-dev.txt
```

Run tests:

```bash
./manage.py test --noinput
```

Create a user and database on Postgres (run `psql`):

```postgresql
CREATE ROLE laxy WITH LOGIN PASSWORD 'blablafooword';
CREATE DATABASE laxy;
ALTER DATABASE laxy OWNER TO laxy;
GRANT ALL PRIVILEGES ON DATABASE laxy TO laxy;
```

Configuration is taken from a `.env` file.
Environment variables (eg `LAXY_*`) will override any variables defined in `.env`.

```bash
# Copy the example settings environment and edit as required,
# including the database name and password above.
cp -n .env.example .env
vi .env
```

(To manually source the `.env` file into your login shell for some purpose, do `export $(grep -v '^#' .env | xargs)`).

Initialize the database, create an admin user:

```bash
./manage.py migrate --no-input --run-syncdb
# ./manage.py migrate contenttypes
./manage.py migrate
./manage.py makemigrations django_celery_results
./manage.py makemigrations sites
./manage.py makemigrations laxy_backend
./manage.py migrate --fake-initial
./manage.py createinitialrevisions
./manage.py makemigrations
./manage.py migrate

./manage.py createsuperuser

# You may want to pre-populate the database with some data
./manage.py loaddata laxy_backend/fixtures.json
```

### Run

```bash
source venv/bin/activate
DEBUG=yes python3.6 manage.py runserver 0.0.0.0:8000
```

#### Run Celery

```bash
celery -A laxy worker -B -E -Ofair -l info -Q celery,low-priority \
       --statedb=laxy_celery_worker.state
```

#### Run Celery Flower to monitor work queue

```bash
FLOWER_BASIC_AUTH=user:pass celery -A laxy flower --port=5555
```

OpenAPI / Swagger API (via drf_openapi):

- Docs: http://localhost:8000/swagger/v1/
- JSON: http://localhost:8000/swagger/v1/?format=openapi

DRF CoreAPI docs: http://localhost:8000/coreapi/

### Docker

See notes on [running under Docker Compose](docs/docker.md)

### Customising

#### Adding a new reference genome

Reference genomes currently follow the naming and path layout used by iGenomes eg `Homo_sapiens/Ensembl/GRCh38`.
This is currently both the internal genome ID used by Laxy and the relative path where the downloaded genome is stored.

- Add the genome to the frontend in `laxy_frontend/src/config/genomics/genomes.ts`
- Add the genome to the backend in `laxy_backend/data/genomics/genomes.py`
- (Optional but recommended): Add on-demand downloading of the genome to the appropriate `run_job.sh` script
  (eg via the `download_ref_urls` bash function). Otherwise pre-install it at the correct path.

This is documented here in the hopes it can be streamlined in the future (eg via simple genome 'service').

#### Adding a new pipeline version

Currently only possible for `rnasik`, and ugly around the edges.
This process will be refined as pipeline are made more modular/pluggable.

Create a directory `laxy_backend/templates/job_scripts/rnasik/{version}/input`, where `{version}` is the new pipeline version.
Create a `conda_environment.yml` file in this directory. Follow the examples for other versions, changing the
appropriate version numbers for packages and the environment name.

Add the version number to the `pipeline_versions` list in `laxy_frontend/src/components/PipelineParams.vue`.
Optionally change the default version used in `store.ts`, `pipelineParams.pipeline_version`.
Optionally change the default value used in `laxy_backend/views.py`, `default_pipeline_version` (local variable in `JobCreate`).

#### Creating the UML diagram(s) for the Django models

```bash
./manage.py graph_models --pygraphviz -g -o docs/models_uml.png laxy_backend
```
