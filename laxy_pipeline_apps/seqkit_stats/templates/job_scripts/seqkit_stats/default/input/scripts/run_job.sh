#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o xtrace

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

readonly PIPELINE_NAME='seqkit_stats'
# These variables are set via templating when the script file is created
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"

# Global variables used throughout the script
readonly TMP="${JOB_PATH}/../../tmp"
readonly JOB_PATH=${PWD}
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly SITE_CONFIGS="${JOB_PATH}/../../config"
readonly INPUT_READS_PATH="${JOB_PATH}/input/reads"
readonly INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
readonly INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
readonly PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
readonly DOWNLOAD_CACHE_PATH="${JOB_PATH}/../../cache/downloads"

readonly PIPELINES_CACHE_PATH="${JOB_PATH}/../../cache/pipelines"
readonly SINGULARITY_CACHEDIR="${JOB_PATH}/../../cache/singularity"
readonly SINGULARITY_TMPDIR="${TMP}"

readonly AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
readonly IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"
readonly LAXYDL_BRANCH=master
readonly LAXYDL_USE_ARIA2C=yes
readonly LAXYDL_PARALLEL_DOWNLOADS=8

# These are applied via chmod to all files and directories in the run, upon completion
readonly JOB_FILE_PERMS='ug+rw-s,o='
readonly JOB_DIR_PERMS='ug+rwx-s,o='

# shellcheck disable=SC1054,SC1083,SC1009
{% if SLURM_EXTRA_ARGS %}
export SLURM_EXTRA_ARGS="{{ SLURM_EXTRA_ARGS }}"
# shellcheck disable=SC1073
{% endif %}

readonly QUEUE_TYPE="{{ QUEUE_TYPE }}"
# readonly QUEUE_TYPE="local"



if [[ ${IGNORE_SELF_SIGNED_CERTIFICATE} == "yes" ]]; then
    readonly CURL_INSECURE="--insecure"
    readonly LAXYDL_INSECURE="--ignore-self-signed-ssl-certificate"
else
    readonly CURL_INSECURE=""
    readonly LAXYDL_INSECURE=""
fi

##
# Load the laxy bash helper functions.
# These functions use some of the variables defined above
##
source "${INPUT_SCRIPTS_PATH}/laxy.lib.sh" || exit 1

send_event "JOB_INFO" "Running using the laxy_pipeline_apps.seqkit-stats pluggable pipeline app."

# We exit on any uncaught error signal. The 'trap finalize_job EXIT' 
# below does sends a job fail HTTP request and cleans up when an error 
# signal is raised. For this reason, it's important to catch any exit
# signals from commands that are 'optional' but might fail, eg like: some_command || true
set -o errexit

function job_done() {
    local _exit_code=${1:-$?}
    
    # Use the EXIT_CODE global if set
    # [[ -n ${EXIT_CODE} ]] || _exit_code=${EXIT_CODE}

    cd "${JOB_PATH}"
    register_files || true

    # remove trap now
    trap - EXIT
    finalize_job ${_exit_code}
}
# Send job fail/done HTTP request, cleanup and remove secrets upon an exit code raise
# This won't catch every case (eg external kill -9), but is better than nothing.
trap job_done EXIT

# function remove_secrets() {
#     if [[ ${DEBUG} != "yes" ]]; then
#       rm -f "${AUTH_HEADER_FILE}"
#     fi
# }
#
# trap remove_secrets EXIT


if [[ ! -f "${AUTH_HEADER_FILE}" ]]; then
    echo "No auth token file (${AUTH_HEADER_FILE}) - exiting."
    exit 1
fi

# For QUEUE_TYPE=='local'
PREFIX_JOB_CMD="/usr/bin/env bash -l -c "
MEM=1000 
CPUS=1

# We use sbatch --wait --wrap rather than srun, since it seems more reliable
# and jobs appear pending on the queue immediately
readonly SLURM_OPTIONS="--parsable \
                        --cpus-per-task=${CPUS} \
                        --mem=${MEM} \
                        -t 3-0:00 \
                        --ntasks-per-node=1 \
                        --ntasks=1 \
                        {% if SLURM_EXTRA_ARGS %}
                        ${SLURM_EXTRA_ARGS} \
                        {% endif %}
                        --job-name=laxy:${JOB_ID}"


if [[ "${QUEUE_TYPE}" == "slurm" ]]; then
    PREFIX_JOB_CMD="sbatch ${SLURM_OPTIONS} --wait --wrap "
fi

if [[ "${QUEUE_TYPE}" == "local" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    add_to_manifest "input/reads/*.fq" "fastq"
    add_to_manifest "input/reads/*.fastq" "fastq"
    add_to_manifest "input/reads/*.fq.gz" "fastq"
    add_to_manifest "input/reads/*.fastq.gz" "fastq"
    add_to_manifest "output/*.tsv" "tsv,report"

    curl -X POST \
      ${CURL_INSECURE} \
     -H "Content-Type: text/csv" \
     -H @"${AUTH_HEADER_FILE}" \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     --data-binary @"${JOB_PATH}/manifest.csv" \
     "${JOB_FILE_REGISTRATION_URL}"
}

function download_input_data() {
    if [[ "${JOB_INPUT_STAGED}" == "no" ]]; then

        # send_event "INPUT_DATA_DOWNLOAD_STARTED" "Input data download started."

        # one URL per line
        readonly urls=$(get_input_data_urls)

        mkdir -p "${DOWNLOAD_CACHE_PATH}"

        LAXYDL_EXTRA_ARGS=""
        if [[ "${LAXYDL_USE_ARIA2C}" != "yes" ]]; then
            LAXYDL_EXTRA_ARGS=" ${LAXYDL_EXTRA_ARGS} --no-aria2c "
        fi

        # Download (FASTQ) reads
        laxydl download \
            ${LAXYDL_INSECURE} \
            -vvv \
            ${LAXYDL_EXTRA_ARGS} \
            --cache-path "${DOWNLOAD_CACHE_PATH}" \
            --no-progress \
            --unpack \
            --parallel-downloads "${LAXYDL_PARALLEL_DOWNLOADS}" \
            --event-notification-url "${JOB_EVENT_URL}" \
            --event-notification-auth-file "${AUTH_HEADER_FILE}" \
            --pipeline-config "${PIPELINE_CONFIG}" \
            --create-missing-directories \
            --skip-existing \
            --destination-path "${INPUT_READS_PATH}"

        DL_EXIT_CODE=$?
        if [[ $DL_EXIT_CODE != 0 ]]; then
            send_job_finished $DL_EXIT_CODE
        fi
        return $DL_EXIT_CODE

        # send_event "INPUT_DATA_DOWNLOAD_FINISHED" "Input data download completed."
    fi
}
# Extract the pipeline parameter seqkit_stats.flags.all from the pipeline_config.json
# Set the --all flag appropriately.
_flags_all=$(jq --raw-output '.params.seqkit_stats.flags.all' "${PIPELINE_CONFIG}" || echo "false")
ALL_FLAG=" "
if [[ "${_flags_all}" == "true" ]]; then
    ALL_FLAG=" --all "
fi

update_permissions || true

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

mkdir -p "${INPUT_CONFIG_PATH}" "${INPUT_SCRIPTS_PATH}" "${INPUT_READS_PATH}"

####
#### Setup and import a Conda environment
####

install_miniconda || fail_job 'install_miniconda' '' $?

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "${PIPELINE_NAME}" "${PIPELINE_VERSION}" || fail_job 'init_conda_env' '' $?

update_laxydl || send_error 'update_laxydl' '' $?

####
#### Stage input data ###
####

download_input_data || fail_job 'download_input_data' '' $?

capture_environment_variables || true

cd "${JOB_PATH}/output"

####
#### Job happens in here
####

send_event "JOB_PIPELINE_STARTING" "Pipeline starting."

send_event "JOB_INFO" "Starting pipeline."

# EXIT_CODE=99

# Note: Using xargs like this will fail if the commandline gets too long (many fastqs, or very long filenames)
# seqkit stats -j $CPUS $(find ${INPUT_READS_PATH} -name "*.f*[q,a].gz" | xargs) >${JOB_PATH}/output/seqkit_stats/seqkit_stats.tsv
${PREFIX_JOB_CMD} "find ${INPUT_READS_PATH} -name "*.f*[q,a].gz" -exec \
                   seqkit stats ${ALL_FLAG} -j ${CPUS} {} + \
                     >${JOB_PATH}/output/seqkit_stats.tsv \
                     2>${JOB_PATH}/output/seqkit_stats.err" \
  >>"${JOB_PATH}/job.pids"
  # >>"${JOB_PATH}/slurm.jids"

# Call job finalization with explicit exit code from the main pipeline command (eg seqkit stats)
job_done $?

# Capture the exit code of the important process, to be returned
# in the curl request below
# EXIT_CODE=$?

# Some job scripts might have things that occur after the main pipeline
# run - so we signal when the 'pipeline' computation completed, but this is
# considered a distinct event from the whole job completing (that will be
# generated as a side effect of calling JOB_COMPLETE_CALLBACK_URL)
# if [[ ${EXIT_CODE} -ne 0 ]]; then
#   send_event "JOB_PIPELINE_FAILED" "Pipeline failed." '{"exit_code":'${EXIT_CODE}'}'
# else
#   send_event "JOB_PIPELINE_COMPLETED" "Pipeline completed." '{"exit_code":'${EXIT_CODE}'}'
# fi

# update_permissions || true

# cd "${JOB_PATH}"
# register_files || true

# ####
# #### Notify service we are done
# ####

# # Authorization header passed to curl is stored in a @file so it doesn't leak in 'ps' etc.

# send_job_finished "${EXIT_CODE}"

# finalize_job "${EXIT_CODE}"

# # Remove the access token now that we don't need it anymore
# remove_secrets

# Remove the trap so job_done doesn't get called a second time when the script naturally exits
trap - EXIT
exit 0

#}}