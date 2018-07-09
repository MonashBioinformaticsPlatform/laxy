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

readonly SCHEDULER="slurm"
# readonly SCHEDULER="local"
MEM=64000
CPUS=12
if [[ "$REFERENCE_GENOME" == "Saccharomyces_cerevisiae/Ensembl/R64-1-1" ]]; then
    MEM=16000 # yeast (uses ~ 8Gb)
    CPUS=8
fi
readonly SBATCH_OPTIONS="--cpus-per-task=${CPUS} --mem=${MEM} -t 1-0:00 --ntasks-per-node=1 --ntasks=1 --job-name=laxy:${JOB_ID}"

PREFIX_JOB_CMD=""
if [[ "${SCHEDULER}" == "slurm" ]]; then
    PREFIX_JOB_CMD="srun ${SBATCH_OPTIONS} "
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
    local env_name="${1}-${PIPELINE_VERSION}"

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
                     rnasik=${PIPELINE_VERSION}

        # Environment takes a very long time to solve if qualimap is included initially
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" qualimap
    fi

    # We shouldn't need to do this .. but it seems required for _some_ environments (ie M3)
    export JAVA_HOME="${CONDA_BASE}/envs/${env_name}/jre"

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
        s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/WholeGenomeFasta/${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/

}

function find_filetype() {
    # eg, *.fastq.gz or *.bam
    local pattern=$1
    # eg, fastq,bam,bam.sorted
    local tags=$2
    # checksum,filepath,type_tags
    find . -name "${pattern}" -type f -exec bash -c 'echo -e "md5:$(md5sum {} | sed -e "s/  */,/g"),\"'${tags}'\""' \;
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
     ""${JOB_FILE_REGISTRATION_URL}""
}

function setup_bds_config() {
    BDS_CONFIG="${JOB_PATH}/bds.config"
    cp $(which bds).config ${BDS_CONFIG}

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

####
#### Pull in reference data from S3
####

# TODO: Detect if we are on AWS and do this conditionally
#       (maybe via ComputeResource metadata passed to task)

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

####
#### Setup and import a Conda environment
####

install_miniconda

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "rnasik"

# get_reference_data_aws
get_igenome_aws "${REFERENCE_GENOME}"

# Make a copy of the bds.config in the $JOB_PATH, possibly modified for SLURM
setup_bds_config

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
     ""${JOB_COMPLETE_CALLBACK_URL}""

# Extra security: Remove the access token now that we don't need it anymore
if [ ${DEBUG} != "yes" ]; then
  rm ../.private_request_headers
fi
