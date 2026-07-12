#!/usr/bin/env bash

##
# BRB-seq (fqdemux + nf-core/rnaseq) wrapper script
##

set -o nounset
set -o pipefail
set -o xtrace

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"

# Global variables used throughout the script
export JOB_PATH="${PWD}"
# INPUT_SCRIPTS_PATH is needed before sourcing env.sh if env.sh uses it
export INPUT_SCRIPTS_PATH="${JOB_PATH}/input/scripts" 

# Source common environment variables
source "${INPUT_SCRIPTS_PATH}/env.sh" || exit 1

export NFCORE_PIPELINE_RELEASE="${PIPELINE_VERSION}"
export NFCORE_PIPELINE_NAME="rnaseq"
export REFERENCE_GENOME_ID="{{ REFERENCE_GENOME }}"

export FQDEMUX_VERSION="c298903"

# run_job.sh specific variables or overrides
export TMPDIR="$(realpath ${JOB_PATH}/../../tmp/${JOB_ID})"
mkdir -p "${TMPDIR}" || true
export INPUT_REFERENCE_PATH="${JOB_PATH}/input/reference"
readonly REFERENCE_BASE="${JOB_PATH}/../references/iGenomes"
export PIPELINES_CACHE_PATH="${JOB_PATH}/../../cache/pipelines"

declare -a TRIMMER_ARGS=()

# Nextflow specific environment variables
export NXF_TEMP="${TMPDIR}"
export NXF_SINGULARITY_CACHEDIR="${SINGULARITY_CACHEDIR}"
export NXF_APPTAINER_CACHEDIR="${SINGULARITY_CACHEDIR}"
export NXF_APPTAINER_TMPDIR="${TMPDIR}"
export NXF_OPTS='-Xms1g -Xmx7g'
export NXF_ANSI_LOG='false'
export NXF_VER=24.10.6
# We use a custom .nextflow directory per run so anything cached in ~/.nextflow won't interfere
# (there seems to be some locking issues when two nextflow instances are run simultaneously, or
#  issues downloading the nf-amazon plugin when a version is already cached in ~/.nextflow/plugins ?
#  Using a fresh .nextflow for each run works around this issue.)
export NXF_HOME="${INPUT_SCRIPTS_PATH}/pipeline/.nextflow"
mkdir -p "${INPUT_SCRIPTS_PATH}/pipeline"
export AWS_EC2_METADATA_DISABLED=true
# export NXF_DEBUG=1  # 2 # 3

# nextflow itself will run on ComputeResource login node, but
# nextflow.config can still make pipeline tasks go to SLURM
# TODO: This should probably be QUEUE_TYPE="slurm" (or taken from ComputeResource params)
#       - we need to add a ${_PRE} to submit the nextflow process as a SLURM task
export QUEUE_TYPE="local" # Override QUEUE_TYPE from env.sh

##
# Setup environment variables and load the laxy bash helper functions.
##

source "${INPUT_SCRIPTS_PATH}/laxy.lib.sh" || exit 1

source "${INPUT_SCRIPTS_PATH}/agat_normalize_annotation.sh" || exit 1

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

    # Tag 'degust' for a "Send to Degust" button (but not front page)
    #add_to_manifest "output/results/**/salmon.merged.gene_counts.tsv" "degust"
    #add_to_manifest "output/results/**/salmon.merged.gene_counts.biotypes.tsv" "degust"
    add_to_manifest "output/results/**/salmon.merged.gene_counts_scaled.tsv" "degust"
    add_to_manifest "output/results/**/salmon.merged.gene_counts_scaled.biotypes.tsv" "degust"
    add_to_manifest "output/results/**/salmon.merged.gene_counts_length_scaled.tsv" "degust"
    add_to_manifest "output/results/**/salmon.merged.gene_counts_length_scaled.biotypes.tsv" "degust"
    
    # featureCounts on front page, tagged 'counts'
    add_to_manifest "output/results/featureCounts/counts.star_featureCounts.tsv" "counts,degust,front-page"

    # Estimated counts scaled up to the original library size,
    # and length-scaled to remove effects of differential transcript usage between samples 
    # when looking at gene-level expression (tximport countsFromAbundance="lengthScaledTPM") from Salmon shouldn't be used for 3' focused sequencing
    # local _jobpage_counts_prefix="salmon.merged.gene_counts_length_scaled"
    
    # Estimated counts scaled up to original library size (tximport countsFromAbundance="scaledTPM")
    # Does not account for potential bias from differtial transcript usage between samples, but is
    # more approriate for 3' focused sequencing
    # see: https://bioconductor.org/packages/devel/bioc/vignettes/tximport/inst/doc/tximport.html#Downstream_DGE_in_Bioconductor
    # local _jobpage_counts_prefix="salmon.merged.gene_counts_scaled"

    # Unscaled Salmon counts. May suffer from bias due to differential transcript usage, but correlates much better with
    # simple featureCounts output
    local _jobpage_counts_prefix="salmon.merged.gene_counts"

    # Here we find a single Salmon counts file to put on the front page 
    # (tagged 'counts' for front page, and 'degust' for a button)
    add_to_manifest "output/results/star_salmon/${_jobpage_counts_prefix}.biotypes.tsv" "counts,degust"

    if [[ ! -f "${JOB_PATH}/output/results/star_salmon/${_jobpage_counts_prefix}.biotypes.tsv" ]]; then
        add_to_manifest "output/results/star_salmon/${_jobpage_counts_prefix}.tsv" "counts,degust,front-page"
    fi

    if [[ ! -f "${JOB_PATH}/output/results/star_salmon/${_jobpage_counts_prefix}.tsv" ]]; then
        add_to_manifest "output/results/salmon/${_jobpage_counts_prefix}.tsv" "counts,degust,front-page"
        add_to_manifest "output/results/salmon/${_jobpage_counts_prefix}.biotypes.tsv" "counts,degust,front-page"
    fi
    
    # Catch these if not already tagged above
    add_to_manifest "output/results/**/salmon.merged.gene_counts.tsv" "degust"
    add_to_manifest "output/results/**/salmon.merged.gene_counts.biotypes.tsv" "degust"

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
    local _fasta_fn=$(jq -e --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_sequence") | .name' "${PIPELINE_CONFIG}" || echo '')
    local _annot_fn=$(jq -e --raw-output '.params.fetch_files[] | select(.type_tags[] == "genome_annotation") | .name' "${PIPELINE_CONFIG}" || echo '')
    
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
        export ANNOTATION_FILE="${_genes_gtf}"
        export GENOME_FASTA="${_genome_fa}"

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
        # --gtf vs --gff is chosen in normalize_annotations() from ANN_FORMAT.
    fi
}

function normalize_annotation_filename_for_nfcore() {
    [[ ${USING_CUSTOM_REFERENCE} == "yes" ]] || return 0
    [[ -n "${ANNOTATION_FILE:-}" ]] || return 0
    [[ -f "${ANNOTATION_FILE}" ]] || return 0

    local _dir _base _newpath
    _dir="$(dirname "${ANNOTATION_FILE}")"
    _base="$(basename "${ANNOTATION_FILE}")"

    if [[ "${_base}" == *.gff3.gz ]]; then
        _newpath="${_dir}/${_base%.gff3.gz}.gff.gz"
        if [[ "${ANNOTATION_FILE}" != "${_newpath}" ]]; then
            rm -f "${_newpath}"
            ln -sf "${_base}" "${_newpath}" || fail_job 'normalize_annotation_symlink_gff3_gz' '' $?
            export ANNOTATION_FILE="${_newpath}"
        fi
        return 0
    fi

    if [[ "${_base}" == *.gff3 ]]; then
        _newpath="${_dir}/${_base%.gff3}.gff"
        rm -f "${_newpath}"
        ln -sf "${_base}" "${_newpath}" || fail_job 'normalize_annotation_symlink_gff3' '' $?
        export ANNOTATION_FILE="${_newpath}"
        return 0
    fi

    if [[ "${_base}" == *.gff ]] && [[ "${_base}" != *.gff.gz ]]; then
        _newpath="${_dir}/${_base%.gff}.gff.gz"
        gzip -cn "${ANNOTATION_FILE}" > "${_newpath}" || fail_job 'normalize_annotation_gzip_gff' '' $?
        rm -f "${ANNOTATION_FILE}"
        export ANNOTATION_FILE="${_newpath}"
        return 0
    fi

    if [[ "${_base}" == *.gtf ]] && [[ "${_base}" != *.gtf.gz ]]; then
        _newpath="${_dir}/${_base%.gtf}.gtf.gz"
        gzip -cn "${ANNOTATION_FILE}" > "${_newpath}" || fail_job 'normalize_annotation_gzip_gtf' '' $?
        rm -f "${ANNOTATION_FILE}"
        export ANNOTATION_FILE="${_newpath}"
    fi
}

function normalize_annotations() {
    export ANNOTATION_FLAGS=""
    export ANN_FEATURE_TYPE="exon"
    export ANN_GROUP_FEATURES="gene_id"
    export ANN_EXTRA_ATTRIBUTES="gene_name"
    export ANN_BIOTYPE_ATTR="gene_biotype"
    export NFCORE_GTF_GROUP_FEATURES="gene_id"
    export NFCORE_BIOTYPE_ATTR="gene_biotype"

    [[ ${USING_CUSTOM_REFERENCE} == "yes" ]] || return 0

    normalize_annotation_filename_for_nfcore

    # AGAT normalisation disabled - superseded by detect_annotation_style.py +
    # filter_annotation_features.py (and drop_biotype_features.py), which handle
    # every corpus case (Ensembl, GENCODE, RefSeq, NCBI GenBank, Bakta, Prokka,
    # SnapGene) without AGAT's prokaryote-misdetection bug (F8_agat_converted xfail).
    # See ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 2.
    # agat_normalize_annotation

    check_fasta_annotation_seqids


    python "${INPUT_SCRIPTS_PATH}/detect_annotation_style.py"         "${ANNOTATION_FILE}"         --output "${INPUT_CONFIG_PATH}/annotation_style.env"       || fail_job 'detect_annotation_style' '' $?

    source "${INPUT_CONFIG_PATH}/annotation_style.env"

    insert_missing_transcript
    drop_biotype_features
    filter_annotation_features

    if [[ -n "${ANNOTATION_FILE:-}" ]] && [[ -f "${ANNOTATION_FILE}" ]]; then
        if [[ "${ANN_FORMAT}" == "gtf" ]]; then
            GENOME_ARGS+=" --gtf ${ANNOTATION_FILE} "
        else
            GENOME_ARGS+=" --gff ${ANNOTATION_FILE} "
        fi
        export GENOME_ARGS
    fi

    # nf-core/rnaseq's own PREPARE_GENOME converts a --gff input to GTF via
    # gffread internally, which always synthesises gene_id/transcript_id
    # attributes from ID=/Parent= regardless of the original GFF3's
    # hierarchy attribute name - "Parent" itself is consumed and does not
    # survive into the GTF that CUSTOM_TX2GENE (and QUANTIFY_STAR_SALMON's
    # own internal Salmon quantification) reads via --gtf_group_features.
    # Passing the raw ANN_GROUP_FEATURES (e.g. "Parent", picked for OUR OWN
    # filter_annotation_features.py/drop_biotype_features.py parsing of the
    # ORIGINAL GFF3) straight through to nf-core here means every row's
    # attribute lookup for that name fails, producing an empty tx2gene
    # mapping and tximport dying with "No column contains all vector
    # entries ...". Confirmed against a real human chr21 3Mb region.
    # See ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 9.
    # When --gtf is passed instead (ANN_FORMAT=gtf), nf-core uses the file
    # unchanged with no internal conversion, so the detected grouping
    # attribute genuinely is what's in the file and must be passed as-is.
    export NFCORE_GTF_GROUP_FEATURES="${ANN_GROUP_FEATURES}"
    [[ "${ANN_FORMAT}" == "gff3" ]] && NFCORE_GTF_GROUP_FEATURES="gene_id"

    # Same gffread-conversion problem as above, but for the biotype attribute used by
    # SUBREAD_FEATURECOUNTS's biotype QC (--featurecounts_group_type): NCBI/RefSeq GFF3's
    # "gene_biotype" attribute on gene rows does not survive nf-core's internal gffread
    # GFF3->GTF conversion, while "gbkey" (the GenBank feature key, eg Gene/mRNA/ncRNA/CDS)
    # does. Passing "gene_biotype" through unchanged makes featureCounts fail outright with
    # "failed to find the gene identifier attribute in the 9th column". Confirmed against a
    # real mouse chr19 whole-chromosome run. See ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 9.
    export NFCORE_BIOTYPE_ATTR="${ANN_BIOTYPE_ATTR}"
    [[ "${ANN_FORMAT}" == "gff3" ]] && [[ "${ANN_BIOTYPE_ATTR}" == "gene_biotype" ]] && NFCORE_BIOTYPE_ATTR="gbkey"

    ANNOTATION_FLAGS=" --featurecounts_feature_type ${ANN_FEATURE_TYPE}"
    ANNOTATION_FLAGS+=" --gtf_group_features ${NFCORE_GTF_GROUP_FEATURES}"
    [[ -n "${ANN_EXTRA_ATTRIBUTES}" ]] &&         ANNOTATION_FLAGS+=" --gtf_extra_attributes ${ANN_EXTRA_ATTRIBUTES}"
    [[ -n "${NFCORE_BIOTYPE_ATTR}" ]] &&         ANNOTATION_FLAGS+=" --featurecounts_group_type ${NFCORE_BIOTYPE_ATTR}"
    [[ -n "${ANN_SKIP_FLAGS}" ]] && ANNOTATION_FLAGS+=" ${ANN_SKIP_FLAGS}"
    export ANNOTATION_FLAGS
}

function get_settings_from_pipeline_config() {
    # Extract the pipeline parameters we need from pipeline_config.json
    local _debug_mode=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].debug_mode' "${PIPELINE_CONFIG}" || echo "false")
    export USER_DEBUG_MODE="no"
    if [[ "${_debug_mode}" == "true" ]]; then
        export USER_DEBUG_MODE="yes"
    fi

    local _has_umi=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].has_umi' "${PIPELINE_CONFIG}" || echo "false")
    export UMI_FLAGS=""
    if [[ "${_has_umi}" == "true" ]]; then
        export UMI_FLAGS=" --with_umi --skip_umi_extract --umitools_umi_separator : "
    fi

    local _skip_trimming=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].skip_trimming' "${PIPELINE_CONFIG}" || echo "false")
    export EXTRA_FLAGS=""
    if [[ "${_skip_trimming}" == "true" ]]; then
        export EXTRA_FLAGS="${EXTRA_FLAGS} --skip_trimming "
    fi

    local -i _min_mapped_reads=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].min_mapped_reads' "${PIPELINE_CONFIG}" || echo "5")
    export MIN_MAPPED_READS_ARG=" --min_mapped_reads ${_min_mapped_reads} "

    # Not currently exposed as a UI option (unlike min_mapped_reads above): nf-core/rnaseq's
    # own default of 10000 is sane for real user data, but it's a separate skip-gate (applied
    # right after trimming, before alignment) that min_mapped_reads=0 does NOT disable. Left
    # unset in pipeline_config.json, this falls through to nf-core's own default unchanged;
    # e2e/corpus tests override it to 0 to exercise star_salmon/featureCounts on tiny
    # synthetic read sets that would otherwise be filtered out here.
    local -i _min_trimmed_reads=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].min_trimmed_reads' "${PIPELINE_CONFIG}" || echo "10000")
    export MIN_TRIMMED_READS_ARG=" --min_trimmed_reads ${_min_trimmed_reads} "
    
    local _trimmer=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].trimmer' "${PIPELINE_CONFIG}" || echo "")
    TRIMMER_ARGS=()
    if [[ "${_trimmer}" == "fastp" ]]; then
        TRIMMER_ARGS=(--trimmer fastp --extra_fastp_args "--trim_poly_g --trim_poly_x")
    elif [[ "${_trimmer}" == "trimgalore" ]]; then
        TRIMMER_ARGS=(--trimmer trimgalore)
    fi
}

function remove_index_reads() {
    # We frequently see I1/I2 index or UMI reads passed by users
    # Ideally these would be filtered / warned about in the UI, there are cases (like passing tarballs)
    # where the user has no opportunity to exclude them. Given that this nf-core/rnaseq wrapper currently does
    # not use I1 / I2 reads (eg as UMIs), we instead delete them before creating the samplesheet.
    find ${INPUT_READS_PATH} -type f -name "*_I1_001.f*.gz" -delete
    find ${INPUT_READS_PATH} -type f -name "*_I2_001.f*.gz" -delete
}

function generate_fqdemux_samplesheet() {
    python ${INPUT_SCRIPTS_PATH}/laxy2fqdemux_samplesheets.py \
      --single-ended R2 \
      "${PIPELINE_CONFIG}" \
      "${INPUT_READS_PATH}" \
      "${INPUT_CONFIG_PATH}/fqdemux_samplesheet.tsv" \
      "${INPUT_CONFIG_PATH}/fqdemux_readstructures.tsv"
    
    # Check if the files were created successfully, otherwise exit
    if [[ ! -f "${INPUT_CONFIG_PATH}/fqdemux_samplesheet.tsv" ]] || [[ ! -f "${INPUT_CONFIG_PATH}/fqdemux_readstructures.tsv" ]]; then
        send_event "JOB_ERROR" "Failed to generate fqdemux input samplesheets."
        exit 1
    fi
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
    local _save_genome_index=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].save_genome_index' "${PIPELINE_CONFIG}" || echo "false")
    if [[ ${_save_genome_index} != 'true' ]]; then
        rm -rf "${JOB_PATH}/output/results/genome/index"
    fi

    local _save_reference_genome=$(jq -e --raw-output '.params["'${PIPELINE_NAME}'"].save_reference_genome' "${PIPELINE_CONFIG}" || echo "false")
    if [[ ${_save_reference_genome} != 'true' ]]; then
        rm -rf "${JOB_PATH}/output/results/genome"
    fi

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
                        --container-system singularity \
                        --container-cache-utilisation amend \
                        --parallel-downloads ${LAXYDL_PARALLEL_DOWNLOADS} \
                        --compress none \
                        --outdir "${CACHED_PIPELINE_PATH}"
    fi

    mkdir -p "${INPUT_SCRIPTS_PATH}/pipeline"
    cp -r "${CACHED_PIPELINE_PATH}" "${INPUT_SCRIPTS_PATH}/pipeline/"
    _NFCORE_PIPELINE_RELEASE_UNDERSCORED=$(echo "${NFCORE_PIPELINE_RELEASE}" | tr '.' '_')
    export NFCORE_PIPELINE_PATH=$(realpath "${INPUT_SCRIPTS_PATH}/pipeline/nf-core-${NFCORE_PIPELINE_NAME}-${NFCORE_PIPELINE_RELEASE}/${_NFCORE_PIPELINE_RELEASE_UNDERSCORED}")
}

function cache_fqdemux_pipeline() {
    nextflow pull -revision ${FQDEMUX_VERSION} MonashBioinformaticsPlatform/fqdemux
}

function run_fqdemux_pipeline() {
    nextflow run MonashBioinformaticsPlatform/fqdemux \
        -revision ${FQDEMUX_VERSION} \
        -c ${INPUT_CONFIG_PATH}/laxy_nextflow.config \
        ${NEXTFLOW_CONFIG_ARG} \
        --barcodes_samplesheet ${JOB_PATH}/input/config/fqdemux_samplesheet.tsv \
        --readstructure_samplesheet ${JOB_PATH}/input/config/fqdemux_readstructures.tsv \
        --outdir ${JOB_PATH}/output/results \
        -profile slurm \
        -resume

    cp ${JOB_PATH}/output/results/samplesheet.csv ${INPUT_CONFIG_PATH}/samplesheet.csv
    # Remove the 'unmatched' (no barcode) sample from the copy of the samplesheet we will use
    sed -i '/^unmatched/d' ${INPUT_CONFIG_PATH}/samplesheet.csv

    # Drop copy the R2 filenames to the R1 column, then drop the values in third column (fastq_2)
    # So we are 'single-ended' using only the R2 reads.
    # awk -F, \
    #   'BEGIN {OFS=","} NR==1 {print; next} {$2=$3; $3=""; print}' \
    #   ${INPUT_CONFIG_PATH}/samplesheet.csv >${INPUT_CONFIG_PATH}/samplesheet.csv.tmp && \
    #   mv ${INPUT_CONFIG_PATH}/samplesheet.csv.tmp ${INPUT_CONFIG_PATH}/samplesheet.csv

    # Change the standedness in the samplesheet to 'reverse' as expected for BRB-seq
    # sed -i 's/,auto$/,reverse/' ${INPUT_CONFIG_PATH}/samplesheet.csv
}

function run_nextflow() {
    cd "${JOB_PATH}/output"

    #module unload singularity || true
    #module load singularity || true

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

    EXIT_CODE=0

    #set +o errexit
    #${PREFIX_JOB_CMD} "\
    nextflow run "${NFCORE_PIPELINE_PATH}" \
       --input "${INPUT_CONFIG_PATH}/samplesheet.csv" \
       --outdir ${JOB_PATH}/output/results \
       ${GENOME_ARGS} \
       ${UMI_FLAGS} \
       ${MIN_MAPPED_READS_ARG} \
       ${MIN_TRIMMED_READS_ARG} \
       ${EXTRA_FLAGS} \
       ${ANNOTATION_FLAGS} \
       "${TRIMMER_ARGS[@]}" \
       --extra_star_align_args '"--alignIntronMax 1000000 --alignIntronMin 20 --alignMatesGapMax 1000000 --alignSJoverhangMin 8 --outFilterMismatchNmax 999 --outFilterMultimapNmax 20 --outFilterType BySJout --outFilterMismatchNoverLmax 0.1 --clip3pAdapterSeq AAAAAAAA"' \
       --extra_salmon_quant_args '"--noLengthCorrection"' \
       --aligner star_salmon \
       --pseudo_aligner salmon \
       --save_reference=true \
       --save_umi_intermeds=true \
       --monochrome_logs \
       -with-trace \
       -with-dag \
       -name "${_nfjobname}" \
       -c ${INPUT_CONFIG_PATH}/laxy_nextflow.config \
       ${NEXTFLOW_CONFIG_ARG} \
       -profile apptainer \
        >${JOB_PATH}/output/nextflow.log \
        2>${JOB_PATH}/output/nextflow.err || EXIT_CODE=$?
    #">>"${JOB_PATH}/slurm.jids"

    #  --save_align_intermeds=true \

    #EXIT_CODE=$?
    # Attempt #2, resuming to catch any failures not caught by Nextflow task retries.
    if [[ ${EXIT_CODE} != 0 ]]; then
        nextflow run "${NFCORE_PIPELINE_PATH}" \
            --input "${INPUT_CONFIG_PATH}/samplesheet.csv" \
            --outdir ${JOB_PATH}/output/results \
            ${GENOME_ARGS} \
            ${UMI_FLAGS} \
            ${MIN_MAPPED_READS_ARG} \
            ${MIN_TRIMMED_READS_ARG} \
            ${EXTRA_FLAGS} \
            ${ANNOTATION_FLAGS} \
            "${TRIMMER_ARGS[@]}" \
            --extra_star_align_args '"--alignIntronMax 1000000 --alignIntronMin 20 --alignMatesGapMax 1000000 --alignSJoverhangMin 8 --outFilterMismatchNmax 999 --outFilterMultimapNmax 20 --outFilterType BySJout --outFilterMismatchNoverLmax 0.1 --clip3pAdapterSeq AAAAAAAA"' \
            --extra_salmon_quant_args '"--noLengthCorrection"' \
            --aligner star_salmon \
            --pseudo_aligner salmon \
            --save_reference=true \
            --save_umi_intermeds=true \
            --monochrome_logs \
            -with-trace \
            -with-dag \
            -name "${_nfjobname}_2" \
            -c ${INPUT_CONFIG_PATH}/laxy_nextflow.config \
            ${NEXTFLOW_CONFIG_ARG} \
            -profile apptainer \
            -resume \
            >${JOB_PATH}/output/nextflow2.log \
            2>${JOB_PATH}/output/nextflow2.err || EXIT_CODE=$?
    fi

    #  --save_align_intermeds=true \


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

    #EXIT_CODE=$?
    #set -o errexit
}

function get_salmon_inferred_strandedness() {
    # 0=unstranded, 1=forward, 2=reverse
    
    # We return unstranded if unknown/no match, since this 
    # is likely the best choice for featureCounts when 
    # strandedness is ambigious.
    local meta_info_json="${1}"
    jq -e --raw-output '.library_types[0]' "${meta_info_json}" | \
        awk '{if ($0 == "U" || $0 == "IU") {print "0"} \
        else if ($0 == "SF" || $0 == "ISF") {print "1"} \
        else if ($0 == "SR" || $0 == "ISR") {print "2"} \
        else {print "0"}}' || echo "0"
}

function post_nextflow_pipeline() {
    local paired_flag=" --paired=true "
    if [[ $(${INPUT_SCRIPTS_PATH}/is_paired.py ${JOB_PATH}/output/results/demultiplexed/output) == "single" ]]; then
        paired_flag=" --paired=false "
    fi

    _nfjobname=$(echo laxy_"${JOB_ID}" | tr '[:upper:]' '[:lower:]')

    local _fc_annotation=""
    local _fc_group_features="${ANN_GROUP_FEATURES}"
    local _fc_extra_attributes="${ANN_EXTRA_ATTRIBUTES}"
    local _fc_biotype_attr="${ANN_BIOTYPE_ATTR}"

    # For GFF3 input, prefer nf-core's own gffread-converted *.filtered.gtf over our
    # own ANNOTATION_FILE (still in the original Parent=/ID= GFF3 hierarchy). This
    # matters because Salmon's gene-level counts (which this step's output later
    # gets merged into, see merge_biotypes.py) are keyed on gffread's synthesised
    # gene_id, forced via NFCORE_GTF_GROUP_FEATURES/ANNOTATION_FLAGS in
    # normalize_annotations(). Grouping our own separate featureCounts run by the
    # originally-detected attribute (eg "Parent", giving transcript/rna-level ids
    # like "rna-XR_...") instead produces a completely different id namespace that
    # never matches Salmon's "gene-..." ids, so the later merge silently finds no
    # matches and every biotype/chromosome column comes back empty - even though the
    # counts themselves are fine. Confirmed against a real whole-genome NCBI RefSeq
    # mouse run. See ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 9.
    if [[ "${ANN_FORMAT:-}" == "gff3" ]]; then
        _fc_annotation=$(find "${JOB_PATH}/output/results/genome" -type f \( -name '*.filtered.gtf' -o -name '*.filtered.gtf.gz' \) 2>/dev/null | head -n 1)
        [[ -z "${_fc_annotation}" ]] && _fc_annotation=$(find "${JOB_PATH}/output/work" -type f \( -name '*.filtered.gtf' -o -name '*.filtered.gtf.gz' \) 2>/dev/null | head -n 1)
        if [[ -n "${_fc_annotation}" && -f "${_fc_annotation}" ]]; then
            _fc_group_features="${NFCORE_GTF_GROUP_FEATURES}"
            # "Name" doesn't survive gffread's conversion; "gene_name" is always
            # synthesised in its place (and "gene", when present, is preserved as-is).
            _fc_extra_attributes="gene_name"
            _fc_biotype_attr="${NFCORE_BIOTYPE_ATTR}"
        fi
    fi

    if [[ -z "${_fc_annotation}" || ! -f "${_fc_annotation}" ]] && [[ -n "${ANNOTATION_FILE:-}" && -f "${ANNOTATION_FILE}" ]]; then
        _fc_annotation="${ANNOTATION_FILE}"
    fi
    if [[ -z "${_fc_annotation}" || ! -f "${_fc_annotation}" ]]; then
        _fc_annotation=$(find "${JOB_PATH}/output/results/genome" -type f \( -name '*.filtered.gtf' -o -name '*.filtered.gtf.gz' \) 2>/dev/null | head -n 1)
    fi
    if [[ -z "${_fc_annotation}" || ! -f "${_fc_annotation}" ]]; then
        _fc_annotation=$(find "${JOB_PATH}/output/work" -type f \( -name '*.filtered.gtf' -o -name '*.filtered.gtf.gz' \) 2>/dev/null | head -n 1)
    fi
    if [[ -z "${_fc_annotation}" || ! -f "${_fc_annotation}" ]]; then
        send_event "JOB_INFO" "Skipping featureCounts post-processing: no annotation file (set save_reference so nf-core publishes results/genome/*.filtered.gtf, use a local iGenomes cache with genes.gtf, or upload a custom annotation)." || true
        return 0
    fi

    nextflow run "${INPUT_SCRIPTS_PATH}/featurecounts_postnfcore.nf" \
       --scripts_path="${INPUT_SCRIPTS_PATH}" \
       --bams="${JOB_PATH}/output/results/star_salmon/"'*.umi_dedup.sorted.bam' \
       --annotation="${_fc_annotation}" \
       --feature_type="${ANN_FEATURE_TYPE}" \
       --group_features="${_fc_group_features}" \
       --extra_attributes="${_fc_extra_attributes}" \
       --biotype_attr="${_fc_biotype_attr}" \
       --meta_info="${JOB_PATH}/output/results/star_salmon/"'*/aux_info/meta_info.json' \
       ${paired_flag} \
       --outdir ${JOB_PATH}/output/results \
       --monochrome_logs \
       -name "${_nfjobname}-featurecounts" \
       -c "${INPUT_CONFIG_PATH}/featurecounts_postnfcore.config" \
       ${NEXTFLOW_CONFIG_ARG} \
       -w "${JOB_PATH}/output/work" \
        >${JOB_PATH}/output/post_nextflow.log \
        2>${JOB_PATH}/output/post_nextflow.err

# -profile apptainer \
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
# install_miniforge || fail_job 'install_miniforge' '' $?

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "${PIPELINE_NAME}" "${PIPELINE_VERSION}" || fail_job 'init_conda_env' '' $?

get_settings_from_pipeline_config || fail_job 's' 'get_settings_from_pipeline_config' $?

# nextflow_self_update || true

if ! command -v laxydl >/dev/null 2>&1; then
    update_laxydl || send_error 'update_laxydl' '' $?
fi

####
#### Stage input data ###
####

download_input_data "${INPUT_REFERENCE_PATH}" "reference_genome" || fail_job 'download_input_data' 'Failed to download reference genome' $?

download_input_data "${INPUT_READS_PATH}" "ngs_reads" || fail_job 'download_input_data' 'Failed to download input data' $?

remove_index_reads

set_genome_args

normalize_annotations

get_site_nextflow_config || true

cache_pipeline

cache_fqdemux_pipeline

generate_fqdemux_samplesheet

cd "${JOB_PATH}/output"

send_event "JOB_PIPELINE_STARTING" "Starting demultiplexing pipeline."

run_fqdemux_pipeline

send_event "JOB_PIPELINE_STARTING" "Starting rnaseq pipeline."

run_nextflow

send_event "JOB_PIPELINE_STARTING" "Starting post-rnaseq pipeline."

post_nextflow_pipeline || true

cd "${JOB_PATH}"

# Called by job_done and job_fail_or_cancel, so we don't need this here
# cleanup_nextflow_intermediates || true

# Call job finalization with explicit exit code from the main pipeline command
job_done $EXIT_CODE

# Remove the trap so job_done doesn't get called a second time when the script naturally exits
trap - EXIT
exit 0
