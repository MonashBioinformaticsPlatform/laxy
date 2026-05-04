#!/bin/bash
export COMPOSE_BAKE=true

if [[ -z $LAXY_ENV ]]; then
	echo "Please set LAXY_ENV to 'dev', 'prod' or 'local-dev'."
	exit 1
fi

if [[ "${LAXY_ENV}" == "local-dev" ]]; then
    export LAXY_ENV=dev
    cmd="docker compose -f docker-compose.yml -f docker-compose.local-dev.yml"
else
    cmd="docker compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml"
fi

# Because accidentally typing up without -d is annoying ...
if [[ "${@}" == "up" ]]; then
    eval ${cmd} up -d
elif [[ "${1}" == "build" && -z "${2}" ]]; then
    # Build django first since nginx depends on laxy:latest image
    # (COPY --from=laxy:latest in nginx Dockerfile)
    echo "Building django first (nginx depends on laxy:latest)..."
    eval ${cmd} build django
    eval ${cmd} build
else
    eval ${cmd} "${@}"
fi

