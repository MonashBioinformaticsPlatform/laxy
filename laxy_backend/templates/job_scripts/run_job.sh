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
readonly PIPELINE_CONFIG="${JOB_PATH}/input/pipeline_config.json"
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly REFERENCE_BASE="${PWD}/../references/iGenomes"
readonly DOWNLOAD_CACHE_PATH="${PWD}/../cache"

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

    # MEM=64000  # defaults for Human, Mouse
    MEM=40000  # defaults for Human, Mouse
    # M3 (typically 24 core nodes)
    # CPUS=12
    # laxy-compute-01 - 16 cores
    CPUS=16
    # TODO: We also need to set this in a custom sik.config so that BDS tasks don't exceed the memory budget SLURM
#    if [[ "$REFERENCE_GENOME" == "Saccharomyces_cerevisiae/Ensembl/R64-1-1" ]]; then
#        MEM=16000 # yeast (uses ~ 8Gb)
#        CPUS=8
#    fi
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

function add_sik_config() {
   # Find that ComputeResource specific sik.config, and if there is none, use the default.
   # Always copy it to the job input directory so preserve it.
    SIK_CONFIG="${JOB_PATH}/../sik.config"
    if [ ! -f "${SIK_CONFIG}" ]; then
        SIK_CONFIG="$(dirname RNAsik)/../opt/rnasik-${PIPELINE_VERSION}/configs/sik.config"
    fi
    cp -n "${SIK_CONFIG}" "${JOB_PATH}/input/sik.config"
}

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
        ${CONDA_BASE}/bin/conda install --yes -n "${env_name}" curl aria2 parallel jq awscli
        ${CONDA_BASE}/bin/pip install oneliner

        pip install --process-dependency-links -e git+https://github.com/MonashBioinformaticsPlatform/laxy#egg=laxy_downloader&subdirectory=laxy_downloader

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

    ${CONDA_BASE}/bin/conda env export >"${JOB_PATH}/input/conda_environment.yml"

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
    BDS_CONFIG="${JOB_PATH}/input/bds.config"
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

function add_sik_config() {
   # Find that ComputeResource specific sik.config, and if there is none, use the default.
   # Always copy it to the job input directory so preserve it.
    SIK_CONFIG="${JOB_PATH}/../sik.config"
    if [ ! -f "${SIK_CONFIG}" ]; then
        SIK_CONFIG="$(dirname RNAsik)/../opt/rnasik-${PIPELINE_VERSION}/configs/sik.config"
    fi
    cp -n "${SIK_CONFIG}" "${JOB_PATH}/input/sik.config"
}

function get_input_data_urls() {
    # Output is one URL one per line
    local urls
    urls=$(jq '.sample_set.samples[].files[][]' <${PIPELINE_CONFIG} | sed s'/"//g')
    echo "${urls}"
}

function detect_pairs() {
    PAIRIDS=""
    EXTN=".fastq.gz"
    if stat -t "${JOB_PATH}/input/*_R2_001.fastq.gz" >/dev/null 2>&1; then
      EXTN="_001.fastq.gz"
      PAIRIDS="_R1,_R2"
    elif stat -t "${JOB_PATH}input/*_R2.fastq.gz" >/dev/null 2>&1; then
      EXTN=".fastq.gz"
      PAIRIDS="_R1,_R2"
    elif stat -t "${JOB_PATH}input/*_2.fastq.gz" >/dev/null 2>&1; then
      EXTN=".fastq.gz"
      PAIRIDS="_1,_2"
    # Very occasionally, we get FASTA format reads
    elif stat -t "${JOB_PATH}input/*_R2.fasta.gz" >/dev/null 2>&1; then
      EXTN=".fasta.gz"
      PAIRIDS="_R1,_R2"
    elif stat -t "${JOB_PATH}input/*_2.fasta.gz" >/dev/null 2>&1; then
      EXTN=".fasta.gz"
      PAIRIDS="_1,_2"
    fi
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

# Make a copy of the sik.config into $JOB_PATH/input/sik.config
add_sik_config

####
#### Stage input data ###
####

if [ "${JOB_INPUT_STAGED}" == "no" ]; then

    send_event "INPUT_DATA_DOWNLOAD_STARTED"

    readonly PARALLEL_DOWNLOADS=8
    # one URL per line
    readonly urls=$(get_input_data_urls)

    mkdir -p "${JOB_PATH}/../cache"
    laxydl --no-progress \
           --untar \
           --parallel-downloads "${PARALLEL_DOWNLOADS}" \
           --cache-path "${DOWNLOAD_CACHE_PATH}" \
           --pipeline-config "${JOB_PATH}/input/pipeline_config.json" \
           --destination-path "${JOB_PATH}/input"

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

# quick and dirty detection of paired-end or not
PAIRIDS=""
EXTN=".fastq.gz"
detect_pairs

if [[ ! -z "PAIRIDS" ]]; then
    ${PREFIX_JOB_CMD} \
       RNAsik \
           -configFile ${JOB_PATH}/input/sik.config \
           -align star \
           -fastaRef ${GENOME_FASTA} \
           -fqDir ../input \
           -counts \
           -gtfFile ${GENOME_GTF} \
           -all \
           -extn ${EXTN} \
           >>job.out 2>>job.err
else
    ${PREFIX_JOB_CMD} \
       RNAsik \
           -configFile ${JOB_PATH}/input/sik.config \
           -align star \
           -fastaRef ${GENOME_FASTA} \
           -fqDir ../input \
           -counts \
           -gtfFile ${GENOME_GTF} \
           -all \
           -paired \
           -extn ${EXTN} \
           -pairIds ${PAIRIDS} \
           >>job.out 2>>job.err
fi

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
