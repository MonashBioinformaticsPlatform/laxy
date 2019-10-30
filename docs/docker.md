### Docker deployment notes

#### Development

##### Building and running the stack

Laxy (and associated services) can run under Docker Compose.

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --build-arg GIT_COMMIT=$(git log -1 --format=%H)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Once running, to watch the logs:
```bash
docker-compose logs -f -t
# or for just one service (eg django)
# docker-compose logs -f -t django
```

To manually create the admin user (`docker-compose.dev.yml` does this itself using
the `LAXY_ADMIN_USERNAME` and `LAXY_ADMIN_PASSWORD` environment variables):

```bash
docker container exec -it laxy_django_1 \
  python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); \
                             User.objects.filter(username='admin').count() or \
                             User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')"
```

To pull down the stack, do:
```bash
docker-compose down
```

##### Database dumps and migrations

Migrate database in Docker container:
```bash
export LAXY_ENV=dev

# or if the container isn't running:
docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml run django python manage.py migrate
```

Run an ad-hoc data migration script (rare task):
```bash
docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml exec django /bin/bash -c \
  "/app/manage.py shell < /app/scripts/ad-hoc-migrations/add-strandedness-metadata.py"
```

Dump fixtures (JSON formatted database records):
```bash
docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml run django python manage.py dumpdata --indent 2

# Just the defined ComputeResource records:
docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml run django python manage.py dumpdata \
       laxy_backend.computeresource \
       --indent 2

# Or a single model of interest, by primary key:
docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml run django python manage.py dumpdata \
       laxy_backend.sampleset \
       --pks 3lSCcJPlvkMq1oCO6hM4XL \
       --indent 2
```

Load fixtures:
```bash
# Copy the fixtures to the container (if not already there)
docker cp fixtures.json laxy_django_1:/tmp/
# Apply fixture to the database via Django's loaddata command
docker container exec -it laxy_django_1  python manage.py loaddata /tmp/fixtures.json
# Remove copy of fixtures from container, may contain secrets
docker exec -it laxy_django_1 rm /tmp/fixtures.json
```

Dropping the test database when it's in use (eg, if tests we terminate prematurely before cleanup). 
Run `psql`:
```postgresql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'test_laxy';
DROP DATABASE test_laxy;
```

Dropping all tables (careful !):
```bash
 docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml \
   run db /bin/bash -c \
   'echo -e "DROP SCHEMA public CASCADE;\n CREATE SCHEMA public;" | PGPASSWORD=postgres psql -h db -p 5432 -w postgres postgres'
```

###### Cloning the Postgres data volume

In the Docker Compose setup the Postgres database lives in an attached volume container
named `laxy_dbdata` (`dbdata`, as defined by `PGDATA` in `docker-compose.yml`).

Assuming the Postgres service is called `db` and it's data volume is `dbdata`,
we can export a tar archive of the database files like:

```bash
DBTAR=postgres-dbdata-$(date +%s).tar
docker-compose run --no-deps --rm -v dbdata:/var/lib/postgresql/data/pgdata -v $(pwd):/backup db tar cvf /backup/${DBTAR} /var/lib/postgresql/data/pgdata

# We can also do this with plain Docker, if we use the correct container name (eg laxy_db_1_*)
# docker run --rm --volumes-from laxy_db_1 -v $(pwd):/backup busybox tar cvf /backup/${DBTAR} /var/lib/postgresql/data/pgdata
```

We can copy this archive back into a new volume container (`database_copy`) like:

```bash
# DBTAR=postgres-dbdata-*.tar
DBVOLNAME=database_copy
# DBVOLNAME=laxy_dbdata
docker-compose stop db
docker volume create ${DBVOLNAME}
docker run --rm -v ${DBVOLNAME}:/var/lib/postgresql/data/pgdata  -v $(pwd):/backup busybox tar xvf /backup/${DBTAR}
docker-compose start db
```

To clone the volume 'directly' into a new volume, use the 
`docker_clone_volume.sh` script found here: https://github.com/gdiepen/docker-convenience-scripts like:

```bash
./docker_clone_volume.sh laxy_dbdata laxy_dbdata.bak
./docker_get_data_volume_info.sh
```


##### To manually restart just the `django` service without bringing the whole stack down/up
```bash
docker-compose restart django
```

##### To tail logs for a particular service/container
```bash
docker-compose logs --timestamps --tail="10" -f django
```

#### Production

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
