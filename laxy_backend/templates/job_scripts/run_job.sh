#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"
# export JOB_ID="${JOB_ID:-}"
# export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"

readonly TMP="${PWD}/../tmp"
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly REFERENCE_GENOME="{{ REFERENCE_GENOME }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
readonly JOB_PATH=${PWD}
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly REFERENCE_BASE="${PWD}/../references/iGenomes"

readonly DOWNLOAD_CACHE_PATH="${PWD}/../cache"
readonly USE_DOWNLOAD_CACHE="yes"

readonly SCHEDULER="slurm"
# readonly SCHEDULER="local"

readonly BDS_SINGLE_NODE="yes"

##
# These memory settings are important when running BigDataScript in single-node
# 'system=local' mode. When running in multi-node 'system=generic' (or 'system=slurm')
# the CPUS and MEM values should be small (eg 2 and 2000) since they reflect only the
# resources required to run the BDS workflow manager, not the tasks it launches (BDS
# will [hopefully!] ask for appropriate resources in the sbatch jobs it launches).

if [[ ${BDS_SINGLE_NODE} == "yes" ]]; then
    # system=local in bds.config - BDS will run each task as local process, not SLURM-aware

    MEM=64000  # defaults for Human, Mouse
    CPUS=12
    if [[ "$REFERENCE_GENOME" == "Saccharomyces_cerevisiae/Ensembl/R64-1-1" ]]; then
        MEM=16000 # yeast (uses ~ 8Gb)
        CPUS=8
    fi
else
    # system=generic or system=slurm in bds.config - BDS will run sbatch tasks
    MEM=2000
    CPUS=2
fi

readonly SRUN_OPTIONS="--cpus-per-task=${CPUS} --mem=${MEM} -t 1-0:00 --ntasks-per-node=1 --ntasks=1 --job-name=laxy:${JOB_ID}"

PREFIX_JOB_CMD=""
if [[ "${SCHEDULER}" == "slurm" ]]; then
    PREFIX_JOB_CMD="srun ${SRUN_OPTIONS} "
fi

function send_event() {
    local event=${1:-"HEARTBEAT"}
    local extra=${2:-"{}"}
    # escape double quotes since this is JSON nested inside JSON ?
    # extra=$(sed 's/"/\\"/g' <<< "${extra}")

    # || true so we don't stop on errors irrespective of set -o errexit state,
    # so if a curl call fails we don't bring down the whole script
    # NOTE: curl v7.55+ is required to use -H @filename

    VERBOSITY="--silent"
    if [ "${DEBUG}" == "yes" ]; then
        # NOTE: verbose mode should NOT be used in production since it prints
        # full headers to stdout/stderr, including Authorization tokens.
        VERBOSITY="-vvv"
    fi

    curl -X POST \
         -H "Content-Type: application/json" \
         -H @"${JOB_PATH}/.private_request_headers" \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"event":"'"${event}"'","extra":'"${extra}"'}' \
         ${VERBOSITY} \
         "${JOB_EVENT_URL}" || true
}

function install_miniconda() {
    if [ ! -d "${CONDA_BASE}" ]; then
         wget --directory-prefix "${TMP}" -c "https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh"
         chmod +x "${TMP}"/Miniconda3-latest-Linux-x86_64.sh
         "${TMP}"/Miniconda3-latest-Linux-x86_64.sh -b -p "${CONDA_BASE}"
    fi
}

function init_conda_env() {
    # By convention, we name our Conda environments after {pipeline}-{version}
    # Each new pipeline version has it's own Conda env

    local env_name="${1}-${2}"

    if [ ! -d "${CONDA_BASE}/envs/${env_name}" ]; then

        # Conda activate misbehaves if nounset and errexit are set
        # https://github.com/conda/conda/issues/3200
        set +o nounset
        # First we update conda itself
        ${CONDA_BASE}/bin/conda update --yes -n base conda

        # Add required channels
        ${CONDA_BASE}/bin/conda config --add channels serine/label/dev \
                                       --add channels serine \
                                       --add channels bioconda \
                                       --add channels conda-forge

        # Create a base environment
        ${CONDA_BASE}/bin/conda create --yes -m -n "${env_name}"

        # Install an up-to-date curl and GNU parallel
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" curl parallel jq awscli

        # Then install rnasik
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" \
                     rnasik=${2}

        # Environment takes a very long time to solve if qualimap is included initially
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" qualimap
    fi

    # We shouldn't need to do this .. but it seems required for _some_ environments (ie M3)
    export JAVA_HOME="${CONDA_BASE}/envs/${env_name}/jre"

    # shellcheck disable=SC1090
    source "${CONDA_BASE}/bin/activate" "${CONDA_BASE}/envs/${env_name}"

    set -o nounset
}

function get_reference_data_aws() {
    # TODO: Be smarter about what we pull in - eg only the reference required,
    #       not the whole lot. Assume reference is present if appropriate
    #       directory is there
    if [ ! -d "${REFERENCE_BASE}" ]; then
        prev="${PWD}"
        mkdir -p "${REFERENCE_BASE}"
        cd "${REFERENCE_BASE}"
        aws s3 sync s3://bioinformatics-au/iGenomes .
        cd "${prev}"
    fi
}

function get_igenome_aws() {
     local REF_ID=$1
     aws s3 --no-sign-request --region eu-west-1 sync \
         s3://ngi-igenomes/igenomes/${REF_ID}/Annotation/Genes/ ${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/ --exclude "*" --include "genes.gtf"
    aws s3 --no-sign-request --region eu-west-1 sync \
        s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/WholeGenomeFasta/ ${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/

}

function find_filetype() {
    # eg, *.fastq.gz or *.bam
    local pattern=$1
    # eg, fastq,bam,bam.sorted
    local tags=$2
    # checksum,filepath,type_tags
    find . -name "${pattern}" -type f -exec bash -c 'fn="$1"; echo -e "md5:$(md5sum "$fn" | sed -e "s/  */,/g"),\"'"${tags}"'\""' _ {} \;
}

function register_files() {
    echo "checksum,filepath,type_tags" >${JOB_PATH}/manifest.csv
    find_filetype "*.bam" "bam,alignment" >>${JOB_PATH}/manifest.csv
    find_filetype "*.bai" "bai" >>${JOB_PATH}/manifest.csv
    find_filetype "*.fastq.gz" "fastq" >>${JOB_PATH}/manifest.csv
    find_filetype "multiqc_report.html" "multiqc,html,report" >>${JOB_PATH}/manifest.csv
    find_filetype "RNAsik.bds.*.html" "bds,logs,html,report" >>${JOB_PATH}/manifest.csv
    find_filetype "*StrandedCounts*.txt" "counts,degust" >>${JOB_PATH}/manifest.csv

    curl -X POST \
     -H "Content-Type: text/csv" \
     -H @"${JOB_PATH}/.private_request_headers" \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     --data-binary @manifest.csv \
     "${JOB_FILE_REGISTRATION_URL}"
}

function setup_bds_config() {
    BDS_CONFIG="${JOB_PATH}/bds.config"
    cp "$(which bds).config" "${BDS_CONFIG}"

    # TODO: This won't work yet since the default bds.config contains
    # ~/.bds/clusterGeneric/* paths to the SLURM wrapper scripts.
    # The SLURM wrappers don't appear to come with the bds conda package (yet)
    # if [[ "${SCHEDULER}" == "slurm" ]]; then
    #     sed -i 's/#system = "local"/system = "generic"/' ${BDS_CONFIG}
    # fi

    if [ -f "${BDS_CONFIG}" ]; then
        export RNASIK_BDS_CONFIG="${BDS_CONFIG}"
    fi
}

function get_input_data_urls() {
    # Output is one URL one per line
    local urls
    urls=$(jq '.sample_set.samples[].files[][]' <pipeline_config.json | sed s'/"//g')
    echo "${urls}"
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


####
#### Pull in reference data from S3
####

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

####
#### Setup and import a Conda environment
####

install_miniconda

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "rnasik" "${PIPELINE_VERSION}"

# get_reference_data_aws
get_igenome_aws "${REFERENCE_GENOME}"

# Make a copy of the bds.config in the $JOB_PATH, possibly modified for SLURM
setup_bds_config

####
#### Stage input data ###
####

if [ "${JOB_INPUT_STAGED}" == "no" ]; then

    send_event "INPUT_DATA_DOWNLOAD_STARTED"

    readonly PARALLEL_DOWNLOADS=4
    # one URL per line
    readonly urls=$(get_input_data_urls)

    if [ "${USE_DOWNLOAD_CACHE}" == "yes" ]; then
        # This simple download cache downloads all files into a cache directory
        # at a path that matches the URL. We then symlink to those files.
        # Most suitable to public database files (eg ENA/SRA).
        # NOTE: The current implementation probably has bugs/corner cases for exotic URLs
        # (eg creating paths based on the URL may be buggy - slash/ , colon: seem fine,
        #  not sure if shell escaping is right for ?@# etc)
        #
        # TODO: Split the URL list into two lists - cache only the simple URLs
        #   - one for URLs without special characters ?&#;:@
        #   - one for 'simple' URLs (the rest)

        # We can grep the download log for retrieved files like:
        # $ grep -E " =>" ${JOB_PATH}/output/download.log  | cut -d "‘" -f 2 | sed s/’//

        mkdir -p "${DOWNLOAD_CACHE_PATH}"
        parallel --no-notice --line-buffer -j ${PARALLEL_DOWNLOADS} --halt now,fail=1 \
          "wget -x -v --continue --trust-server-names --retry-connrefused --read-timeout=60 \
               --waitretry 60 --timeout=30 --tries 8 \
               --append-output output/download.log --directory-prefix ${DOWNLOAD_CACHE_PATH}/ {}" <<< """${urls}"""
               # && ln -s ${DOWNLOAD_CACHE_PATH}/{} input/" <<< """${urls}"""

        # Grab the the absolute paths to downloaded files from the download.log, symlink to {job_path}/input
        # shellcheck disable=SC1112
        readonly downloaded_files="$(grep -E '’ saved \[' "${JOB_PATH}"/output/download.log | sed 's/[‘’]//g' | cut -d ' ' -f 6)"
        for f in ${downloaded_files}; do
            ln -s "${f}" input/
        done
    else
        parallel --no-notice --line-buffer -j ${PARALLEL_DOWNLOADS} --halt now,fail=1 \
          "wget -v --continue --trust-server-names --retry-connrefused --read-timeout=60 \
               --waitretry 60 --timeout=30 --tries 8 \
               --append-output output/download.log --directory-prefix input/ {}" <<< """${urls}"""
    fi

    send_event "INPUT_DATA_DOWNLOAD_FINISHED"

fi

cd output

env >job_env.out

####
#### Job happens in here
####

GENOME_FASTA="${REFERENCE_BASE}/${REFERENCE_GENOME}/Sequence/WholeGenomeFasta/genome.fa"
GENOME_GTF="${REFERENCE_BASE}/${REFERENCE_GENOME}/Annotation/Genes/genes.gtf"

send_event "JOB_PIPELINE_STARTING"

# Don't exit on error, since we want to capture exit code and do an HTTP
# request with curl upon failure
set +o errexit

${PREFIX_JOB_CMD} \
   RNAsik -align star \
       -fastaRef ${GENOME_FASTA} \
       -fqDir ../input \
       -counts \
       -gtfFile ${GENOME_GTF} \
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
if [ ${EXIT_CODE} -ne 0 ]; then
  send_event "JOB_PIPELINE_FAILED" '{"exit_code":'${EXIT_CODE}'}'
else
  send_event "JOB_PIPELINE_COMPLETED" '{"exit_code":'${EXIT_CODE}'}'
fi


cd ${JOB_PATH}
register_files

####
#### Notify service we are done
####

# Authorization header is stored in a file so it doesn't
# leak in 'ps' etc.

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
     "${JOB_COMPLETE_CALLBACK_URL}"

# Extra security: Remove the access token now that we don't need it anymore
if [ ${DEBUG} != "yes" ]; then
  rm ../.private_request_headers
fi
