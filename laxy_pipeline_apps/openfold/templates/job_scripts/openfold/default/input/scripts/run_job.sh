#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o xtrace

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

readonly PIPELINE_NAME='openfold'
# These variables are set via templating when the script file is created
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
readonly CONTAINER_IMAGE="pansapiens/openfold:${PIPELINE_VERSION}"
# Global variables used throughout the script
readonly TMP="${JOB_PATH}/../../tmp"
readonly JOB_PATH=${PWD}
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly SITE_CONFIGS="${JOB_PATH}/../../config"
readonly INPUT_PATH="${JOB_PATH}/input"
readonly OUTPUT_PATH="${JOB_PATH}/output"
readonly INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
readonly INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
readonly PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
readonly DOWNLOAD_CACHE_PATH="${JOB_PATH}/../../cache/downloads"

readonly PIPELINES_CACHE_PATH="${JOB_PATH}/../../cache/pipelines"
readonly SINGULARITY_CACHEDIR="${JOB_PATH}/../../cache/singularity"
readonly SINGULARITY_TMPDIR="${TMP}"
readonly SINGULARITY_OPTS="--bind /mnt/reference/alphafold"
readonly ALPHAFOLD_PARAMS_PATH="$(realpath ${JOB_PATH}/../../cache/alphafold)"
readonly OPENFOLD_PARAMS_PATH="$(realpath ${JOB_PATH}/../../cache/openfold)"

readonly AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
readonly IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"
readonly LAXYDL_BRANCH=master
readonly LAXYDL_USE_ARIA2C=yes
readonly LAXYDL_PARALLEL_DOWNLOADS=8

# These are applied via chmod to all files and directories in the run, upon completion
readonly JOB_FILE_PERMS='ug+rw-s,o='
readonly JOB_DIR_PERMS='ug+rwx-s,o='

export SLURM_EXTRA_ARGS="{{ SLURM_EXTRA_ARGS|default:"" }}"

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

send_event "JOB_INFO" "Running using laxy_pipeline_apps.openfold"

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

if [[ ! -f "${AUTH_HEADER_FILE}" ]]; then
    echo "No auth token file (${AUTH_HEADER_FILE}) - exiting."
    exit 1
fi

# For QUEUE_TYPE=='local'
PREFIX_JOB_CMD="/usr/bin/env bash -l -c "

function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    add_to_manifest "${INPUT_PATH}/fasta/*.fasta" "fasta"
    add_to_manifest "${OUTPUT_PATH}/predictions/*.pdb" "pdb,structure"

    curl -X POST \
      ${CURL_INSECURE} \
     -H "Content-Type: text/csv" \
     -H @"${AUTH_HEADER_FILE}" \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 600 \
     --retry 8 \
     --retry-max-time 600 \
     --data-binary @"${JOB_PATH}/manifest.csv" \
     "${JOB_FILE_REGISTRATION_URL}"
}

update_permissions || true

mkdir -p "${TMP}"
mkdir -p ${INPUT_PATH}
mkdir -p ${OUTPUT_PATH}

mkdir -p "${INPUT_CONFIG_PATH}" "${INPUT_SCRIPTS_PATH}"

####
#### Setup and import a Conda environment
####

install_miniconda || fail_job 'install_miniconda' '' $?

# We primarily use this conda env for jq and curl
init_conda_env "${PIPELINE_NAME}" "${PIPELINE_VERSION}" || fail_job 'init_conda_env' '' $?

####
#### Pull container
####

# TODO: This should be part of a ComputeResource specific pre-amble
module load singularity/3.9.2 || true

# Takes:   ghcr.io/pansapiens/openfold:42e71db
# Returns: openfold_42e71db.sif
#
CONTAINER_FILENAME=$(python -c '\
import sys; \
from pathlib import Path; \
from urllib.parse import urlparse; \
print(Path(urlparse(sys.argv[1]).path).name.replace(":","_") + ".sif")' ${CONTAINER_IMAGE})

#CONTAINER_FILENAME="openfold-multimer_260db67.sif"
#CONTAINER_FILENAME="openfold_42e71db.sif"

send_event "JOB_INFO" "Getting/finding Singularity container image (${CONTAINER_IMAGE})"

SINGULARITY_PULL_EXIT_CODE=0
if [[ ! -f "${SINGULARITY_CACHEDIR}/${CONTAINER_FILENAME}" ]]; then
    singularity pull ${SINGULARITY_CACHEDIR}/${CONTAINER_FILENAME} docker://${CONTAINER_IMAGE}
    SINGULARITY_PULL_EXIT_CODE=$?
fi

if [[ ${SINGULARITY_PULL_EXIT_CODE} != 0 ]]; then
    send_event "JOB_ERROR" "Failed to get/find Singularity container." '{"exit_code": "${SINGULARITY_PULL_EXIT_CODE}"}'
fi

# update_laxydl || send_error 'update_laxydl' '' $?

####
#### Download model parameters, if required
####

# TODO: This doesn't work in vanilla openfold (42e71db) container or openfold-multimer (260db67) container.
#       The container is missing the `aws` commandline tool, multimer container is also missing the 
#       `download_openfold_params.sh` script. We could copy (cat) the download scripts out of the
#       containers and use `awscli` installed in conda ... but given the size of the downloads
#       it might make more sense for these to be pre-cached on ComputeResources.
#
function download_databases() {
    singularity run ${SINGULARITY_CACHEDIR}/${CONTAINER_FILENAME} \
      /opt/openfold/scripts/download_alphafold_dbs.sh \
      ${ALPHAFOLD_PARAMS_PATH}
    singularity run ${SINGULARITY_CACHEDIR}/${CONTAINER_FILENAME} \
      /opt/openfold/scripts/download_openfold_params.sh \
      ${OPENFOLD_PARAMS_PATH}
}

#download_databases || true

# Since the Alphafold database is large, we don't download this on demand by default.
# Instead, it should be downloaded manually in advance to the ComputeResource(s).
# We check if the appropriate directories exist and fail if they don't

if [[ ! -e "${ALPHAFOLD_PARAMS_PATH}" ]]; then
    send_event "JOB_ERROR" "Alphafold database and model parameters are missing. \
Please ask your Laxy administrator to install them at \
the appropriate path ($(realpath ${ALPHAFOLD_PARAMS_PATH})) on the ComputeResource." '{"exit_code":'1'}'
fi

if [[ ! -e "${OPENFOLD_PARAMS_PATH}" ]]; then
    send_event "JOB_ERROR" "Openfold model parameters are missing. \
Please ask your Laxy administrator to install them at \
the appropriate path ($(realpath ${OPENFOLD_PARAMS_PATH})) on the ComputeResource." '{"exit_code":'1'}'
fi

####
#### Stage input data ###
####

# TODO: Use conda instead ?
#curl -L "https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64" ${SINGULARITY_CACHEDIR}/jq
#chmod +x ${SINGULARITY_CACHEDIR}/jq

#if  [[ ! -f ${SINGULARITY_CACHEDIR}/jq.sif ]]; then
#    singularity pull ${SINGULARITY_CACHEDIR}/jq.sif docker://stedolan/jq
#fi
# JQ="singularity exec -B $(realpath ${JOB_PATH}) ${SINGULARITY_CACHEDIR}/jq.sif jq "

mkdir -p ${INPUT_PATH}/fasta
jq --raw-output '.params.openfold.input.fasta' "$(realpath ${PIPELINE_CONFIG})" \
   >${INPUT_PATH}/fasta/sequences.fasta

if [[ $(stat -c %s ${INPUT_PATH}/fasta/sequences.fasta) == 0 ]]; then
   send_event "JOB_ERROR" "Empty FASTA sequence ?!?" '{"exit_code":'1'}'
fi

PEPTIDE_LENGTH_ESTIMATE=$(wc -c "${INPUT_PATH}/fasta/sequences.fasta" | cut -f 1 -d ' ')

# Fine for smaller proteins (M3/MASSIVE specific)
# TODO: Make configurable for other HPC sites
MEM=64G
GPU_PARTITION_OPTS="--partition=m3g,gpu --gres=gpu:1"
CPUS=8

if [[ ${PEPTIDE_LENGTH_ESTIMATE} -gt 1000 ]]; then
    # For larger multimer (~3000+ residues ?) (M3/MASSIVE specific)
    # TODO: Make configurable for other HPC sites
    MEM=128G
    GPU_PARTITION_OPTS="--partition=gpu --gres=gpu:A40:1"
fi

####
# Some notes specific to the MASSIVE M3 cluster
# These may help in chossing GPU resources required at other HPC sites.
##

# Any gpu partition - fine for small proteins where 16G GPU memory is enough
# Here you typically get 16Gb GPU memory - could be P100s, V100s, T4                        
# GPU_PARTITION_OPTS="--partition=m3g,m3h,gpu --gres=gpu:1"

# For 48Gb GPU memory A40s on M3.
# 'relax' for larger (~3000 residue) multimers needs >64Gb (CPU) RAM
# GPU_PARTITION_OPTS="--partition=gpu --gres=gpu:A40:1"

# V100 with 32G GPU memory (requires --gres=gpu:1)
# Not enough for ~3000 residues
# GPU_PARTITION_OPTS="--partition=m3g --gres=gpu:1 --constraint=V100-32G"

# Fails with: RuntimeError: Found no NVIDIA driver on your system. 
#             Please check that you have an NVIDIA GPU and installed a driver
# Seems the V100-16G nodes don't have the right CUDA version ? 
# Might need --gres=gpu:1 ?
# GPU_PARTITION_OPTS="--partition=m3g"

# We use sbatch --wait --wrap rather than srun, since it seems more reliable
# and jobs appear pending on the queue immediately
readonly SLURM_OPTIONS="--parsable \
                        --cpus-per-task=${CPUS} \
                        --mem=${MEM} \
                        ${GPU_PARTITION_OPTS} \
                        --time 7-00:00 \
                        --ntasks-per-node=1 \
                        --ntasks=1 \
                        ${SLURM_EXTRA_ARGS} \
                        --job-name=laxy:${JOB_ID}"
#
####

if [[ "${QUEUE_TYPE}" == "slurm" ]]; then
    PREFIX_JOB_CMD="sbatch ${SLURM_OPTIONS} --wait --wrap "
fi

if [[ "${QUEUE_TYPE}" == "local" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

send_event "JOB_INFO" "Sanity checking FASTA sequences."

seqkit stats ${INPUT_PATH}/fasta/sequences.fasta \
   >${JOB_PATH}/output/seqkit_stats.tsv \
   2>${JOB_PATH}/output/seqkit_stats.err

SEQKIT_STATS_EXIT_CODE=$?

if [[ ${SEQKIT_STATS_EXIT_CODE} != 0 ]]; then
    send_event "JOB_ERROR" "Invalid FASTA sequence ?!?" '{"exit_code": "${SEQKIT_STATS_EXIT_CODE}"}'
fi

cp -f "${ALPHAFOLD_PARAMS_PATH}/alphafold_Terms_of_Use.txt" "${OUTPUT_PATH}/" || true

capture_environment_variables || true

cd "${OUTPUT_PATH}"

####
#### Job happens in here
####

send_event "JOB_PIPELINE_STARTING" "Pipeline starting."

send_event "JOB_INFO" "Starting pipeline."

# EXIT_CODE=99

export OPENMM_CPU_THREADS=${CPUS}
export NVIDIA_VISIBLE_DEVICES=all

OPENFOLD_CMD="python3 /opt/openfold/run_pretrained_openfold.py \
    --output_dir=$(realpath ${OUTPUT_PATH}) \
    --config_preset "model_1_ptm" \
    --model_device "cuda:0" \
    --cpus=${CPUS} \
    --openfold_checkpoint_path $(realpath ${OPENFOLD_PARAMS_PATH}/finetuning_ptm_2.pt) \
    --preset=full_dbs \
    --max_template_date=2023-01-01 \
    --uniref90_database_path=${ALPHAFOLD_PARAMS_PATH}/uniref90/uniref90.fasta \
    --mgnify_database_path=${ALPHAFOLD_PARAMS_PATH}/mgnify/mgy_clusters_2018_12.fa \
    --obsolete_pdbs_path=${ALPHAFOLD_PARAMS_PATH}/pdb_mmcif/obsolete.dat \
    --bfd_database_path=${ALPHAFOLD_PARAMS_PATH}/bfd/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt \
    --uniclust30_database_path=${ALPHAFOLD_PARAMS_PATH}/uniclust30/uniclust30_2018_08/uniclust30_2018_08 \
    --pdb70_database_path=${ALPHAFOLD_PARAMS_PATH}/pdb70/pdb70 \
    --jackhmmer_binary_path=/opt/conda/bin/jackhmmer \
    --hhblits_binary_path=/opt/conda/bin/hhblits \
    --hhsearch_binary_path=/opt/conda/bin/hhsearch \
    --kalign_binary_path=/opt/conda/bin/kalign \
    $(realpath ${INPUT_PATH}/fasta) ${ALPHAFOLD_PARAMS_PATH}/pdb_mmcif/mmcif_files"


${PREFIX_JOB_CMD} "singularity exec --nv \
                    ${SINGULARITY_OPTS} \
                    --bind $(realpath $PWD) \
                    --bind $(realpath $INPUT_PATH) \
                    --bind $(realpath $OUTPUT_PATH) \
                    --bind ${ALPHAFOLD_PARAMS_PATH} \
                    --bind ${OPENFOLD_PARAMS_PATH} \
                    ${SINGULARITY_CACHEDIR}/${CONTAINER_FILENAME} \
                    ${OPENFOLD_CMD} \
                    >${JOB_PATH}/output/openfold.out \
                    2>${JOB_PATH}/output/openfold.err" \
    >>"${JOB_PATH}/slurm.jids" 2>"${JOB_PATH}/output/slurm.err"

# Check if any of the recorded job IDs were cancelled due to TIMEOUT
if [[ "${QUEUE_TYPE}" == "slurm" ]]; then
    for j in $(cat slurm.jids); do 
        if [[ $(sacct -X -n -o State -j "$j") == *"TIMEOUT"* ]]; then 
            EXIT_CODE=140
        fi
    done
fi

# Call job finalization with explicit exit code from the main pipeline command
job_done "${EXIT_CODE}"

# Remove the trap so job_done doesn't get called a second time when the script naturally exits
trap - EXIT
exit 0
