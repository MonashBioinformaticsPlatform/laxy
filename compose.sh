#!/bin/bash
if [[ -z $LAXY_ENV ]]; then
	echo "Please set LAXY_ENV to 'dev', 'prod' or 'local-dev'."
	exit 1
fi

if [[ "${LAXY_ENV}" == "local-dev" ]]; then
	export LAXY_ENV=dev
    cmd="docker-compose -f docker-compose.yml -f docker-compose.local-dev.yml"
else
    cmd="docker-compose -f docker-compose.yml -f docker-compose.${LAXY_ENV}.yml"
fi

# Because accidentally typing up without -d is annoying ...
if [[ "${@}" == "up" ]]; then
    eval ${cmd} up -d
else
    eval ${cmd} "${@}"
fi

