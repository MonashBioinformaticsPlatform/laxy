#!/usr/bin/env bash

# Source after laxy.lib.sh (send_event, fail_job). Requires env.sh (AGAT_CONTAINER_IMAGE, JOB_PATH).
function agat_normalize_annotation() {
    # Standardise user-supplied GFF/GTF with AGAT into a clean GFF3 with
    # proper ID=/Parent= hierarchy so nf-core/rnaseq GFFREAD can build a GTF.
    # The uploaded file in ${dir} is left in place; ANNOTATION_FILE is set to
    # the new AGAT output for the pipeline only.
    #
    # Output: ${dir}/annotation.agat.gff.gz (compressed GFF3, .gff.gz so that
    # nf-core treats it as GFF without further renaming).
    [[ "${USING_CUSTOM_REFERENCE}" == "yes" ]] || return 0
    [[ -n "${ANNOTATION_FILE:-}" && -f "${ANNOTATION_FILE}" ]] || return 0
    [[ -n "${AGAT_CONTAINER_IMAGE:-}" ]] || return 0

    mkdir -p "${JOB_PATH}/output"


    local _in="${ANNOTATION_FILE}"
    local _dir
    _dir="$(dirname "${_in}")"
    local _work
    _work="$(mktemp -d)"
    local _staged="${_work}/$(basename "${_in}")"
    local _out_plain="${_dir}/annotation.agat.gff"
    local _out_gz="${_dir}/annotation.agat.gff.gz"

    cp -L "${_in}" "${_staged}"

    # AGAT uses Parallel::ForkManager / File::Temp under $TMPDIR. The job's TMPDIR is often under
    # /scratch/tmp/... which is not bind-mounted unless we explicitly -B it; perl then hits a
    # read-only view. Force temps inside _work which is mounted.
    local _tmp_inner="${_work}/agat_tmp"
    mkdir -p "${_tmp_inner}"

    # AGAT also writes an `agat_log_<input>/` directory into the working
    # directory, so set --pwd to the bind-mounted scratch dir as well.
    apptainer exec \
        --env "TMPDIR=${_tmp_inner}" \
        --env "TMP=${_tmp_inner}" \
        --env "TEMP=${_tmp_inner}" \
        --pwd "${_work}" \
        -B "${_dir}" -B "${_work}" \
        "docker://${AGAT_CONTAINER_IMAGE}" \
        agat_convert_sp_gxf2gxf.pl \
            --gff "${_staged}" \
            -o "${_out_plain}" \
        >>"${JOB_PATH}/output/agat.log" 2>&1 \
      || fail_job 'agat_normalize_annotation' 'AGAT GFF normalisation (gxf2gxf) failed' $?

    gzip -nf "${_out_plain}" || fail_job 'agat_normalize_annotation_gzip' '' $?

    export ANNOTATION_FILE="${_out_gz}"
    rm -rf "${_work}"
}

# Verify that the FASTA and the (AGAT-normalised) annotation share at least one
# sequence id. nf-core/rnaseq PREPARE_GENOME:GTF_FILTER runs `filter_gtf.py`
# which removes every GTF/GFF row whose column 1 isn't present as the first
# whitespace-delimited token of a FASTA '>' header, and then errors with
# `All GTF lines removed by filters` if nothing survives. Fail early here with
# a much more actionable message instead of waiting ~10 min for Nextflow to
# discover it. SnapGene `.ape` FASTAs in particular use the SnapGene "name"
# (e.g. `AB307_NCBI_CP001172_CURRENT`) as the FASTA seqid while the annotation
# still references the accession (`CP001172`).
function check_fasta_annotation_seqids() {
    [[ "${USING_CUSTOM_REFERENCE}" == "yes" ]] || return 0
    [[ -n "${GENOME_FASTA:-}" && -f "${GENOME_FASTA}" ]] || return 0
    [[ -n "${ANNOTATION_FILE:-}" && -f "${ANNOTATION_FILE}" ]] || return 0

    local _fasta="${GENOME_FASTA}"
    local _ann="${ANNOTATION_FILE}"

    local -a _fa_ids _ann_ids
    local _cat_fa="cat"
    [[ "${_fasta}" == *.gz ]] && _cat_fa="zcat"
    local _cat_ann="cat"
    [[ "${_ann}" == *.gz ]] && _cat_ann="zcat"

    mapfile -t _fa_ids < <(${_cat_fa} "${_fasta}" 2>/dev/null \
        | awk '/^>/{sub(/^>/,""); split($0,a,/[[:space:]]/); if (a[1] != "") print a[1]}' \
        | sort -u)

    # Skip comment lines, the GFF FASTA section, and any malformed rows.
    mapfile -t _ann_ids < <(${_cat_ann} "${_ann}" 2>/dev/null \
        | awk 'BEGIN{f=0} /^##FASTA/{f=1; next} f==1{next} /^#/{next} NF>=8 && $1 !~ /^[[:space:]]*$/ {print $1}' \
        | sort -u)

    if [[ ${#_fa_ids[@]} -eq 0 ]]; then
        fail_job 'check_fasta_annotation_seqids' "Genome FASTA ${_fasta##*/} appears to contain no '>' headers." 1
    fi
    if [[ ${#_ann_ids[@]} -eq 0 ]]; then
        fail_job 'check_fasta_annotation_seqids' "Annotation ${_ann##*/} has no feature rows with a sequence id in column 1." 1
    fi

    local _overlap
    _overlap=$(comm -12 \
        <(printf '%s\n' "${_fa_ids[@]}") \
        <(printf '%s\n' "${_ann_ids[@]}") \
        | head -n 5)

    if [[ -z "${_overlap}" ]]; then
        local _fa_show _ann_show
        _fa_show=$(printf '%s\n' "${_fa_ids[@]}" | head -n 5 | paste -sd, -)
        _ann_show=$(printf '%s\n' "${_ann_ids[@]}" | head -n 5 | paste -sd, -)
        local _msg="Genome FASTA and annotation use different sequence ids and share no overlap, "
        _msg+="so nf-core/rnaseq would filter out every annotation row. "
        _msg+="FASTA seqids (sample): ${_fa_show}. "
        _msg+="Annotation seqids (sample): ${_ann_show}. "
        _msg+="Rename the FASTA header (or the annotation column 1) so they match, then resubmit."
        send_event "JOB_INFO" "${_msg}" || true
        fail_job 'check_fasta_annotation_seqids' "${_msg}" 1
    fi
}

# Trim a prokaryotic annotation to ANN_FEATURE_TYPE rows and (for GFF3 input)
# expand each kept row into a synthesised transcript+exon+<feature_type>
# hierarchy in GTF format. The output is always GTF, so nf-core/rnaseq's
# PREPARE_GENOME skips its lossy gffread synthesis step (which would drop
# exon rows and gene_id attributes when fed a flat CDS-only GFF3) and the
# annotation flows straight into RSEM, STAR, featureCounts, gtf2bed, and
# CUSTOM_TX2GENE with the gene_id/transcript_id they expect.
#
# Runs AFTER detect_annotation_style.py so ANN_FORMAT / ANN_FEATURE_TYPE /
# ANN_GROUP_FEATURES / ANN_PROKARYOTIC are populated.
#
# Restricted to prokaryotic annotations (ANN_PROKARYOTIC=yes) by design:
#   * It exists to repair malformed prokaryotic inputs (e.g. SnapGene-exported
#     GFF3 with `variation` rows where end<start; CDS-only annotations
#     without ID=/Parent= that make gffread silently emit a 0-row GTF).
#   * Synthesising one transcript+exon per CDS only makes sense for
#     prokaryotes (1 gene = 1 ORF = 1 transcript). Running it on eukaryotic
#     GFF3 would destroy the shared-Parent grouping that RSEM/STAR rely on
#     to reconstruct multi-exon transcripts.
#
# The uploaded file is left in place; the filtered GTF is written alongside it
# and ANNOTATION_FILE / ANN_FORMAT / ANN_GROUP_FEATURES / ANN_BIOTYPE_ATTR are
# re-exported to point at the new GTF.
function filter_annotation_features() {
    [[ "${USING_CUSTOM_REFERENCE}" == "yes" ]] || return 0
    [[ "${ANN_PROKARYOTIC:-no}" == "yes" ]] || return 0
    [[ -n "${ANNOTATION_FILE:-}" && -f "${ANNOTATION_FILE}" ]] || return 0
    [[ -n "${ANN_FEATURE_TYPE:-}" ]] || return 0
    [[ -n "${ANN_FORMAT:-}" ]] || return 0

    local _in="${ANNOTATION_FILE}"
    local _dir _out_gz
    _dir="$(dirname "${_in}")"
    _out_gz="${_dir}/annotation.filtered.gtf.gz"


    mkdir -p "${JOB_PATH}/output"

    python "${INPUT_SCRIPTS_PATH}/filter_annotation_features.py" \
        --input "${_in}" \
        --output "${_out_gz}" \
        --feature-type "${ANN_FEATURE_TYPE}" \
        --format "${ANN_FORMAT}" \
        --prokaryotic "${ANN_PROKARYOTIC}" \
        --group-feature "${ANN_GROUP_FEATURES:-}" \
        >>"${JOB_PATH}/output/annotation_filter.log" 2>&1 \
      || fail_job 'filter_annotation_features' 'feature-type filter failed' $?

    export ANNOTATION_FILE="${_out_gz}"
    # The synthesised GTF uses standard GTF attribute names regardless of
    # what detect_annotation_style.py picked from the original GFF3.
    export ANN_FORMAT="gtf"
    export ANN_GROUP_FEATURES="gene_id"
    export ANN_BIOTYPE_ATTR="gene_biotype"
}
