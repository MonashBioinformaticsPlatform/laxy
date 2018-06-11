#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-no}"
# export JOB_ID="${JOB_ID:-}"
# export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"
# export JOB_COMPLETE_AUTH_HEADER="${JOB_COMPLETE_AUTH_HEADER:-}"

readonly TMP="${PWD}/../tmp"
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly REFERENCE_GENOME="{{ REFERENCE_GENOME }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
readonly JOB_PATH=${PWD}
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly REFERENCE_BASE="${PWD}/../references/iGenomes"

readonly SCHEDULER="slurm"
# readonly SCHEDULER="local"
readonly SBATCH_OPTIONS="--cpus-per-task=8 --mem=31500 -t 7-0:00 --ntasks-per-node=1 --ntasks=1 --job-name=laxy:${JOB_ID}"

PREFIX_JOB_CMD=""
if [ "${SCHEDULER}" == "slurm" ]; then
    PREFIX_JOB_CMD="srun ${SBATCH_OPTIONS} "
fi

function send_event() {
    event=${1:-"HEARTBEAT"}
    extra=${2:-"{}"}
    # escape double quotes since this is JSON nested inside JSON ?
    # extra=$(sed 's/"/\\"/g' <<< "${extra}")

    # || true so we don't stop on errors irrespective of set -o errexit state,
    # so if a curl call fails we don't bring down the whole script
    # NOTE: curl v7.55+ is required to use -H @filename

    VERBOSITY="--silent"
    if [ ${DEBUG} == "yes" ]; then
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
         ""${JOB_EVENT_URL}"" || true
}

function install_miniconda() {
    if [ ! -d "${CONDA_BASE}" ]; then
         wget --directory-prefix "${TMP}" -c "https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh"
         chmod +x "${TMP}"/Miniconda3-latest-Linux-x86_64.sh
         "${TMP}"/Miniconda3-latest-Linux-x86_64.sh -b -p "${CONDA_BASE}"
    fi
}

function init_conda_env() {
    env_name="${1}-${PIPELINE_VERSION}"

    if [ ! -d "${CONDA_BASE}/envs/${env_name}" ]; then

        # Conda activate misbehaves if nounset and errexit are set
        # https://github.com/conda/conda/issues/3200
        set +o nounset
        # First we update conda itself
        ${CONDA_BASE}/bin/conda update --yes -n base conda

        # Create a base environment
        ${CONDA_BASE}/bin/conda create --yes -m -n "${env_name}"

        # Install an up-to-date curl and GNU parallel
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" \
                     -c serine \
                     -c bioconda \
                     -c conda-forge \
                     curl parallel

        # Then install rnasik
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" \
                     -c serine \
                     -c bioconda \
                     -c conda-forge \
                     rnasik=${PIPELINE_VERSION}

        # Environment takes a very long time to solve if qualimap is included initially
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" \
                     -c serine \
                     -c bioconda \
                     -c conda-forge \
                     qualimap

    fi

    source "${CONDA_BASE}/bin/activate" "${CONDA_BASE}/envs/${env_name}"
    set -o nounset
}


function patch_bds_config_slurm() {
    # Will only work after conda env with bds has been imported
    sed -i 's/#system = "local"/system = "generic"/' $(which bds).config
}

function get_reference_data_aws() {
    # TODO: Be smarter about what we pull in - eg only the reference required,
    #       not the whole lot. Assume reference is present if appropriate
    #       directory is there
    if [ ! -d "${REFERENCE_BASE}" ]; then
        prev="${PWD}"
        mkdir -p "${REFERENCE_BASE}"
        cd "${REFERENCE_BASE}"
        aws s3 cp s3://bioinformatics-au/iGenomes .
        cd "${prev}"
    fi
}

####
#### Pull in reference data from S3
####

# TODO: Detect if we are on AWS and do this conditionally
#       (maybe via ComputeResource metadata passed to task)

get_reference_data_aws

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

####
#### Setup and import a Conda environment
####

install_miniconda

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
