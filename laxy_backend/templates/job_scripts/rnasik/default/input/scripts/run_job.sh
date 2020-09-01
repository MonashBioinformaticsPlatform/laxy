#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

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
#readonly LAXYDL_BRANCH=master
readonly LAXYDL_BRANCH=feature/custom-genomes3
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

if [[ ! -f "${AUTH_HEADER_FILE}" ]]; then
    echo "No auth token file (${AUTH_HEADER_FILE}) - exiting."
    exit 1
fi

if [[ ${IGNORE_SELF_SIGNED_CERTIFICATE} == "yes" ]]; then
    readonly CURL_INSECURE="--insecure"
    readonly LAXYDL_INSECURE="--ignore-self-signed-ssl-certificate"
else
    readonly CURL_INSECURE=""
    readonly LAXYDL_INSECURE=""
fi

##
# These memory settings are important when running BigDataScript in single-node
# 'system=local' mode. When running in multi-node 'system=generic' (or 'system=slurm')
# the CPUS and MEM values should be small (eg 2 and 2000) since they reflect only the
# resources required to run the BDS workflow manager, not the tasks it launches (BDS
# will [hopefully!] ask for appropriate resources in the sbatch jobs it launches).

RESOURCE_PROFILE="default"
[[ "${REFERENCE_GENOME_ID}" == *"Saccharomyces_cerevisiae"* ]] && RESOURCE_PROFILE="low"
# [[ "${REFERENCE_GENOME_ID}" == *"Acinetobacter"* ]] && RESOURCE_PROFILE="low"
[[ "${REFERENCE_GENOME_ID}" == *"Escherichia"* ]] && RESOURCE_PROFILE="low"

if [[ ${QUEUE_TYPE} == "local" ]]; then
    # system=local in bds.config - BDS will run each task as local process, not SLURM-aware

    # M3 (typically 24 core, ~256 Gb RAM nodes)
    MEM=64000  # defaults for Human, Mouse
    CPUS=12

    # laxy-compute-01 - 16 cores, 64 Gb RAM
    # MEM=40000  # defaults for Human, Mouse
    # CPUS=16

    if [[ "${RESOURCE_PROFILE}" == "low" ]]; then
        MEM=16000
        CPUS=4
    fi
else
    # system=generic or system=slurm in bds.config - BDS will run sbatch tasks
    MEM=3850
    CPUS=2
fi

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

# For default QUEUE_TYPE=='local'
PREFIX_JOB_CMD="/usr/bin/env bash -l -c "

if [[ "${QUEUE_TYPE}" == "slurm" ]]; then
    PREFIX_JOB_CMD="sbatch ${SLURM_OPTIONS} --wait --wrap "
fi

# In this mode we run the bds workflow manager process on the head or login node, 
# but still use SLURM for other tasks (eg mash runs on SLURM, we use bds.config 
# system=generic or system=slurm to still).
# This is because a small SLURM queue which INCLUDES the head node can become deadlocked
# with multiple bds processess waiting for tasks to complete that can't get resources,
# since all the bds processes themselves are using those resource. The easiet solution
# is to run the bds process itself outside of SLURM so it's resources aren't counted
# (and hope that we don't exceed available RAM to often)
if [[ "${QUEUE_TYPE}" == "slurm-hybrid" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

if [[ "${QUEUE_TYPE}" == "local" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

# TODO: Maybe this should be a called in a trap statement near the top of the script eg:
# trap "rm -f ${AUTH_HEADER_FILE}" EXIT
function remove_secrets() {
    if [[ ${DEBUG} != "yes" ]]; then
      rm -f "${AUTH_HEADER_FILE}"
    fi
}

function update_permissions() {
    send_event "JOB_INFO" "Updating Unix file permissions for job outputs on compute node."

    # This can be used to update the permission on files after job completion
    # (eg if you want to automatically share files locally with a group of users on a compute resource).
    chmod "${JOB_DIR_PERMS}" "${JOB_PATH}"
    find "${JOB_PATH}" -type d -exec chmod "${JOB_DIR_PERMS}" {} \;
    find "${JOB_PATH}" -type f -exec chmod "${JOB_FILE_PERMS}" {} \;
}

function add_sik_config() {
   send_event "JOB_INFO" "Configuring RNAsik (sik.config)."

   # Find the ComputeResource specific sik.config, and if there is none, use the default.
   # Always copy it to the job input directory to preserve it.
    local SIK_CONFIG

    SIK_CONFIG="${JOB_PATH}/../sik.config"
    if [[ ! -f "${SIK_CONFIG}" ]]; then
        SIK_CONFIG="$(dirname $(which RNAsik))/../opt/rnasik-${PIPELINE_VERSION}/configs/sik.config"
    fi

    # special lower resource sik.config for yeast
    if [[ "${RESOURCE_PROFILE}" == "low" ]]; then
        echo "Using low resource sik.config."
        SIK_CONFIG="${JOB_PATH}/../sik.yeast.config"
    fi

    cp -n "${SIK_CONFIG}" "${INPUT_CONFIG_PATH}/sik.config" || true
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
         "${JOB_EVENT_URL}" || true &
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

function get_reference_data_aws() {
    # TODO: Be smarter about what we pull in - eg only the reference required,
    #       not the whole lot. Assume reference is present if appropriate
    #       directory is there
    if [[ ! -d "${REFERENCE_BASE}" ]]; then
        mkdir -p "${REFERENCE_BASE}"
        pushd "${REFERENCE_BASE}"
        aws s3 sync s3://bioinformatics-au/iGenomes .
        popd
    fi
}

function curl_gunzip_check {
     local url="${1}"
     local gunziped_file="${2}"
     local md5="${3}"

     if [[ "${url}" == *gz ]]; then
         curl "${url}" \
              --silent --retry 10 | gunzip -c >"${gunziped_file}"
     else
         curl "${url}" \
              --silent --retry 10 >"${gunziped_file}"
     fi
     DL_EXIT_CODE=$?
     checksum=$(md5sum "${gunziped_file}" | cut -f 1 -d ' ')
     if [[ "${checksum}" != "${md5}" ]]; then
         return 1
     fi

     return ${DL_EXIT_CODE}
}

# TODO: This should probably be handled by laxydl to prevent simultaneous downloads by concurrent jobs
function download_ref_urls() {
     local fasta_url="${1}"
     local annotation_file_url="${2}"
     local fasta_md5="${3}"
     local annotation_file_md5="${4}"
     local annotation_format="${5:-gtf}"
     local fasta="${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/genome.fa"
     local annotation_ext="gtf"

     if [[ "${annotation_format}" == "gff" ]] || \
        [[ "${annotation_file_url}" == *.gff.gz ]] || \
        [[ "${annotation_file_url}" == *.gff3.gz ]]; then
        annotation_ext="gff"
     fi

     local annotation_file="${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/genes.${annotation_ext}"

     if [[ ! -f "${fasta}" ]]; then
         mkdir -p "${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta"
         curl_gunzip_check "${fasta_url}" \
                           "${fasta}" \
                           "${fasta_md5}" || exit 1
     fi
     if [[ ! -f "${annotation_file}" ]]; then
         mkdir -p "${REFERENCE_BASE}/${REF_ID}/Annotation/Genes"
         curl_gunzip_check "${annotation_file_url}" \
                           "${annotation_file}" \
                           "${annotation_file_md5}" || exit 1
     fi
}

# TODO: Downloads here should probably be handled by laxydl to prevent simultaneous downloads by concurrent jobs
function get_reference_genome() {
     local REF_ID=$1

     # noop if we are using a user supplied genome - gets downloaded as part for the fetch_files list instead
    if [[ -z "${REF_ID}" ]]; then
        return 0
     fi

     send_event "JOB_INFO" "Getting reference genome (${REF_ID})."

     if [[ "${REF_ID}" == "Homo_sapiens/Ensembl/GRCh38" ]]; then
         download_ref_urls "ftp://ftp.ensembl.org/pub/release-95/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna_sm.primary_assembly.fa.gz" \
                       "ftp://ftp.ensembl.org/pub/release-95/gtf/homo_sapiens/Homo_sapiens.GRCh38.95.gtf.gz" \
                       "6ee1ec578b2b6495eb7da26885d0a496" \
                       "cfe6daf315889981b6c22789127232ef"
         return 0
     fi

     if [[ "${REF_ID}" == "Danio_rerio/Ensembl/GRCz11.97" ]]; then
         download_ref_urls "ftp://ftp.ensembl.org/pub/release-97/fasta/danio_rerio/dna/Danio_rerio.GRCz11.dna_sm.toplevel.fa.gz" \
                       "ftp://ftp.ensembl.org/pub/release-97/gtf/danio_rerio/Danio_rerio.GRCz11.97.gtf.gz" \
                       "90e7dcb80ab9ca2a4ae4033a4b8d83c4" \
                       "aaab04e8713b1712ae998e9d045e5270"
         return 0
     fi

     if [[ "${REF_ID}" == "Danio_rerio/Ensembl/GRCz11.97-noalt" ]]; then
         # TODO: We need to download the proper Danio_rerio/Ensembl/GRCz11.97 then
         #       drop CHR_ALT contigs by running:
         #       cd ${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta
         #       seqmagick mogrify --pattern-exclude CHR_ALT genome.fa genome.fa
         #
         return 0
     fi

     # https://www.ncbi.nlm.nih.gov/genome/?term=Chelonia%20mydas
     # TODO: This is a GFF3 but we are saving with a .gtf extension ! Bad.
     #       Need to either deal with gtf/gff alternatives (eg file discovery in Chelonia_mydas/NCBI/CheMyd_1.0/Annoation/Genes
     #       Or automatically convert all GFFs to GTF format (or vice versa). Yeck.
     # TODO: This genome contains many small contigs that tend to break the RAM budget when generating a STAR index.
     #       We need to make a custom version where we drop the contigs without any annotated exons like:
     #         samtools faidx \
     #           "${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/genome.fa" \
     #           $(grep '\texon\t' "${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/genes.gtf" \
     #              |cut -f1 | sort | uniq | xargs) >"${REFERENCE_BASE}/${REF_ID}-exon-contigs/Sequence/WholeGenomeFasta/genome.fa"
     if [[ "${REF_ID}" == "Chelonia_mydas/NCBI/CheMyd_1.0" ]]; then
         download_ref_urls \
                      "ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/344/595/GCF_000344595.1_CheMyd_1.0/GCF_000344595.1_CheMyd_1.0_genomic.fna.gz" \
                      "ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/344/595/GCF_000344595.1_CheMyd_1.0/GCF_000344595.1_CheMyd_1.0_genomic.gff.gz" \
                      "4d4ea95ed027d5cdc44b71c7a6587376" \
                      "069b82e9d71870d724f89c0ba4a31242"
         return 0
     fi

     # This genome also contains many small contigs (~2300 total, where ~1500 are without exons).
     # I experimented with dropping contigs that don't contain exons, as per Chelonia_mydas/NCBI/CheMyd_1.0,
     # however this wasn't necessary since the STAR index for the unmodified reference builds using ~30Gb RAM.
     if [[ "${REF_ID}" == "Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0" ]]; then
         download_ref_urls \
                      "ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/002/204/515/GCF_002204515.2_AaegL5.0/GCF_002204515.2_AaegL5.0_genomic.fna.gz" \
                      "ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/002/204/515/GCF_002204515.2_AaegL5.0/GCF_002204515.2_AaegL5.0_genomic.gff.gz" \
                      "64c3dec8867dd2c96f0e67655ea144c5" \
                      "8419ba1da70d832eefadf467cf697031"
         return 0
     fi

     if [[ "${REF_ID}" == "Aedes_aegypti/VectorBase/AaegL5.2" ]]; then
        download_ref_urls \
         "https://www.vectorbase.org/sites/default/files/ftp/downloads/Aedes-aegypti-LVP_AGWG_CHROMOSOMES_AaegL5.fa.gz" \
         "https://www.vectorbase.org/sites/default/files/ftp/downloads/Aedes-aegypti-LVP_AGWG_BASEFEATURES_AaegL5.2.gff3.gz" \
         "b1182d3854b59f50123b453690bfa657" \
         "4d1682b6624974040469243abd788774"
        return 0
     fi

     if [[ "${REF_ID}" == "Plasmodium_falciparum/PlasmoDB/3D7-release-39" ]]; then
        download_ref_urls \
         "https://plasmodb.org/common/downloads/release-39/Pfalciparum3D7/fasta/data/PlasmoDB-39_Pfalciparum3D7_Genome.fasta" \
         "https://plasmodb.org/common/downloads/release-39/Pfalciparum3D7/gff/data/PlasmoDB-39_Pfalciparum3D7.gff" \
         "809039c5aff401fe31035c2e7f0522e6" \
         "ab664575518980ad51890a67e624b21f" \
         "gff"
        return 0
     fi

     if [[ "${REF_ID}" == "Escherichia_coli/Ensembl/GCA_000019425.1__release-46" ]]; then
        download_ref_urls \
          "ftp://ftp.ensemblgenomes.org/pub/bacteria/release-46/fasta/bacteria_9_collection/escherichia_coli_str_k_12_substr_dh10b/dna/Escherichia_coli_str_k_12_substr_dh10b.ASM1942v1.dna_sm.toplevel.fa.gz" \
          "ftp://ftp.ensemblgenomes.org/pub/bacteria/release-46/gff3/bacteria_9_collection/escherichia_coli_str_k_12_substr_dh10b/Escherichia_coli_str_k_12_substr_dh10b.ASM1942v1.46.gff3.gz" \
          "1c17f0cabeb0fe1de64060ea492067dd" \
          "461d99ce76a42a9ec205df52b16aff83"
        return 0
     fi

     if [[ "${REF_ID}" == "Escherichia_coli/Ensembl/GCA_000005845.2__release-46" ]]; then
        download_ref_urls \
          "ftp://ftp.ensemblgenomes.org/pub/bacteria/release-46/fasta/bacteria_0_collection/escherichia_coli_str_k_12_substr_mg1655/dna/Escherichia_coli_str_k_12_substr_mg1655.ASM584v2.dna_sm.toplevel.fa.gz" \
          "ftp://ftp.ensemblgenomes.org/pub/bacteria/release-46/gff3/bacteria_0_collection/escherichia_coli_str_k_12_substr_mg1655/Escherichia_coli_str_k_12_substr_mg1655.ASM584v2.46.gff3.gz" \
          "9f96e24975f42df8c398797414edcfcc" \
          "fc96ca62b7b862690d956ed23fc2e11f"
        return 0
     fi

     if [[ ! -f "${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/genes.gtf" ]]; then
         aws s3 --no-sign-request --region eu-west-1 sync \
             s3://ngi-igenomes/igenomes/${REF_ID}/Annotation/Genes/ ${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/ --exclude "*" --include "genes.gtf"
         # Grab the README.txt too (contains release information), if present
         aws s3 --no-sign-request --region eu-west-1 cp \
             "s3://ngi-igenomes/igenomes/${REF_ID}/Annotation/README.txt" "${REFERENCE_BASE}/${REF_ID}/Annotation/README.txt" || true
     fi
     if [[ ! -f "${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/genome.fa" ]]; then
         aws s3 --no-sign-request --region eu-west-1 sync \
             s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/WholeGenomeFasta/ ${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/
         # AWS-iGenomes pre-generated STAR indices are incompatible with newer versions of STAR (>=2.7.2b)
         # aws s3 --no-sign-request --region eu-west-1 sync \
         #     s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/STARIndex/ ${REFERENCE_BASE}/${REF_ID}/Sequence/STARIndex/
     fi
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

function cleanup_tmp_files() {
    # Failed RNAsik runs can leave some temporary files around which we rarely want to keep
    find "${JOB_PATH}/output/sikRun/countFiles/" -type f -name "temp-core-*.tmp" -delete
    find "${JOB_PATH}/output/tmp/" -type f -delete
}

function get_strandedness_metadata() {
    local prediction="unknown"
    local bias="null"
    # RNAsik <=1.5.3
    local strandInfoOld="${JOB_PATH}/output/sikRun/countFiles/strandInfo.txt"
    # RNAsik >=1.5.4
    local strandInfoGuess="${JOB_PATH}/output/sikRun/countFiles/strandInfoGuess.txt"
    local strandInfoFile="${strandInfoGuess}"

    [[ -f  "${strandInfoOld}" ]] && strandInfoFile="${strandInfoOld}"
    # [[ -f  "${strandInfoGuess}" ]] && local strandInfoFile="${strandInfoGuess}"

    if [[ -f "${strandInfoFile}" ]]; then
      prediction=$(cut -f 1 -d ',' "${strandInfoFile}")
      bias=$(cut -f 2 -d ',' "${strandInfoFile}")
      echo '{"metadata":{"results":{"strandedness":{"predicted":"'${prediction}'","bias":'${bias}'}}}}'
    else
      echo '{"metadata":{"results":{"strandedness":{"predicted":"unknown"}}}}'
    fi
}

# TODO: This has become complex enough that it probably should be a Python script for file registration,
#  (pulled into the Conda environment, just like laxydl)
function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    # Not find and tag specific files/filetypes
    add_to_manifest "*.bam" "bam,alignment"
    add_to_manifest "*.bai" "bai"
    add_to_manifest "*.fastq.gz" "fastq"
    add_to_manifest "**/multiqc_report.html" "multiqc,html,report"
    add_to_manifest "**/RNAsik.bds.*.html" "bds,logs,html,report"
    add_to_manifest "**/*_fastqc.html" "fastqc,html,report"
    add_to_manifest "**/*StrandedCounts-withNames-proteinCoding.txt" "counts,degust,degust-protein-coding"
    add_to_manifest "**/*StrandedCounts.txt" "counts"
    add_to_manifest "**/*StrandedCounts-withNames.txt" "counts,degust,degust-all-biotypes"
    add_to_manifest "output/sikRun/countFiles/strandInfo*.txt" "strand-info"
    # TODO: These two recursive commands to add the remaining files don't seem to be working ?
    add_to_manifest "input/*" ""
    add_to_manifest "output/*" ""
    add_to_manifest "input/**/*" ""
    add_to_manifest "output/**/*" ""

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
     --data-binary @${JOB_PATH}/manifest.csv \
     "${JOB_FILE_REGISTRATION_URL}"
}

function setup_bds_config() {
    send_event "JOB_INFO" "Configuring BigDataScript (bds.config)."

    local default_bds_config
    local job_bds_config

    default_bds_config="$(which bds).config"
    job_bds_config="${INPUT_CONFIG_PATH}/bds.config"

    # Check for custom bds.config
    if [[ -f "${JOB_PATH}/../bds.config" ]]; then
        default_bds_config="${JOB_PATH}/../bds.config"
    fi

    # TODO: This won't work yet since the default bds.config contains
    # ~/.bds/clusterGeneric/* paths to the SLURM wrapper scripts.
    # The SLURM wrappers don't appear to come with the bds conda package (yet)
    # if [ "${QUEUE_TYPE}" == "slurm" ]; then
    #     sed -i 's/#system = "local"/system = "generic"/' ${job_bds_config}
    # fi

    if [[ "${QUEUE_TYPE}" == "local" ]] && [[ -f "${JOB_PATH}/../bds.local.config" ]]; then
        echo "Using system=local (non-queued) bds.config."
        default_bds_config="${JOB_PATH}/../bds.local.config"
    # special lower resource bds.config for yeast
    elif [[ "${RESOURCE_PROFILE}" == "low" ]] && [[ -f "${JOB_PATH}/../bds.yeast.config" ]]; then
        echo "Using low resource bds.yeast.config."
        default_bds_config="${JOB_PATH}/../bds.yeast.config"
    fi

    cp -n "${default_bds_config}" "${job_bds_config}" || true

    if [[ -f "${job_bds_config}" ]]; then
        export RNASIK_BDS_CONFIG="${job_bds_config}"
    fi
}

function get_input_data_urls() {
    # Output is one URL one per line
    local urls
    # urls=$(jq '.sample_cart.samples[].files[][]' <"${PIPELINE_CONFIG}" | sed s'/"//g')
    urls=$(jq '.params.fetch_files[]' <"${PIPELINE_CONFIG}" | sed s'/"//g')
    echo "${urls}"
}

function detect_pairs() {
    RNASIK_PAIR_EXTN_ARGS=$(${INPUT_SCRIPTS_PATH}/helper.py pairids "${INPUT_READS_PATH}") || fail_job 'detect_pairs' '' $?

    if [[ "${RNASIK_PAIR_EXTN_ARGS}" = *" -paired "* ]]; then
        send_event "JOB_INFO" "(Looks like unpaired reads)"
    else
        send_event "JOB_INFO" "(Looks like paired end data) 👍"
    fi
}

function generate_samplesheet() {
    pushd ${JOB_PATH}
    ${INPUT_SCRIPTS_PATH}/helper.py samplesheet "${PIPELINE_CONFIG}" >"${INPUT_CONFIG_PATH}/samplesSheet.txt"
    popd

    send_event "JOB_INFO" "Generated an RNAsik samplesSheet.txt 🧪"
}

function set_genome_index_arg() {
    GENOME_INDEX_ARG=""
    if [[ -d "${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex" ]]; then
        GENOME_INDEX_ARG="-genomeIdx ${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex"
    fi

    old_star=$(python -c 'import semver; print(semver.compare("'${PIPELINE_VERSION}'".split("-")[0], "1.5.4"))')
    # Pre-computed indices are different for pre-2.7.0 versions of STAR
    if [[ "${old_star}" == "-1" ]]; then
        GENOME_INDEX_ARG=""
        if [[ -d "${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex-pre-2.7.0" ]]; then
            GENOME_INDEX_ARG="${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex-pre-2.7.0"
        fi
    fi
}

function set_reference_paths() {
    # See if we can find a custom reference in the fetch_files list
    local _fasta_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_sequence") | .name' "${PIPELINE_CONFIG}" || echo '')
    local _annot_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_annotation") | .name' "${PIPELINE_CONFIG}" || echo '')

    [[ -z ${_fasta_fn} ]] || GENOME_FASTA="${INPUT_REFERENCE_PATH}/${_fasta_fn}"
    [[ -z ${_annot_fn} ]] || ANNOTATION_FILE="${INPUT_REFERENCE_PATH}/${_annot_fn}"

    # If there is no custom genome, then we assume we are using a pre-defined references
    if [[ -z ${_fasta_fn} ]]; then
        GENOME_FASTA="${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/WholeGenomeFasta/genome.fa"
    fi

    if [[ -z ${_annot_fn} ]]; then
        ANNOTATION_FILE="${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Annotation/Genes/genes"

        if [[ -f "${ANNOTATION_FILE}.gtf" ]]; then
            ANNOTATION_FILE="${ANNOTATION_FILE}.gtf"
        elif [[ -f "${ANNOTATION_FILE}.gff" ]]; then
            ANNOTATION_FILE="${ANNOTATION_FILE}.gff"
        else
            send_event "JOB_INFO" "This isn't going so well. Unable to find annotation file"
            send_job_finished 1
            exit 1
        fi
    fi
}

function fastq_sanity_check() {
    #
    # Read every FASTQ with seqkit, exit with error if any fail
    #

    local orig_errexit=${-//[^e]/}
    set -o errexit
    local _cpus=4

    mkdir -p "${JOB_PATH}/output/seqkit_stats"
    echo -e "This directory contains the output from 'seqkit stats' for the FASTQ input files provided. "\
            "It is primarily intended to catch corrupted FASTQ files early, before the main pipeline runs." \
            >"${JOB_PATH}/output/seqkit_stats/README.txt"
    for fq in $(find "${INPUT_READS_PATH}" -name "*.f*[q,a].gz"); do
        local _fn=$(basename "${fq}")
        seqkit stats -j $_cpus $fq >"${JOB_PATH}/output/seqkit_stats/${_fn}.tsv" 2>"${JOB_PATH}/output/seqkit_stats/${_fn}.err" || \
          { send_event "JOB_INFO" "Something wrong with input file: ${_fn}" & \
            send_job_metadata '{"metadata": {"error": {"bad_input_file": "'${_fn}'"}}}'; \
            return 1; }
    done

    if [[ -z "${orig_errexit}" ]]; then
        set +o errexit
    fi
}

function run_mash_screen() {
    # This is additional 'pre-pipeline' step - might make sense integrating it as an option to RNAsik
    # in the future.

    #local _globstat_state=$(shopt -p globstar)
    #shopt -s globstar

    send_event "JOB_INFO" "Starting Mash screen (detects organism/contamination)."

    local -r mash_db_base="${REFERENCE_BASE}/../mash"
    local -r mash_reference_sketches="${mash_db_base}/refseq.genomes.k21s1000.msh"

    mkdir -p "${mash_db_base}"
    if [[ ! -f "${mash_reference_sketches}/refseq.genomes.k21s1000.msh" ]]; then
        curl -L -o "${mash_reference_sketches}" -C - "https://gembox.cbcb.umd.edu/mash/refseq.genomes.k21s1000.msh" || true
    fi

    local mash_reads=$(find "${INPUT_READS_PATH}" -name "*.f*[q,a].gz" | xargs)
    local cmd="mash screen -w -p 8 ${mash_reference_sketches}"
    # TODO: Try subsamping (1000?) via process substitution - should make mash screen closer to constant time
    #       A few quick tests suggest it's no faster subsampled in this way (I/O limited ?)
    # local cmd="mash screen -w -p 8 ${mash_reference_sketches} <(seqtk sample -s 42 ${mash_reads} 1000)"
    local mash_outdir="${JOB_PATH}/output/mash/"
    mkdir -p "${mash_outdir}"
    cat >"${INPUT_SCRIPTS_PATH}/run_mash.sh" <<EOM
#!/bin/bash
#SBATCH --mem 16G
#SBATCH --cpus-per-task=8
#SBATCH --time=30
#SBATCH --ntasks-per-node=1
#SBATCH --ntasks=1
#SBATCH --job-name="laxy:mash:${JOB_ID}"
#SBATCH --error="${JOB_PATH}/output/mash_screen.err"
{% if SLURM_EXTRA_ARGS %}
#SBATCH {{ SLURM_EXTRA_ARGS }}
{% endif %}
# #SBATCH --qos=shortq
# #SBATCH --partition=short,comp

fqfile="\${1}"
sample_base="\$(basename \${fqfile%%.*})"

mash_outfile="${mash_outdir}/\${sample_base}_mash_screen.tab"

mkdir -p "${mash_outdir}"

${cmd} "\${fqfile}" | sort -gr >"\${mash_outfile}" && \
grep '_ViralProj\|_ViralMultiSegProj' "\${mash_outfile}" >"${mash_outdir}/\${sample_base}_mash_screen_virus.tab" && \
grep -v '_ViralProj\|_ViralMultiSegProj' "\${mash_outfile}" >"${mash_outdir}/\${sample_base}_mash_screen_nonvirus.tab"
EOM

    if [[ "${QUEUE_TYPE}" == "slurm" || "${QUEUE_TYPE}" == "slurm-hybrid" ]]; then
        for f in $mash_reads; do
            sbatch --output="${mash_outdir}/slurm.out" \
                   --error="${mash_outdir}/slurm.err" \
                   --open-mode=append \
                   --parsable \
                   "${INPUT_SCRIPTS_PATH}/run_mash.sh" "${f}" >>"${JOB_PATH}/slurm.jids"
        done
    else
        for f in $mash_reads; do
            bash "${INPUT_SCRIPTS_PATH}/run_mash.sh" "${f}" >>"${JOB_PATH}/job.pids"
            # local sample_base="${mash_outdir}/${f%%.*}"
            # local mash_outfile="${sample_base}_mash_screen.tab"
            # eval ${cmd} "${f}" | sort -gr >"${mash_outfile}" && \
            # grep '_ViralProj\|_ViralMultiSegProj' "${mash_outfile}" >"${sample_base}_mash_screen_virus.tab" && \
            # grep -v '_ViralProj\|_ViralMultiSegProj' "${mash_outfile}" >"${sample_base}_mash_screen_nonvirus.tab"
        done
    fi
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

        # Download reference genome files. 
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
            --type-tags reference_genome \
            --create-missing-directories \
            --skip-existing \
            --destination-path "${INPUT_REFERENCE_PATH}"

        # RNAsik automatically creates an uncompressed copy of the reference in sikRun/refFiles,
        # so we don't need to do this (nor do we need laxydl --copy-from-cache to allow it)
        # find "${INPUT_REFERENCE_PATH}" -maxdepth 1 -name '*.gz' -exec gunzip {} \;

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
            --type-tags ngs_reads \
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

function capture_environment_variables() {
    env >"${JOB_PATH}/output/job_env.out"
}

#function filter_ena_urls() {
#    local urls
#    urls=$(get_input_data_urls)
#    local ena_urls
#    for u in ${urls}; do
#        if [[ $u = *"ebi.ac.uk"* ]]; then
#            ena_urls="${ena_urls}"'\n'"${u}"
#        fi
#    done
#    echo "${ena_urls}"
#}

update_permissions || true

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

mkdir -p ${INPUT_CONFIG_PATH} ${INPUT_SCRIPTS_PATH} ${INPUT_READS_PATH} ${INPUT_REFERENCE_PATH}

####
#### Setup and import a Conda environment
####

install_miniconda || fail_job 'install_miniconda' '' $?

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "rnasik" "${PIPELINE_VERSION}" || fail_job 'init_conda_env' '' $?

update_laxydl || send_error 'update_laxydl' '' $?

# get_reference_data_aws
get_reference_genome "${REFERENCE_GENOME_ID}" || fail_job 'get_reference_genome' '' $?

# Set the GENOME_FASTA and ANNOTATION_FILE global variable based on presence of 
# custom genomes and genes.gtf vs. genes.gff
set_reference_paths || send_error 'set_reference_paths' '' $?

# Make a copy of the bds.config in the $JOB_PATH, possibly modified for SLURM
setup_bds_config || send_error 'setup_bds_config' '' $?

# Make a copy of the sik.config into $INPUT_CONFIG_PATH/sik.config
add_sik_config || send_error 'add_sik_config' '' $?

####
#### Stage input data ###
####

download_input_data || fail_job 'download_input_data' '' $?

capture_environment_variables || true

fastq_sanity_check || fail_job 'fastq_sanity_check' '' $?

detect_pairs

generate_samplesheet || fail_job 'generate_samplesheet' '' $?

RNASIK_SAMPLESHEET_ARG=""
if [[ -s "${INPUT_CONFIG_PATH}/samplesSheet.txt" ]]; then
    RNASIK_SAMPLESHEET_ARG=" -samplesSheet ${INPUT_CONFIG_PATH}/samplesSheet.txt "
fi

cd "${JOB_PATH}/output"

####
#### Job happens in here
####

send_event "JOB_PIPELINE_STARTING" "Pipeline starting."

run_mash_screen || true

# Don't exit on error, since we want to capture exit code and do an HTTP
# request with curl upon failure
set +o errexit

# quick and dirty detection of paired-end or not
# PAIRIDS=""
# EXTN=".fastq.gz"
# detect_pairs || fail_job 'detect_pairs' '' $?

# set_genome_index_arg
GENOME_INDEX_ARG=""

send_event "JOB_INFO" "Starting RNAsik."

EXIT_CODE=99
RETRY_COUNT=0
MAX_RETRIES=3
RETRY_DELAY=10
# Since BDS pipelines (in theory) can be just restarted and continue after a failure,
# this while loop might make things more robust in the face of temporary failures
# (eg transient SLURM queue submission errors)
while [[ "${EXIT_CODE}" -ne 0 ]] && [[ ${RETRY_COUNT} -le ${MAX_RETRIES} ]]; do

    if [[ ${RETRY_COUNT} -gt 0 ]]; then
        send_event "JOB_INFO" "Restarting RNAsik after (temporary?) failure (retry $RETRY_COUNT)."
        sleep ${RETRY_DELAY}
    fi

    # _PAIR_ARGS=''
    # if [[ ! -z "${PAIRIDS}" ]]; then
    #   _PAIR_ARGS=" -paired -pairIds ${PAIRIDS} "
    # fi

    ${PREFIX_JOB_CMD} \
       "RNAsik \
           -configFile ${INPUT_CONFIG_PATH}/sik.config \
           -align ${PIPELINE_ALIGNER} \
           -fastaRef ${GENOME_FASTA} \
           -gtfFile ${ANNOTATION_FILE} \
           ${GENOME_INDEX_ARG} \
           -fqDir "${INPUT_READS_PATH}" \
           -counts \
           -all \
           ${RNASIK_PAIR_EXTN_ARGS} \
           ${RNASIK_SAMPLESHEET_ARG} \
           >>rnasik.out 2>>rnasik.err" \
    >>"${JOB_PATH}/slurm.jids"

    # Capture the exit code of the important process, to be returned
    # in the curl request below
    EXIT_CODE=$?

    RETRY_COUNT=$((RETRY_COUNT+1))
done

# Some job scripts might have things that occur after the main pipeline
# run - so we signal when the 'pipeline' computation completed, but this is
# considered a distinct event from the whole job completing (that will be
# generated as a side effect of calling JOB_COMPLETE_CALLBACK_URL)
if [[ ${EXIT_CODE} -ne 0 ]]; then
  send_event "JOB_PIPELINE_FAILED" "Pipeline failed." '{"exit_code":'${EXIT_CODE}'}'
else
  send_event "JOB_PIPELINE_COMPLETED" "Pipeline completed." '{"exit_code":'${EXIT_CODE}'}'
fi

send_job_metadata $(get_strandedness_metadata) || true

cleanup_tmp_files || true

update_permissions || true

cd "${JOB_PATH}"
register_files || true

####
#### Notify service we are done
####

# Authorization header passed to curl is stored in a @file so it doesn't leak in 'ps' etc.

send_job_finished "${EXIT_CODE}"

# Extra security: Remove the access token now that we don't need it anymore
remove_secrets
