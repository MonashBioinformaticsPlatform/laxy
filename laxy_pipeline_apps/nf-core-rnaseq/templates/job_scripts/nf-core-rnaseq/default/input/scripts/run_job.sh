#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o xtrace

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

export PIPELINE_NAME='nf-core-rnaseq'
export NFCORE_PIPELINE_RELEASE='{{ PIPELINE_VERSION }}'
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
export TMPDIR="$(realpath ${JOB_PATH}/../../tmp/${JOB_ID})"
mkdir -p "${TMPDIR}" || true
export INPUT_READS_PATH="${JOB_PATH}/input/reads"
export INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts"
export INPUT_CONFIG_PATH="${JOB_PATH}/input/config"
export INPUT_REFERENCE_PATH="${JOB_PATH}/input/reference"
export PIPELINE_CONFIG="${INPUT_CONFIG_PATH}/pipeline_config.json"
export SITE_CONFIGS="${JOB_PATH}/../../config"
readonly REFERENCE_BASE="${JOB_PATH}/../references/iGenomes"
export CONDA_BASE="${JOB_PATH}/../miniconda3"
export DOWNLOAD_CACHE_PATH="${JOB_PATH}/../../cache/downloads"
export SINGULARITY_CACHEDIR="${JOB_PATH}/../../cache/singularity"
export SINGULARITY_LOCALCACHEDIR="${TMPDIR}"
export PIPELINES_CACHE_PATH="${JOB_PATH}/../../cache/pipelines"
export SINGULARITY_TMPDIR="${TMPDIR}"
export AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
export IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"
export LAXYDL_BRANCH=master
export LAXYDL_USE_ARIA2C=yes
export LAXYDL_PARALLEL_DOWNLOADS=8

# These are applied via chmod to all files and directories in the run, upon completion
export JOB_FILE_PERMS='ug+rw-s,o='
export JOB_DIR_PERMS='ug+rwx-s,o='

# Nextflow specific environment variables
export NXF_TEMP="${TMPDIR}"
export NXF_SINGULARITY_CACHEDIR="${SINGULARITY_CACHEDIR}"
export NXF_OPTS='-Xms1g -Xmx7g'
export NXF_ANSI_LOG='false'
export NXF_VER=22.10.4
# We use a custom .nextflow directory per run so anything cached in ~/.nextflow won't interfere
# (there seems to be some locking issues when two nextflow instances are run simultaneously, or
#  issues downloading the nf-amazon plugin when a version is already cached in ~/.nextflow/plugins ?
#  Using a fresh .nextflow for each run works around this issue.)
export NXF_HOME="${INPUT_SCRIPTS_PATH}/pipeline/.nextflow"
mkdir -p "${INPUT_SCRIPTS_PATH}/pipeline"
# export NXF_DEBUG=1  # 2 # 3

export SLURM_EXTRA_ARGS="{{ SLURM_EXTRA_ARGS|default:"" }}"

# export QUEUE_TYPE="{{ QUEUE_TYPE }}"
# nextflow itself will run on ComputeResource login node, but
# nextflow.config can still make pipeline tasks go to SLURM
export QUEUE_TYPE="local"

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
    trap - EXIT

    local _exit_code=${1:-$?}
    # Use the EXIT_CODE global if set
    [[ -v EXIT_CODE ]] && _exit_code=${EXIT_CODE}

    cd "${JOB_PATH}"
    capture_environment_variables || true
    cleanup_nextflow_intermediates || true
    register_files || true
    finalize_job ${_exit_code}
}

function job_fail_or_cancel() {
    trap - EXIT

    cd "${JOB_PATH}"
    capture_environment_variables || true
    # We keep '.command.*' and '.exitcode' files in the work directory on failure to assist debugging
    cleanup_nextflow_intermediates_keep_work_logs || true
    register_files || true
    # send exit code of 1
    finalize_job 1
}

# Send job fail/done HTTP request, cleanup and remove secrets upon an exit code raise
# This won't catch every case (eg external kill -9), but is better than nothing.
trap job_fail_or_cancel EXIT

if [[ ! -f "${AUTH_HEADER_FILE}" ]]; then
    echo "No auth token file (${AUTH_HEADER_FILE}) - exiting."
    exit 1
fi

# For QUEUE_TYPE=='local'
# PREFIX_JOB_CMD="/usr/bin/env bash -l -c "
MEM=8000 
CPUS=1

# We use sbatch --wait --wrap rather than srun, since it seems more reliable
# and jobs appear pending on the queue immediately
# export SLURM_OPTIONS="--parsable \
#                       --cpus-per-task=${CPUS} \
#                       --mem=${MEM} \
#                       -t 7-0:00 \
#                       --ntasks-per-node=1 \
#                       --ntasks=1 \
#                       ${SLURM_EXTRA_ARGS} \
#                       --job-name=laxy:${JOB_ID}"


# if [[ "${QUEUE_TYPE}" == "slurm" ]] || [[ "${QUEUE_TYPE}" == "slurm-hybrid" ]]; then
#     PREFIX_JOB_CMD="sbatch ${SLURM_OPTIONS} --wait --wrap "
# fi

if [[ "${QUEUE_TYPE}" == "local" ]]; then
    echo $$ >>"${JOB_PATH}/job.pids"
fi

# Various sanity checks to ensure the host is properly configured and in a state that can accept a job
function host_sanity() {
    # TODO: Move this to the genome args fn since we don't always need this to exist, but should
    # check and fail in cases where it's supposed to be there
    if [[ ! -d ${REFERENCE_BASE} ]]; then
        echo "${REFERENCE_BASE} doesn't exist !"
        exit 1
    fi
}

function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    pushd "${JOB_PATH}"

    add_to_manifest "input/**/*.fq" "fastq"
    add_to_manifest "input/**/*.fastq" "fastq"
    add_to_manifest "input/**/*.fq.gz" "fastq"
    add_to_manifest "input/**/*.fastq.gz" "fastq"
    
    add_to_manifest "output/results/**/*.fq" "fastq"
    add_to_manifest "output/results/**/*.fastq" "fastq"
    add_to_manifest "output/results/**/*.fq.gz" "fastq"
    add_to_manifest "output/results/**/*.fastq.gz" "fastq"

    add_to_manifest "output/results/**/*.bam" "bam,alignment"
    add_to_manifest "output/results/**/*.bai" "bai"
    add_to_manifest "output/results/**/multiqc_report.html" "report,html,multiqc"
    add_to_manifest "output/results/**/*_fastqc.html" "report,html,fastqc"
    #add_to_manifest "output/results/**/salmon.merged.gene_counts.tsv" "counts,degust"
    #add_to_manifest "output/results/**/salmon.merged.gene_counts.biotypes.tsv" "counts,degust"
    #add_to_manifest "output/results/featureCounts/counts.star_featureCounts.tsv" "counts,degust"

    add_to_manifest "output/results/star_salmon/salmon.merged.gene_counts_length_scaled.biotypes.tsv" "counts,degust"

    if [[ ! -f "${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts_length_scaled.biotypes.tsv" ]]; then
        add_to_manifest "output/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv" "counts,degust"
    fi

    if [[ ! -f "${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv" ]]; then
        add_to_manifest "output/results/salmon/salmon.merged.gene_counts_length_scaled.tsv" "counts,degust"
        add_to_manifest "output/results/salmon/salmon.merged.gene_counts_length_scaled.biotypes.tsv" "counts,degust"
    fi
    
    # Nextflow reports
    add_to_manifest "output/results/pipeline_info/*.html" "report,html,nextflow"
    add_to_manifest "output/results/pipeline_info/software_versions.tsv" "report,nextflow"

    # Performance is currently poor (late-2021) when registering many files in a single request
    # so we avoid doing this and allow the server-side indexing to pick up the rest
    #add_to_manifest "output/*" ""
    #add_to_manifest "output/**/*" ""
    #add_to_manifest "input/*" ""
    #add_to_manifest "input/**/*" ""

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

     popd
}

function set_genome_args() {
    # See if we can find a custom reference in the fetch_files list
    local _fasta_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_sequence") | .name' "${PIPELINE_CONFIG}" || echo '')
    local _annot_fn=$(jq --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_annotation") | .name' "${PIPELINE_CONFIG}" || echo '')
    
    if [[ -z ${_fasta_fn} ]] && [[ -z ${_annot_fn} ]]; then
        export USING_CUSTOM_REFERENCE=no
    else
        export USING_CUSTOM_REFERENCE=yes
    fi

    # If _fasta_fn and _annot_fn are set, set the expected custom reference paths
    [[ -z ${_fasta_fn} ]] || export GENOME_FASTA="${INPUT_REFERENCE_PATH}/${_fasta_fn}"
    [[ -z ${_annot_fn} ]] || export ANNOTATION_FILE="${INPUT_REFERENCE_PATH}/${_annot_fn}"

    # If reference files exist locally, use those
    _refpath="${REFERENCE_BASE}/${REFERENCE_GENOME_ID}"
    _genome_fa="${_refpath}/Sequence/WholeGenomeFasta/genome.fa"
    _genes_gtf="${_refpath}/Annotation/Genes/genes.gtf"
    if [[ -f "${_genome_fa}" ]] && [[ -f "${_genes_gtf}" ]]; then
        GENOME_ARGS=" --fasta ${_genome_fa} --gtf ${_genes_gtf} "
        # Add flags for locally cached STAR and Salmon index if they exist 
        if [[ -d "${_refpath}/Sequence/STARIndex" ]]; then
            GENOME_ARGS=" ${GENOME_ARGS} --star_index=${_refpath}/Sequence/STARIndex "
        fi
        if [[ -d ${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/salmon ]]; then
            GENOME_ARGS=" ${GENOME_ARGS} --salmon_index=${_refpath}/Sequence/salmon "
        fi
    # If there is no custom genome, then we assume we are using a pre-defined reference
    # defined in the igenomes.config associated with the pipeline
    # For nf-core pipelines these are downloaded on demand from AWS iGenomes
    # ( https://ewels.github.io/AWS-iGenomes )
    elif [[ ${USING_CUSTOM_REFERENCE} == "no" ]]; then
        # The last part of the iGenomes-style ID is the ID used by nf-core,
        # eg Homo_sapiens/Ensembl/GRCh38 -> GRCh38
        export NFCORE_GENOME_ID="$(echo ${REFERENCE_GENOME_ID} | cut -f 3 -d '/')"
        export GENOME_ARGS=" --genome ${NFCORE_GENOME_ID} "

        # Use a locally cached iGenomes copy if it exists
        # if [[ -d ${REFERENCE_BASE}/${REFERENCE_GENOME_ID} ]]; then
        #     GENOME_ARGS="${GENOME_ARGS} --igenomes_base=${REFERENCE_BASE} "
        # fi
        # # Add flags for locally cached STAR and Salmon index if they exist 
        # if [[ -d ${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex ]]; then
        #     GENOME_ARGS="${GENOME_ARGS} --star_index=${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/STARIndex "
        # fi
        # if [[ -d ${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/salmon ]]; then
        #     GENOME_ARGS="${GENOME_ARGS} --salmon_index=${REFERENCE_BASE}/${REFERENCE_GENOME_ID}/Sequence/salmon "
        # fi
    fi

    if [[ ${USING_CUSTOM_REFERENCE} == "yes" ]]; then
        GENOME_ARGS=" --fasta ${GENOME_FASTA} "
        
        if [[ ${_annot_fn} == *.gtf ]] || [[ ${_annot_fn} == *.gtf.gz ]]; then
            export GENOME_ARGS=" ${GENOME_ARGS} --gtf ${ANNOTATION_FILE} "
        elif [[ ${_annot_fn} == *.gff ]] || [[ ${_annot_fn} == *.gff.gz ]]; then
            export GENOME_ARGS=" ${GENOME_ARGS} --gff ${ANNOTATION_FILE} "
        elif [[ ${_annot_fn} == *.gff3 ]] || [[ ${_annot_fn} == *.gff3.gz ]]; then
            ln -s ${ANNOTATION_FILE} ${INPUT_REFERENCE_PATH}/genes.gff.gz
            export ANNOTATION_FILE="${INPUT_REFERENCE_PATH}/genes.gff.gz"
            export GENOME_ARGS=" ${GENOME_ARGS} --gff ${ANNOTATION_FILE} "
        else
            send_event "JOB_INFO" "This isn't going so well. Unable to detemine type of annotation file."
            send_job_finished 1
            exit 1
        fi
    fi
}

function normalize_annotations() {
    # We run custom GFF/GTFs through AGAT in an attempt to ensure they are somewhat uniform and contain the 
    # expected features (exons) and attribute fields (gene_id).
    #
    # The alternative would be to set the nf-core --gtf_group_features and --featurecounts_feature_type to an 
    # appropriate identifier (eg ID, gene, or Name, and CDS vs. exon). 
    
    # TODO: These Prokka GTFs also don't have gene_biotype. It's unlikely we can automatically add this
    #       field reliably (eg can't easily guess protein_coding vs tRNA).
    #       In this case, maybe detect the lack of gene_biotype fields, add --skip_biotype_qc and/or
    #       change --featurecounts_group_type, and ensure post_nextflow_jobs doesn't expect gene_biotype in this case

    # TODO: DuRadar (NFCORE_RNASEQ:RNASEQ:DUPRADAR) seems to fail on these 'cleaned' annotations ?
    #       We could simply add --skip_dupradar when using custom annotations, or get more sophisicated
    #       with a custom nextflow.config that adds:
    # process {
    #    withName: 'NFCORE_RNASEQ:RNASEQ:DUPRADAR' {
    #        errorStrategy 'ignore'
    #    }
    #}

    export AGAT_CONTAINER="https://depot.galaxyproject.org/singularity/agat%3A1.0.0--pl5321hdfd78af_0"
    if [[ ${USING_CUSTOM_REFERENCE} == "yes" && 
          $(zgrep -Pc "\texon\t.*gene_id*" "${ANNOTATION_FILE}") == 0 ]]; then

        send_event "JOB_INFO" "Standardising annotation file using AGAT" || true

        module load singularity || true

        # We need a copy with a real name accessible to Singularity
        # (cached copies with hashed names don't end in .gtf/.gff etc)
        local _tmp=$(mktemp -d)
        local _tmp_annotation_path="${_tmp}/$(basename ${ANNOTATION_FILE})"
        cp $(realpath "${ANNOTATION_FILE}") "${_tmp_annotation_path}"

        local _out_dir=$(dirname "${ANNOTATION_FILE}")
        local _pathbinds=" -B ${_out_dir} -B ${_tmp} "

        # Formatting for WebApollo (!) seems to work well in making a GFF/GTF
        # subread/featureCounts compatible (generates exons features when missing 
        # and adds gene_id attributes, fixes/removes some attributes that seem to break featureCounts).
        # dupRadar QC uses subread featureCounts, among other parts of the pipeline.
        (cd "${JOB_PATH}/output" && \
         singularity run ${_pathbinds} ${AGAT_CONTAINER} \
            agat_sp_webApollo_compliant.pl \
            -g "${_tmp_annotation_path}" \
            -o "${_tmp_annotation_path}.agat_webapollo.gff" \
          >>"${JOB_PATH}/output/agat.log" 2>&1)

        # We then convert GFF to GTF
        (cd "${JOB_PATH}/output" && \
         singularity run ${_pathbinds} ${AGAT_CONTAINER} \
            agat_convert_sp_gff2gtf.pl \
            -i "${_tmp_annotation_path}.agat_webapollo.gff" \
            --gtf_version relax \
            -o "${_out_dir}/annotation.agat.gtf" \
          >>"${JOB_PATH}/output/agat.log" 2>&1)
            
            # --gtf_version 3 \
            #2>"${_out_dir}/annotation.agat_relax.err"

        gzip "${_out_dir}/annotation.agat.gtf"
        export ANNOTATION_FILE="${_out_dir}/annotation.agat.gtf.gz"
        export GENOME_ARGS=" --fasta ${GENOME_FASTA} --gtf ${ANNOTATION_FILE} "

        rm -f "${_tmp_annotation_path}" "${_tmp_annotation_path}.agat_webapollo.gff"
    fi
}

function get_settings_from_pipeline_config() {
    # Extract the pipeline parameters we need from pipeline_config.json
    local _debug_mode=$(jq --raw-output '.params."nf-core-rnaseq".debug_mode' "${PIPELINE_CONFIG}" || echo "false")
    export USER_DEBUG_MODE="no"
    if [[ "${_debug_mode}" == "true" ]]; then
        export USER_DEBUG_MODE="yes"
    fi

    local _has_umi=$(jq --raw-output '.params."nf-core-rnaseq".has_umi' "${PIPELINE_CONFIG}" || echo "false")
    export UMI_FLAGS=""
    if [[ "${_has_umi}" == "true" ]]; then
        export UMI_FLAGS=" --with_umi --skip_umi_extract --umitools_umi_separator : "
    fi
}

function generate_samplesheet() {

    export STRANDEDNESS='auto'

    python ${INPUT_SCRIPTS_PATH}/laxy2nfcore_samplesheet.py  \
      ${INPUT_CONFIG_PATH}/pipeline_config.json ${INPUT_READS_PATH} ${STRANDEDNESS} \
      >${INPUT_CONFIG_PATH}/samplesheet.csv
}

function cleanup_nextflow_intermediates() {
    if [[ ${USER_DEBUG_MODE} == "yes" ]]; then
        return 0;
    fi
    if [[ ${DEBUG} == "yes" ]]; then
        return 0;
    fi

    send_event "JOB_INFO" "Cleaning up." || true
    
    rm -rf "${JOB_PATH}/output/work"
    rm -rf "${JOB_PATH}/output/.nextflow"
}

function cleanup_nextflow_intermediates_keep_work_logs() {
    if [[ ${USER_DEBUG_MODE} == "yes" ]]; then
        return 0;
    fi
    if [[ ${DEBUG} == "yes" ]]; then
        return 0;
    fi

    send_event "JOB_INFO" "Cleaning up (but keeping work/* logs)." || true
    
    # Remove all files except logs from the Nextflow work directory
    find "${JOB_PATH}/output/work/" -type f ! -name ".command.*" ! -name ".exitcode" -delete

    # tar up the work directory so we don't need to ingest tons of little files
    #tar cvzhf "${JOB_PATH}/output/nextflow_work_logs.tar.gz" --directory "${JOB_PATH}/output" work
    
    # Oneliner to tar up the Nextflow script/log files in the work directory so we don't ingest lots of little files
    #find "${JOB_PATH}/output/work/" \( -name "*.command.*" -o -name "*.exitcode" \) -printf 'work/%P\0' | \
    #    tar --null -cvzhf "${JOB_PATH}/output/nextflow_work_logs.tar.gz" --directory "${JOB_PATH}/output" --no-recursion -T -

    # rm -rf "${JOB_PATH}/output/work"
    rm -rf "${JOB_PATH}/output/.nextflow"
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
                        --revision "${NFCORE_PIPELINE_RELEASE}" \
                        --container singularity \
                        --singularity-cache-only \
                        --parallel-downloads ${LAXYDL_PARALLEL_DOWNLOADS} \
                        --compress none \
                        --outdir "${CACHED_PIPELINE_PATH}"
    fi

    mkdir -p "${INPUT_SCRIPTS_PATH}/pipeline"
    cp -r "${CACHED_PIPELINE_PATH}" "${INPUT_SCRIPTS_PATH}/pipeline/"
    export NFCORE_PIPELINE_PATH=$(realpath "${INPUT_SCRIPTS_PATH}/pipeline/nf-core-${NFCORE_PIPELINE_NAME}-${NFCORE_PIPELINE_RELEASE}/workflow")
}

function fastq_sanity_check() {
    #
    # Read every FASTQ with seqkit, exit with error if any fail
    #

    local orig_errexit=${-//[^e]/}
    set -o errexit
    local _cpus=4

    send_event "JOB_INFO" "Starting seqkit stats sanity check."

    mkdir -p "${JOB_PATH}/output/seqkit_stats"
    echo -e "This directory contains the output from 'seqkit stats' for the FASTQ input files provided. " \
            "It is primarily intended to catch corrupted FASTQ files early, before the main pipeline runs." \
            >"${JOB_PATH}/output/seqkit_stats/README.txt"
    
    pushd "${INPUT_READS_PATH}"
    # Get just the header that seqkit stats will output
    echo ">dummy_seq\nXXX\n" | seqkit stats --tabular | head -n 1 >"${JOB_PATH}/output/seqkit_stats/seqkit_stats.tsv"
    local _error=0
    for fq in $(find . -name "*.f*[q,a].gz" -printf '%P\n'); do
        local _fn=$(basename "${fq}")
        seqkit stats --tabular --threads $_cpus $fq \
                > >(tail -n +2 >>"${JOB_PATH}/output/seqkit_stats/seqkit_stats.tsv") \
                2>> "${JOB_PATH}/output/seqkit_stats/seqkit_stats.err"

        # Unforturnately seqkit stats doesn't return a non-zero error code for corrupt files !
        grep -q "[ERRO]" "${JOB_PATH}/output/seqkit_stats/seqkit_stats.err" && \
            { send_event "JOB_INFO" "Something wrong with input file: ${_fn}" & \
              send_job_metadata '{"metadata": {"error": {"bad_input_file": "'${_fn}'"}}}';
              if [[ -z "${orig_errexit}" ]]; then
                set +o errexit
              fi
              popd
              return 1
            }
    done

    popd
    if [[ -z "${orig_errexit}" ]]; then
        set +o errexit
    fi
}

function run_nextflow() {
    cd "${JOB_PATH}/output"

    module load singularity || true

    # TODO: Valid genome IDs from:
    # https://github.com/nf-core/rnaseq/blob/master/conf/igenomes.config

    # export NFCORE_GENOME_ID="R64-1-1"   # yeast
    # export NFCORE_GENOME_ID="GRCm38"    # mouse
    # export NFCORE_GENOME_ID="GRCh38"    # hoomn
    # export NFCORE_GENOME_ID="$(echo ${REFERENCE_GENOME_ID} | cut -f 3 -d '/')"

    # export NFCORE_PIPELINE_PATH="nf-core/rnaseq"  # download, don't use pre-cached version

    # Nextflow job names must be all lowercase, can't start with a number, can't contain dashes
    # regex: ^[a-z](?:[a-z\d]|[-_](?=[a-z\d])){0,79}$
    _nfjobname=$(echo laxy_"${JOB_ID}" | tr '[:upper:]' '[:lower:]')

    #set +o errexit
    #${PREFIX_JOB_CMD} "\
    nextflow run "${NFCORE_PIPELINE_PATH}" \
       --input "${INPUT_CONFIG_PATH}/samplesheet.csv" \
       --outdir ${JOB_PATH}/output/results \
       -c ${INPUT_CONFIG_PATH}/laxy_nextflow.config \
       ${GENOME_ARGS} \
       ${UMI_FLAGS} \
       --aligner star_salmon \
       --pseudo_aligner salmon \
       --save_reference \
       ${NEXTFLOW_CONFIG_ARG} \
       --monochrome_logs \
       -with-trace \
       -with-dag \
       -name "${_nfjobname}" \
       -profile singularity \
        >${JOB_PATH}/output/nextflow.log \
        2>${JOB_PATH}/output/nextflow.err
    #">>"${JOB_PATH}/slurm.jids"
    
    EXIT_CODE=$?
    # Attempt #2, resuming to catch any failures not caught by Nextflow task retries.
    if [[ $EXIT_CODE != 0 ]]; then
        nextflow run "${NFCORE_PIPELINE_PATH}" \
            --input "${INPUT_CONFIG_PATH}/samplesheet.csv" \
            --outdir ${JOB_PATH}/output/results \
            -c ${INPUT_CONFIG_PATH}/laxy_nextflow.config \
            ${GENOME_ARGS} \
            ${UMI_FLAGS} \
            --aligner star_salmon \
            --pseudo_aligner salmon \
            --save_reference \
            ${NEXTFLOW_CONFIG_ARG} \
            --monochrome_logs \
            -with-trace \
            -with-dag \
            -name "${_nfjobname}" \
            -profile singularity \
            -resume \
            >${JOB_PATH}/output/nextflow2.log \
            2>${JOB_PATH}/output/nextflow2.err
    fi

    # TODO: Should we have the --trim_nextseq option here by default ?
    #       (assuming it's mostly benign with non-nextseq/novaseq data ?)
    #       Fancy (but potentially more fragile) way would be to look at 
    #       FASTQ headers, infer machine type from instrument ID and apply 
    #       when required.

    # TODO: log nextflow events to a job-specific url (include a secret in the, expire url after run completed)
    #       It might make sense to build this as a pluggable Django app for Laxy. We'd translate some Nextflow
    #       events into Laxy EventLogs - it's probably too noisy to send everything to EventLogs. Maybe *capture* 
    #       all the Nextflow events (minimally timestamped JSON blobs linked to a job) even if we don't have 
    #       UI to display them right now.
    # https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    # -with-weblog "${NEXTFLOW_WEBLOG_URL}"

    # TODO: if the user provides Nextflow Tower access token (https://tower.nf/tokens) as part of their
    # user profile, then we validate it for shell safety serverside, pass it into the template as 
    # NEXTFLOW_TOWER_TOKEN, set the TOWER_ACCESS_TOKEN env var and add the flag:
    #export TOWER_ACCESS_TOKEN="${NEXTFLOW_TOWER_TOKEN}"
    #-with-tower

    EXIT_CODE=$?
    #set -o errexit
}

function get_salmon_inferred_strandedness() {
    # 0=unstranded, 1=forward, 2=reverse
    
    # We return unstranded if unknown/no match, since this 
    # is likely the best choice for featureCounts when 
    # strandedness is ambigious.
    local meta_info_json="${1}"
    jq --raw-output '.library_types[0]' "${meta_info_json}" | \
        awk '{if ($0 == "U" || $0 == "IU") {print "0"} \
        else if ($0 == "SF" || $0 == "ISF") {print "1"} \
        else if ($0 == "SR" || $0 == "ISR") {print "2"} \
        else {print "0"}}' || echo "0"
}

function post_nextflow_jobs() {
    # This function runs some post-processing and analyis not within nf-core/rnaseq.
    # In particular, a featureCounts output table including biotypes.
    
    # TODO: We currently just run featureCounts directy, however a better way might be to reuse
    #       the existing PREPARE_GENOME and SUBREAD_FEATURECOUNTS tasks within nf-core/rnaseq,
    #       called by a mini nextflow workflow of our own based on a skeleton of workflows/rnaseq.nf
    #       We might be able to overide the process options as required like:
    #  process { 
    # withName: 'NFCORE_RNASEQ:RNASEQ:SUBREAD_FEATURECOUNTS' {
    #     ext.args   = [
    #         '-B -C',
    #         '-t gene', 
    #         '-g gene_biotype', 
    #         '--extraAttributes gene_name,gene_biotype',
    #     ].join(' ').trim()
    # }
    #  }

    local cpus=6

    # This should ideally match the version used by the current $PIPELINE_VERSION
    # See: https://github.com/nf-core/rnaseq/blob/master/modules/nf-core/subread/featurecounts/main.nf
    export SUBREAD_FEATURECOUNTS_CONTAINER="https://depot.galaxyproject.org/singularity/subread:2.0.1--hed695b0_0"
    #export SUBREAD_FEATURECOUNTS_CONTAINER="docker://quay.io/biocontainers/subread:2.0.1--hed695b0_0"

    # We point to the appropriate annoation file (custom or canned iGenomes)
    local _annotation=""
    if [[ ${USING_CUSTOM_REFERENCE} == "yes" ]]; then
        _annotation="${ANNOTATION_FILE}"
    else
        _annotation="$(find ${JOB_PATH}/output/results/genome/ -name "*.gtf" | head -n1)"
    fi
    if [[ -z ${_annotation} ]]; then
        send_error "post_nextflow_jobs" "Unable to find GTF reference" 1
        exit 1
    fi
    _annotation="$(realpath ${_annotation})"

    module load singularity || true

    # We set _PRE as the prefix to our featureCounts command, possibly running
    # inside singularity and/or as a SLURM job.
    local _PRE=""
    local _real_JOB_PATH=$(realpath ${JOB_PATH})  # for singularity
    if [[ $(builtin type -P singularity) ]]; then
        local _PATHBINDS=" -B ${TMPDIR} -B ${_real_JOB_PATH} -B $(realpath ${_annotation}) "
        _PRE="singularity run ${_PATHBINDS} ${SUBREAD_FEATURECOUNTS_CONTAINER} -- "
    fi

    if [[ ${QUEUE_TYPE} == "slurm" ]]; then
        _PRE="sbatch --parsable \
                     --cpus-per-task=${cpus} \
                     --mem=64G \
                     -t 7-0:00 \
                     --job-name=laxy:${JOB_ID}:post_nextflow \
                     ${SLURM_EXTRA_ARGS} \
                     --wait --wrap ${_PRE} "
    fi
    
    # We grab the Salmon predicted strandedness from it's meta_info.json output file.
    # We assume all samples have the same strandedness, just get the prediction
    # for the first sample we find ....
    # There are other options for this another good option would be the rseqc infer_experiment output: 
    #    results/star_salmon/rseqc/infer_experiment/${sample_name}.infer_experiment.txt
    # Or, the qualimap settings ()"protocol = strand-specific-forward"):
    #    results/star_salmon/qualimap/${sample_name}/rnaseq_qc_results.txt
    # TODO: Might be worth parsing the rseq infer_experiment numbers and putting them into 
    #       job metadata (as per rnasik): 
    #           send_job_metadata '{"metadata":{"results":{"strandedness":{"predicted":"'${prediction}'","bias":'${bias}'}}}}' || true
    local _first_meta_info_json=$(find "${_real_JOB_PATH}/output/results/star_salmon/" -type f -name meta_info.json | head -n1)
    local _strand=$(get_salmon_inferred_strandedness "${_first_meta_info_json}")

    # Ensure output directory is writable
    local _outdir="${_real_JOB_PATH}/output/results/featureCounts"
    local _bamdir="${_real_JOB_PATH}/output/results/star_salmon"
    mkdir -p "${_outdir}"
    chmod u+w "${_outdir}"

    # Detect paired end reads
    local _FC_PAIRED_FLAGS=""
    if [[ $(${INPUT_SCRIPTS_PATH}/is_paired.py ${INPUT_READS_PATH}) == "paired" ]]; then
        _FC_PAIRED_FLAGS=" -p "
    fi

    # We use -Q 10 to remove multimappers, as per logic in RNAsik: 
    # https://github.com/MonashBioinformaticsPlatform/RNAsik-pipe/blob/master/src/sikCounts.bds#L60
    # We only run if BAMs were generated
    if [[ -n "$(find ${_bamdir} -name '*.bam' -print -quit)" ]]; then
        ${_PRE} featureCounts \
            -B -C \
            -T ${cpus} \
            -Q 10 \
            ${_FC_PAIRED_FLAGS} \
            --tmpDir "${TMPDIR}" \
            -a "${_annotation}" \
            -s ${_strand} \
            --extraAttributes gene_name,gene_biotype \
            -o "${_outdir}/counts.star_featureCounts.txt" \
            ${_bamdir}/*.bam \
                >"${_outdir}/counts.star_featureCounts.out" 2>&1

        # Remove featureCounts 'comment' header and rewrite long paths + suffixes in sample names
        tail -n +2 "${_outdir}/counts.star_featureCounts.txt" | \
                sed '1s#'"${_bamdir}"'##g' | \
                sed '1s#\.markdup\.sorted\.bam##g' | \
                sed '1s#\.umi_dedup\.sorted\.bam##g' \
                >"${_outdir}/counts.star_featureCounts.tsv"

        # Merge the biotypes from featureCounts into the Salmon counts tables.
        ${INPUT_SCRIPTS_PATH}/merge_biotypes.py \
            "${_outdir}/counts.star_featureCounts.tsv" \
            "${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts.tsv" \
            >"${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts.biotypes.tsv"

        ${INPUT_SCRIPTS_PATH}/merge_biotypes.py \
            "${_outdir}/counts.star_featureCounts.tsv" \
            "${JOB_PATH}/output/results/salmon/salmon.merged.gene_counts.tsv" \
            >"${JOB_PATH}/output/results/salmon/salmon.merged.gene_counts.biotypes.tsv"

        ${INPUT_SCRIPTS_PATH}/merge_biotypes.py \
            "${_outdir}/counts.star_featureCounts.tsv" \
            "${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv" \
            >"${JOB_PATH}/output/results/star_salmon/salmon.merged.gene_counts_length_scaled.biotypes.tsv"

        ${INPUT_SCRIPTS_PATH}/merge_biotypes.py \
            "${_outdir}/counts.star_featureCounts.tsv" \
            "${JOB_PATH}/output/results/salmon/salmon.merged.gene_counts_length_scaled.tsv" \
            >"${JOB_PATH}/output/results/salmon/salmon.merged.gene_counts_length_scaled.biotypes.tsv"
    fi
}

update_permissions || true

mkdir -p "${TMPDIR}"
mkdir -p input
mkdir -p output

mkdir -p "${INPUT_CONFIG_PATH}" "${INPUT_SCRIPTS_PATH}" "${INPUT_READS_PATH}"

####
#### Setup and import a Conda environment
####

install_miniconda || fail_job 'install_miniconda' '' $?

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "${PIPELINE_NAME}" "${PIPELINE_VERSION}" || fail_job 'init_conda_env' '' $?

get_settings_from_pipeline_config || fail_job 's' 'get_settings_from_pipeline_config' $?

# nextflow_self_update || true

update_laxydl || send_error 'update_laxydl' '' $?

####
#### Stage input data ###
####

download_input_data "${INPUT_REFERENCE_PATH}" "reference_genome" || fail_job 'download_input_data' 'Failed to download reference genome' $?

download_input_data "${INPUT_READS_PATH}" "ngs_reads" || fail_job 'download_input_data' 'Failed to download input data' $?

set_genome_args

normalize_annotations

# This probably isn't all that necessary for nf-core/rnaseq since it runs
# some FASTQ subsampling and FASTQC early that would catch bad FASTQs
# fastq_sanity_check || fail_job 'fastq_sanity_check' '' $?

generate_samplesheet

get_site_nextflow_config || true

cache_pipeline

cd "${JOB_PATH}/output"

send_event "JOB_PIPELINE_STARTING" "Starting pipeline."

run_nextflow

post_nextflow_jobs || true

cd "${JOB_PATH}"

# Called by job_done and job_fail_or_cancel, so we don't need this here
# cleanup_nextflow_intermediates || true

# Call job finalization with explicit exit code from the main pipeline command
job_done $EXIT_CODE

# Remove the trap so job_done doesn't get called a second time when the script naturally exits
trap - EXIT
exit 0
