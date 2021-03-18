#!/usr/bin/env bash

#
# A do nothing test job with some variables
#

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

# These variables are set via templating when the script file is created
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly REFERENCE_GENOME_ID="{{ REFERENCE_GENOME }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
readonly PIPELINE_ALIGNER="{{ PIPELINE_ALIGNER }}"

# Global variables used throughout the script
readonly TMP="${PWD}/../tmp"
readonly JOB_PATH=${PWD}
readonly INPUT_READS_PATH="${JOB_PATH}/input/reads"
# contains symlinks to references, either public or custom reference downloaded to cache
readonly INPUT_REFERENCE_PATH="${JOB_PATH}/input/reference"
readonly INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
readonly INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
readonly PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly REFERENCE_BASE="${JOB_PATH}/../references/iGenomes"
readonly DOWNLOAD_CACHE_PATH="${JOB_PATH}/../cache"
readonly AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
readonly IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"

env

echo "version"