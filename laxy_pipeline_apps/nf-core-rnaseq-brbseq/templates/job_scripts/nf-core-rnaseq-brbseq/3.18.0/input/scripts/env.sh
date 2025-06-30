#!/usr/bin/env bash

export PIPELINE_NAME='nf-core-rnaseq-brbseq'
# These variables are set via templating when the script file is created
export JOB_ID="{{ JOB_ID }}"
export JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
export JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
export JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
export JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
export PIPELINE_VERSION="{{ PIPELINE_VERSION }}"

# Global variables used throughout the script
export TMP="${PWD}/../tmp"
export TMPDIR="${TMP}"
export JOB_PATH=${PWD}
export INPUT_READS_PATH="${JOB_PATH}/input/reads"
export INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
export INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
export PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
export SITE_CONFIGS="${JOB_PATH}/../../config"
export CONDA_BASE="${JOB_PATH}/../miniconda3"
# export CONDA_BASE="${JOB_PATH}/../miniforge3"
export DOWNLOAD_CACHE_PATH="${JOB_PATH}/../../cache/downloads"
export SINGULARITY_CACHEDIR="${JOB_PATH}/../../cache/singularity"
export APPTAINER_CACHEDIR="${SINGULARITY_CACHEDIR}"
export SINGULARITY_TMPDIR="${TMP}"
export APPTAINER_TMPDIR="${TMP}"
export SINGULARITY_LOCALCACHEDIR="${TMPDIR}"
export APPTAINER_LOCALCACHEDIR="${TMPDIR}"
export AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
export IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"
export LAXYDL_BRANCH=${LAXYDL_BRANCH:-master}
export LAXYDL_USE_ARIA2C=${LAXYDL_USE_ARIA2C:-yes}
export LAXYDL_PARALLEL_DOWNLOADS=${LAXYDL_PARALLEL_DOWNLOADS:-8}

# These are applied via chmod to all files and directories in the run, upon completion
export JOB_FILE_PERMS='ug+rw-s,o='
export JOB_DIR_PERMS='ug+rwx-s,o='

export SLURM_EXTRA_ARGS="{{ SLURM_EXTRA_ARGS|default:"" }}"

export QUEUE_TYPE="{{ QUEUE_TYPE }}"
# export QUEUE_TYPE="local"

if [[ ${IGNORE_SELF_SIGNED_CERTIFICATE} == "yes" ]]; then
    export CURL_INSECURE="--insecure"
    export LAXYDL_INSECURE="--ignore-self-signed-ssl-certificate"
else
    export CURL_INSECURE=""
    export LAXYDL_INSECURE=""
fi