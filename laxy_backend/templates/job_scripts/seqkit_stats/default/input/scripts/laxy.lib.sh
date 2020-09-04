#!/bin/bash

function remove_secrets() {
    if [[ ${DEBUG} != "yes" ]]; then
      rm -f "${AUTH_HEADER_FILE}"
    fi
}

function get_input_data_urls() {
    # Output is one URL one per line
    local urls
    # urls=$(jq '.sample_cart.samples[].files[][]' <"${PIPELINE_CONFIG}" | sed s'/"//g')
    urls=$(jq '.params.fetch_files[]' <"${PIPELINE_CONFIG}" | sed s'/"//g')
    echo "${urls}"
}

function capture_environment_variables() {
    env >"${JOB_PATH}/output/job_env.out"
}

function update_permissions() {
    send_event "JOB_INFO" "Updating Unix file permissions for job outputs on compute node."

    # This can be used to update the permission on files after job completion
    # (eg if you want to automatically share files locally with a group of users on a compute resource).
    chmod "${JOB_DIR_PERMS}" "${JOB_PATH}"
    find "${JOB_PATH}" -type d -exec chmod "${JOB_DIR_PERMS}" {} \;
    find "${JOB_PATH}" -type f -exec chmod "${JOB_FILE_PERMS}" {} \;
}

function send_event() {
    local event=${1:-"HEARTBEAT"}
    local message=${2:-""}
    local extra=${3:-"{}"}
    # escape double quotes since this is JSON nested inside JSON ?
    # extra=$(sed 's/"/\\"/g' <<< "${extra}")

    # || true so we don't stop on errors irrespective of set -o errexit state,
    # so if a curl call fails we don't bring down the whole script
    # NOTE: curl v7.55+ is required to use -H @filename

    VERBOSITY="--silent"
    if [[ "${DEBUG}" == "yes" ]]; then
        # NOTE: verbose mode should NOT be used in production since it prints
        # full headers to stdout/stderr, including Authorization tokens.
        VERBOSITY="-vvv"
    fi

    curl -X POST \
         ${CURL_INSECURE} \
         -H "Content-Type: application/json" \
         -H @"${AUTH_HEADER_FILE}" \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"event":"'"${event}"'","message":"'"${message}"'","extra":'"${extra}"'}' \
         ${VERBOSITY} \
         "${JOB_EVENT_URL}" || true
}

function send_job_finished() {
    local _exit_code=$1
    curl -X PATCH \
         ${CURL_INSECURE} \
         -H "Content-Type: application/json" \
         -H @"${AUTH_HEADER_FILE}" \
         --silent \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"exit_code":'${_exit_code}'}' \
         "${JOB_COMPLETE_CALLBACK_URL}"
}

function send_error() {
    local _step="$1"
    local _reason="$2"
    local _exit_code=${3:-$?}
    send_event "JOB_ERROR" \
               "Error - ${_reason} (${_step})" \
               '{"exit_code":'${_exit_code}',"step":"'${_step}'","reason":"'${_reason}'"}'
}

function fail_job() {
    local _step="$1"
    local _reason="$2"
    local _exit_code=${3:-$?}
    send_error "${_step}" "${_reason}" ${_exit_code}
    send_job_finished ${_exit_code}
    remove_secrets
    update_permissions || true
    exit ${_exit_code}
}

function finalize_job() {
    local _exit_code=${1:-$?}
    
    if [[ ${_exit_code} -ne 0 ]]; then
      send_event "JOB_PIPELINE_FAILED" "Pipeline failed." '{"exit_code":'${_exit_code}'}'
    else
     send_event "JOB_PIPELINE_COMPLETED" "Pipeline completed." '{"exit_code":'${_exit_code}'}'
    fi

    send_job_finished ${_exit_code}
    remove_secrets
    update_permissions || true
    exit ${_exit_code}
}

function send_job_metadata() {
    local metadata="$1"
    curl -X PATCH \
         ${CURL_INSECURE} \
         -H "Content-Type: application/merge-patch+json" \
         -H @"${AUTH_HEADER_FILE}" \
         --silent \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d "${metadata}" \
         "${JOB_COMPLETE_CALLBACK_URL}"
}

function download_somehow() {
    # A very determined download function
    # Finds something, _ANYTHING_ that might help us download a file over HTTPS
    # This is primarily used to bootstrap a conda installation - after
    # that we can use the curl installed by conda.
    #
    # (We don't include the most bare-bones solution that only uses 
    #  /dev/tcp/$host/$port since we need HTTPS, not just HTTP)

    local url=$1
    local filename=$2
    if which wget; then
        wget --directory-prefix "${TMP}" -c "${url}"
    elif which curl; then
        curl "${url}" >"${TMP}/${filename}"
    elif which python && [[ "$(python --version | cut -d '.' -f 1)" == "Python 3" ]]; then
        python3 -c "from urllib.request import urlretrieve; urlretrieve('${url}', '${filename}')"
    elif which python && [[ "$(python --version | cut -d '.' -f 1)" == "Python 2" ]]; then
        python -c "from urllib import urlretrieve; urlretrieve('${url}', '${filename}')"
    elif which GET; then
        GET "${url}" >"${filename}"
    elif perl -MLWP::Simple=getstore -e"exit 0;"; then
        perl -MLWP::Simple=getstore -e"getstore('${url}', '${filename}');" 
    elif which openssl; then
        read proto server path <<<$(echo ${url//// })
        local scheme=${proto//:*}
        local url_path=/${path// //}
        local host=${server//:*}
        local port=${server//*:}
        if [[ "${host}" == "${port}" ]]; then
            [[ "${scheme}" == 'http' ]] && port=80;
            [[ "${scheme}" == 'https' ]] && port=443;
        fi

        echo -e"GET ${url_path} HTTP/1.0\nHost: ${host}\n\n" | openssl s_client -quiet -connect "${host}:${port}" >"${filename}"
    else
        return 1
    fi
}

function install_miniconda() {
    send_event "JOB_INFO" "Installing/detecting local conda installation."

    if [[ ! -d "${CONDA_BASE}" ]]; then
        # TODO: On some older systems (eg Centos 7.7, gcc 8.1.0) the latest Miniconda installer seems to segfault
        #       Miniconda3-4.4.10-Linux-x86_64.sh appears to work, but still segfaults when attempting
        #       conda update. Maybe a running inside a pre-baked Singularity image is the solution here ?
        local url="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        local filename="Miniconda3-latest-Linux-x86_64.sh"
        download_somehow "${url}" "${TMP}/${filename}" || return 1

        chmod +x "${TMP}/${filename}"
        "${TMP}/${filename}" -b -p "${CONDA_BASE}"
    fi
}

function init_conda_env() {
    # By convention, we name our Conda environments after {pipeline}-{version}
    # Each new pipeline version has it's own Conda env
    local env_name="${1}-${2}"
    local pip="${CONDA_BASE}/envs/${env_name}/bin/pip"

    # Conda activate misbehaves if nounset and errexit are set
    # https://github.com/conda/conda/issues/3200
    set +o nounset

    source "${CONDA_BASE}/etc/profile.d/conda.sh"

    if [[ ! -d "${CONDA_BASE}/envs/${env_name}" ]]; then
        send_event "JOB_INFO" "Installing dependencies (conda environment ${env_name})"

        # First we update conda itself
        conda update --yes -n base conda || return 1
        # Put git and curl in the base env, since we generally need them
        # We need gcc to compile some pip dependencies for laxydl, so grab that too :/
        conda install --yes -n base curl git gcc_linux-64 || return 1

        # Create an empty environment
        # conda create --yes -m -n "${env_name}" || return 1

##       TODO: Also consider `conda-pack` support to find and use pre-packaged environment tarballs
##       https://conda.github.io/conda-pack/ - less likely to break than an enviroment.yml (on a single arch)
#        CONDA_PACK_PATH="${JOB_PATH}/../conda-pack"
#        if [[ -f "${CONDA_PACK_PATH}/${env_name}.tar.gz" ]]; then
#          mkdir -p "${CONDA_BASE}/envs/${env_name}"
#          tar -xzf  "${CONDA_PACK_PATH}/${env_name}.tar.gz" -C "${CONDA_BASE}/envs/${env_name}"
#          conda activate "${CONDA_BASE}/envs/${env_name}" || return 1
#          conda-unpack || return 1
#        fi

        if [[ -f "${INPUT_CONFIG_PATH}/conda_environment_explicit.txt" ]]; then
            # Create environment with explicit dependencies
            conda create --name "${env_name}" --file "${INPUT_CONFIG_PATH}/conda_environment_explicit.txt" || return 1
        else
            # Create from an environment (yml) file
            conda env create --name "${env_name}" --file "${INPUT_CONFIG_PATH}/conda_environment.yml" || return 1
        fi
    fi

    # We shouldn't need to do this .. but it seems required for _some_ environments (ie M3)
    export JAVA_HOME="${CONDA_BASE}/envs/${env_name}/jre"

    # shellcheck disable=SC1090
    # source "${CONDA_BASE}/bin/activate" "${CONDA_BASE}/envs/${env_name}"
    conda activate "${CONDA_BASE}/envs/${env_name}" || return 1

    # Capture environment files if they weren't provided
    [[ ! -f "${INPUT_CONFIG_PATH}/conda_environment.yml" ]] || \
      conda env export >"${INPUT_CONFIG_PATH}/conda_environment.yml" || return 1
    [[ ! -f "${INPUT_CONFIG_PATH}/conda_environment_explicit.txt" ]] || \
      conda list --explicit >"${INPUT_CONFIG_PATH}/conda_environment_explicit.txt" || return 1

    # We can't use send_event BEFORE the env is activated since we rely on a recent
    # version of curl (>7.55)
    send_event "JOB_INFO" "Successfully activated conda environment (${env_name})."

    set -o nounset
}

function update_laxydl() {
     # Requires conda environment to be activated first
     # local pip="${CONDA_BASE}/bin/pip"
     # CONDA_PREFIX is set when the conda environment is activated
     local pip="${CONDA_PREFIX}/bin/pip"
     # "${pip}" install -U --process-dependency-links "git+https://github.com/MonashBioinformaticsPlatform/laxy#egg=laxy_downloader&subdirectory=laxy_downloader"
     # local LAXYDL_BRANCH=develop
     ${pip} install --upgrade --ignore-installed --force-reinstall \
            "laxy_downloader @ git+https://github.com/MonashBioinformaticsPlatform/laxy@${LAXYDL_BRANCH}#egg=laxy_downloader&subdirectory=laxy_downloader"
}

function add_to_manifest() {
    # Call like:
    # add_to_manifest "*.bam" "bam,alignment" '{"some":"extradata"}'

    # Writes manifest.csv with lines like:
    # checksum,filepath,type_tags,metadata
    # "md5:c0a248f159f700a340361e07421e3e62","output/sikRun/bamFiles/SRR5963435_ss_sorted_mdups.bam","bam,alignment",{"metadata":"datadata"}
    #" md5:eb8c7a1382f1ef0cf984749a42e136bc","output/sikRun/bamFiles/SRR5963441_ss_sorted_mdups.bam","bam,alignment",{"metadata":"datadata"}

    local manifest_path=${JOB_PATH}/manifest.csv
    python3 ${INPUT_SCRIPTS_PATH}/add_to_manifest.py ${manifest_path} "$1" "$2" "${3:-}"
}