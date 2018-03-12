#!/usr/bin/env bash
set -e
set -o nounset
set -o pipefail

# These variables are overriden by environment vars if present
# export DEBUG="${DEBUG:-yes}"
export JOB_ID="${JOB_ID:-}"
export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"
export JOB_COMPLETE_AUTH_HEADER="${JOB_COMPLETE_AUTH_HEADER:-}"

#### Job happens in here ####

env >job.out
EXIT_CODE=$?

#### Notify service we are done ####
curl -X PATCH \
     -H "Content-Type: application/json" \
     -H "${JOB_COMPLETE_AUTH_HEADER}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     -d '{"exit_code":'${EXIT_CODE}'}' \
     "${JOB_COMPLETE_CALLBACK_URL}"
