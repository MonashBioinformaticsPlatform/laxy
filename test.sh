#/bin/bash

# We need the laxy:dev image to exist locally, as a base for laxy:test
# If it doesn't exist, build it.
if ! docker image inspect laxy:dev >/dev/null; then
    docker-compose -p laxytest -f docker-compose.yml -f docker-compose.local-dev.yml build
fi

docker-compose -p laxytest -f docker-compose.test.yml run test-dev
