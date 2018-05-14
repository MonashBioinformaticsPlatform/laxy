#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
# export DEBUG="${DEBUG:-yes}"
# export JOB_ID="${JOB_ID:-}"
# export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"
# export JOB_COMPLETE_AUTH_HEADER="${JOB_COMPLETE_AUTH_HEADER:-}"

readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly REFERENCE_GENOME="{{ REFERENCE_GENOME }}"

readonly JOB_PATH=${PWD}
readonly CONDA_BASE="../miniconda3"

function send_event() {
    event=${1:-"HEARTBEAT"}
    extra=${2:-"{}"}
    # escape double quotes since this is JSON nested inside JSON ?
    # extra=$(sed 's/"/\\"/g' <<< "${extra}")

    # || true so we don't stop on errors irrespective of set -o errexit state,
    # so if a curl call fails we don't bring down the whole script
    # NOTE: curl v7.55+ is required to use -H @filename

    # --silent \
    curl -X POST \
         -H "Content-Type: application/json" \
         -H @"${JOB_PATH}/.private_request_headers" \
         -vvv \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"event":"'"${event}"'","extra":'"${extra}"'}' \
         ""${JOB_EVENT_URL}"" || true
}

function init_conda_env() {
    env_name="${1}"

    # Conda activate misbehaves if nounset and errexit are set
    # https://github.com/conda/conda/issues/3200
    set +o nounset
    conda install -n "${env_name}" \
                 -c serine \
                 -c bioconda \
                 -c conda-forge \
                 rnasik qualimap curl

    source "${CONDA_BASE}/bin/activate" "${CONDA_BASE}/envs/${env_name}"
    set -o nounset
}

mkdir -p input
mkdir -p output

####
#### Import a Conda environment
####

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "rnasik"


####
#### Stage input data ###
####

if [ "${JOB_INPUT_STAGED}" == "no" ]; then

    send_event "INPUT_DATA_DOWNLOAD_STARTED"

    PARALLEL_DOWNLOADS=4
    jq '.sample_set.samples[].files[][]' <pipeline_config.json | \
      sed s'/"//g' | \
      parallel --no-notice --line-buffer -j ${PARALLEL_DOWNLOADS} \
      wget --continue --trust-server-names --retry-connrefused --read-timeout=60 \
           --waitretry 60 --timeout=30 --tries 8 \
           --output-file output/download.log --directory-prefix input {}

    send_event "INPUT_DATA_DOWNLOAD_FINISHED"

fi

cd output

env >job_env.out

####
#### Job happens in here
####

GENOME_FASTA="references/iGenomes/${REFERENCE_GENOME}/Sequence/WholeGenomeFasta/genome.fa"
GENOME_GTF="references/iGenomes/${REFERENCE_GENOME}/Annotation/Genes/genes.gtf"

send_event "JOB_PIPELINE_STARTING"

# Don't exit on error, since we want to capture exit code and do an HTTP
# request with curl upon failure
set +o errexit

RNAsik -align star \
       -fastaRef ../../${GENOME_FASTA} \
       -fqDir ../input \
       -counts \
       -gtfFile ../../${GENOME_GTF} \
       -all \
       -paired \
       -extn ".fastq.gz" \
       -pairIds "_1,_2" \
       >>job.out 2>>job.err

# Capture the exit code of the important process, to be returned
# in the curl request below
EXIT_CODE=$?

# Some job scripts might have things that occur after the main pipeline
# run - so we signal when the 'pipeline' computation completed, but this is
# considered a distinct event from the whole job completing (that will be
# generated as a side effect of calling JOB_COMPLETE_CALLBACK_URL)
send_event "JOB_PIPELINE_FINISHED" '{"exit_code":'${EXIT_CODE}'}'

####
#### Notify service we are done
####

# Authorization header is stored in a file so it doesn't
# leak in 'ps' etc.

# -H "Content-Type: application/json" \
# -H "${JOB_COMPLETE_AUTH_HEADER}" \

curl -X PATCH \
     -H "Content-Type: application/json" \
     -H @"${JOB_PATH}/.private_request_headers" \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     -d '{"exit_code":'${EXIT_CODE}'}' \
     ""${JOB_COMPLETE_CALLBACK_URL}""

# Extra security: Remove the access token now that we don't need it anymore
# rm ../.private_request_headers
