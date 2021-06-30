#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o xtrace

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

export PIPELINE_NAME='nf-core-rnaseq'
export NFCORE_PIPELINE_RELEASE='3.2'
export NFCORE_PIPELINE_NAME="rnaseq"
# These variables are set via templating when the script file is created
export JOB_ID="{{ JOB_ID }}"
export JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
export JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
export JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
export JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
export PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
export REFERENCE_GENOME_ID="{{ REFERENCE_GENOME }}"

# Global variables used throughout the script
export JOB_PATH="${PWD}"
export TMP="${JOB_PATH}/../../tmp"
export INPUT_READS_PATH="${JOB_PATH}/input/reads"
export INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
export INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
export INPUT_REFERENCE_PATH="${JOB_PATH}/input/reference"
export PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
export SITE_CONFIGS="${JOB_PATH}/../../config"
export CONDA_BASE="${JOB_PATH}/../miniconda3"
export DOWNLOAD_CACHE_PATH="${JOB_PATH}/../../cache/downloads"
export SINGULARITY_CACHEDIR="${JOB_PATH}/../../cache/singularity"
export PIPELINES_CACHE_PATH="${JOB_PATH}/../../cache/pipelines"
export SINGULARITY_TMPDIR="${TMP}"
export AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
export IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"
export LAXYDL_BRANCH=master
export LAXYDL_USE_ARIA2C=yes
export LAXYDL_PARALLEL_DOWNLOADS=8

# These are applied via chmod to all files and directories in the run, upon completion
export JOB_FILE_PERMS='ug+rw-s,o='
export JOB_DIR_PERMS='ug+rwx-s,o='

# Nextflow specific environment variables
export NXF_TEMP=${TMP}
export NXF_SINGULARITY_CACHEDIR="${SINGULARITY_CACHEDIR}"
export NXF_OPTS='-Xms1g -Xmx7g'
export NXF_ANSI_LOG='false'
# export NXF_VER=21.04.0
# export NXF_DEBUG=1  # 2 # 3

# shellcheck disable=SC1054,SC1083,SC1009
{% if SLURM_EXTRA_ARGS %}
export SLURM_EXTRA_ARGS="{{ SLURM_EXTRA_ARGS }}"
# shellcheck disable=SC1073
{% endif %}

export QUEUE_TYPE="{{ QUEUE_TYPE }}"
# export QUEUE_TYPE="local"

if [[ ${IGNORE_SELF_SIGNED_CERTIFICATE} == "yes" ]]; then
    export CURL_INSECURE="--insecure"
    export LAXYDL_INSECURE="--ignore-self-signed-ssl-certificate"
else
    export CURL_INSECURE=""
    export LAXYDL_INSECURE=""
fi

##
# Setup environment variables and load the laxy bash helper functions.
##

# TODO: Fix templating so env.sh gets populated by Jinja2, move env vars to above (except DEBUG) to env.sh
# source "${INPUT_SCRIPTS_PATH}/env.sh" || exit 1

source "${INPUT_SCRIPTS_PATH}/laxy.lib.sh" || exit 1

send_event "JOB_INFO" "Getting ready to run nf-core/rnaseq"

# We exit on any uncaught error signal. The 'trap finalize_job EXIT' 
# below sends a job fail HTTP request and cleans up when an error 
# signal is raised. For this reason, it's important to catch any exit
# signals from commands that are 'optional' but might fail, eg like: some_command || true
set -o errexit

function job_done() {
    local _exit_code=${1:-$?}
    
    # Use the EXIT_CODE global if set
    # [[ -n ${EXIT_CODE} ]] || _exit_code=${EXIT_CODE}

    cd "${JOB_PATH}"
    register_files || true
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
MEM=8000 
CPUS=1

# We use sbatch --wait --wrap rather than srun, since it seems more reliable
# and jobs appear pending on the queue immediately
export SLURM_OPTIONS="--parsable \
                        --cpus-per-task=${CPUS} \
                        --mem=${MEM} \
                        -t 3-0:00 \
                        --ntasks-per-node=1 \
                        --ntasks=1 \
                        {% if SLURM_EXTRA_ARGS %}
                        ${SLURM_EXTRA_ARGS} \
                        {% endif %}
                        --job-name=laxy:${JOB_ID}"


if [[ "${QUEUE_TYPE}" == "slurm" ]] || [[ "${QUEUE_TYPE}" == "slurm-hybrid" ]]; then
    PREFIX_JOB_CMD="sbatch ${SLURM_OPTIONS} --wait --wrap "
fi

if [[ "${QUEUE_TYPE}" == "local" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    add_to_manifest "*.fq" "fastq"
    add_to_manifest "*.fastq" "fastq"
    add_to_manifest "*.fq.gz" "fastq"
    add_to_manifest "*.fastq.gz" "fastq"
    add_to_manifest "*.bam" "bam,alignment"
    add_to_manifest "*.bai" "bai"
    add_to_manifest "output/*.tsv" "tsv,report"
    add_to_manifest "**/multiqc_report.html" "report,html,multiqc"
    add_to_manifest "**/*_fastqc.html" "report,html,fastqc"
    add_to_manifest "**/salmon.merged.gene_counts.tsv" "counts,degust"

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

function set_genome_args() {
    # See if we can find a custom reference in the fetch_files list
    local _fasta_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_sequence") | .name' "${PIPELINE_CONFIG}" || echo '')
    local _annot_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_annotation") | .name' "${PIPELINE_CONFIG}" || echo '')

    [[ -z ${_fasta_fn} ]] || GENOME_FASTA="${INPUT_REFERENCE_PATH}/${_fasta_fn}"
    [[ -z ${_annot_fn} ]] || ANNOTATION_FILE="${INPUT_REFERENCE_PATH}/${_annot_fn}"

    # If there is no custom genome, then we assume we are using a pre-defined references
    if [[ -z ${_fasta_fn} ]] && [[ -z ${_annot_fn} ]]; then
        # The last part of the iGenomes-style ID is the ID used by nf-core,
        # eg Homo_sapiens/Ensembl/GRCh38 -> GRCh38
        export NFCORE_GENOME_ID="$(echo ${REFERENCE_GENOME_ID} | cut -f 3 -d '/')"
        export GENOME_ARGS=" --genome ${NFCORE_GENOME_ID} "
    else
        GENOME_ARGS=" --fasta ${GENOME_FASTA} "
        
        if [[ ${_annot_fn} == *.gtf ]] || [[ ${_annot_fn} == *.gtf.gz ]]; then
            export GENOME_ARGS=" ${GENOME_ARGS} --gtf ${ANNOTATION_FILE} "
        elif [[ ${_annot_fn} == *.gff ]] || [[ ${_annot_fn} == *.gff.gz ]]; then
            export GENOME_ARGS=" ${GENOME_ARGS} --gff ${ANNOTATION_FILE} "
        else
            send_event "JOB_INFO" "This isn't going so well. Unable to detemine type of annotation file."
            send_job_finished 1
            exit 1
        fi
    fi
}

function find_strandedness() {
    # UPDATE: Looks like nf-core/rnaseq (3.2) now does this, but only for salmon (not star_salmon)
    #         https://github.com/nf-core/rnaseq/issues/637
    # use: --salmon_quant_libtype A

    # TODO: This could come from https://github.com/betsig/how_are_we_stranded_here, or similar
    # eg:
    # check_strandedness --gtf Yeast.gtf --transcripts Yeast_cdna.fasta --reads_1 Sample_A_1.fq.gz --reads_2 Sample_A_2.fq.gz

    # An alternative would be to run something like:
    #
    # gffread -w transcripts.fa -g genome.fa genes.gtf
    # 
    # salmon index -t transcripts.fa -i transcripts_index --decoys decoys.txt -k 31
    # salmon quant --writeMappings | samtools >outpath/pseudoalignments.bam
    # _or_
    # kallisto index -i kindex transcripts.fa
    # kallisto quant -i kindex -o outpath --genomebam --gtf genes.gtf sample_R1.fastq.gz sample_R2.fastq.gz
    #
    # to generate pseudoaligments and then call rseqc:
    # gtf2bed genes.gtf genes.bed
    # n_reads = 200000
    # infer_experiment.py -r genes.bed -s ${n_reads} -i outpath/pseudoalignments.bam

    # It would be nice to launch this as the actual nf-core/rnaseq salmon quant task (pre-pipeline) so the result gets
    # cached in work/ prior to the full pipeline run, but unfortunately it looks like the `salmon quant` calls
    # by nf-core/rnaseq don't use --writeMappings (by default)

    #export STRANDEDNESS='unstranded'
    #export STRANDEDNESS='forward'
    #export STRANDEDNESS='reverse'
    export STRANDEDNESS=$(jq --raw-output '.params."nf-core-rnaseq".strandedness' "${PIPELINE_CONFIG}" || echo "unstranded")
    # return $STRANDEDNESS
}

function generate_samplesheet() {

    export STRANDEDNESS='unstranded'
    find_strandedness || true

    python ${INPUT_SCRIPTS_PATH}/laxy2nfcore_samplesheet.py  \
      ${INPUT_CONFIG_PATH}/pipeline_config.json ${INPUT_READS_PATH} ${STRANDEDNESS} \
      >${INPUT_CONFIG_PATH}/samplesheet.csv
}

function cleanup_nextflow_intermediates() {
    if [[ ${DEBUG} != "yes" ]]; then
      rm -rf "${JOB_PATH}/output/work"
      rm -rf "${JOB_PATH}/output/.nextflow"
    fi
}

function get_site_nextflow_config() {
    export NEXTFLOW_CONFIG_ARG=""
    readonly NEXTFLOW_DEFAULT_SITE_CONFIG="${SITE_CONFIGS}/nextflow.config"
    readonly NEXTFLOW_PIPELINE_SITE_CONFIG="${SITE_CONFIGS}/${PIPELINE_NAME}/nextflow.config"

    if [[ -f "${NEXTFLOW_DEFAULT_SITE_CONFIG}" ]]; then
        cp "${NEXTFLOW_DEFAULT_SITE_CONFIG}" "${INPUT_CONFIG_PATH}/nextflow.config"
        export NEXTFLOW_CONFIG_ARG=" -c ${INPUT_CONFIG_PATH}/nextflow.config"
    fi
    if [[ -f "${NEXTFLOW_PIPELINE_SITE_CONFIG}" ]]; then
        cp "${NEXTFLOW_PIPELINE_SITE_CONFIG}" "${INPUT_CONFIG_PATH}/nextflow.config"
        export NEXTFLOW_CONFIG_ARG=" -c ${INPUT_CONFIG_PATH}/nextflow.config"
    fi
}

function nextflow_self_update() {
    nextflow -self-update
}

function cache_pipeline() {
    # Use the nf-core tool to pre-cache a release of the pipeline, and all singularity containers.
    # We make a copy of the pipeline code into our job to preserve it.
    mkdir -p "${PIPELINES_CACHE_PATH}"
    export CACHED_PIPELINE_PATH=$(realpath "${PIPELINES_CACHE_PATH}/nf-core-${NFCORE_PIPELINE_NAME}-${NFCORE_PIPELINE_RELEASE}")

    if [[ ! -d "${CACHED_PIPELINE_PATH}" ]]; then
        nf-core download ${NFCORE_PIPELINE_NAME} \
                        --release "${NFCORE_PIPELINE_RELEASE}" \
                        --container singularity \
                        --singularity-cache-only \
                        --parallel-downloads ${LAXYDL_PARALLEL_DOWNLOADS} \
                        --compress none \
                        --outdir "${CACHED_PIPELINE_PATH}"
    fi

    mkdir -p "${JOB_PATH}/input/pipeline"
    cp -r "${CACHED_PIPELINE_PATH}" "${JOB_PATH}/input/pipeline/"
    export NFCORE_PIPELINE_PATH=$(realpath "${JOB_PATH}/input/pipeline/nf-core-${NFCORE_PIPELINE_NAME}-${NFCORE_PIPELINE_RELEASE}/workflow")
}

function run_nextflow() {
    cd "${JOB_PATH}/output"

    module load singularity/3.7.1 || true

    # TODO: Valid genome IDs from:
    # https://github.com/nf-core/rnaseq/blob/master/conf/igenomes.config

    # export NFCORE_GENOME_ID="R64-1-1"   # yeast
    # export NFCORE_GENOME_ID="GRCm38"    # mouse
    # export NFCORE_GENOME_ID="GRCh38"    # hoomn
    # export NFCORE_GENOME_ID="$(echo ${REFERENCE_GENOME_ID} | cut -f 3 -d '/')"
    
    set_genome_args

    # export NFCORE_PIPELINE_PATH="nf-core/rnaseq"  # download, don't use pre-cached version

    #set +o errexit
    #${PREFIX_JOB_CMD} "\
    nextflow run "${NFCORE_PIPELINE_PATH}" \
       --input "${INPUT_CONFIG_PATH}/samplesheet.csv" \
        ${GENOME_ARGS} \
       --aligner star_salmon \
       --pseudo_aligner salmon \
       -profile singularity \
        ${NEXTFLOW_CONFIG_ARG} \
       -resume
        >${JOB_PATH}/output/nextflow.log \
        2>${JOB_PATH}/output/nextflow.err
    #">>"${JOB_PATH}/slurm.jids"
    #   --salmon_quant_libtype A \

    EXIT_CODE=$?
    #set -o errexit

       #-with-tower

    cleanup_nextflow_intermediates || true
}

# Extract the pipeline parameter nf-core-rnaseq.flags.all from the pipeline_config.json
# Set the --all flag appropriately.
#_flags_all=$(jq --raw-output '.params.nf-core-rnaseq.flags.all' "${PIPELINE_CONFIG}" || echo "false")
#ALL_FLAG=" "
#if [[ "${_flags_all}" == "true" ]]; then
#    ALL_FLAG=" --all "
#fi

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

# nextflow_self_update || true

update_laxydl || send_error 'update_laxydl' '' $?

####
#### Stage input data ###
####

download_input_data || fail_job 'download_input_data' '' $?

generate_samplesheet

get_site_nextflow_config || true

cache_pipeline

cd "${JOB_PATH}/output"

send_event "JOB_PIPELINE_STARTING" "Pipeline starting."

send_event "JOB_INFO" "Starting pipeline."

run_nextflow

capture_environment_variables || true

cd "${JOB_PATH}"
register_files || true

# Call job finalization with explicit exit code from the main pipeline command
job_done $EXIT_CODE

# Remove the trap so job_done doesn't get called a second time when the script naturally exits
trap - EXIT
exit 0

#}}