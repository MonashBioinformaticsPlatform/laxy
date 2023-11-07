#!/usr/bin/env nextflow
nextflow.enable.dsl = 2
import groovy.json.JsonOutput

params.bams = file('results/star_salmon/*.bam')
params.annotation = file('reference/genes.gtf.gz')
params.meta_info = file('results/star_salmon/*/aux_info/meta_info.json')
params.paired = true
params.use_annotation_as_is = false
params.outdir = file('results')
//params.scripts_path = workflow.scriptFile.getParent()


process PREPROCESS_ANNOTATION {
    // executor = 'local'
    container = 'quay.io/biocontainers/agat:1.2.0--pl5321hdfd78af_0'
    cpus = 1
    // 10.GB is not enough for Ensembl GRCh38 release 109
    memory = 24.GB

    input:
        path annotation
    output:
        path 'annotation.gxf'
    script:
        """
        if [[ "${params.use_annotation_as_is}" == "true" ]]; then
            if [[ ${annotation} =~ \.gz\$ ]]; then
                gunzip -c ${annotation} >annotation.gxf
            else
                ln -s ${annotation} annotation.gxf
            fi
        else
            agat_sp_webApollo_compliant.pl \
              -g ${annotation} \
              -o annotation.fixed.gff

            agat_convert_sp_gff2gtf.pl \
              --gff annotation.fixed.gff \
              -o annotation.gxf
        fi
        """
}

process GET_SALMON_INFERRED_STRANDEDNESS {
    executor = 'local'
    cpus = 1
    memory = 128.MB
    // happens to contain the jq tool we need ..
    container = 'quay.io/biocontainers/fastq-scan:1.0.1--h4ac6f70_2'

    input:
        path(meta_info_json)
    output:
        stdout

    script:
        """
        # 0=unstranded, 1=forward, 2=reverse
        # We return unstranded if unknown/no match, since this
        # is likely the best choice for featureCounts when
        # strandedness is ambigious.

        jq --raw-output '.library_types[0]' "${meta_info_json}" | \
            awk '{if (\$0 == "U" || \$0 == "IU") {print "0"} \
            else if (\$0 == "SF" || \$0 == "ISF") {print "1"} \
            else if (\$0 == "SR" || \$0 == "ISR") {print "2"} \
            else {printf("%s", "0");} }' || echo -n "0"
        """
}

process FEATURECOUNTS {
    //executor = 'local'

    container = 'quay.io/biocontainers/subread:2.0.1--hed695b0_0'
    cpus = 4
    memory = 16.GB

    publishDir path: "${params.outdir}/featureCounts",
               mode: 'copy',
               failOnError: true

    input:
        tuple val(sample_name), path(bam), path(bai)
        path annotation
        val paired
        val strandedness
    output:
        tuple val(sample_name), path("${sample_name}.counts.star_featureCounts.txt"), emit: counts
        tuple val(sample_name), path("${sample_name}.counts.star_featureCounts.txt.summary"), emit: summary

    script:
        def paired_flag = ' -p '
        if (!paired) {
        paired_flag = ' '
        }

        """
        mkdir tmp

        featureCounts \
            -a "${annotation}" \
            -o "${sample_name}.counts.star_featureCounts.txt" \
            -T ${task.cpus} \
            ${paired_flag} \
            -B \
            -C \
            -Q 10 \
            --tmpDir ./tmp \
            --extraAttributes gene_name,gene_biotype \
            -s ${strandedness.replace('\n', '')} \
            ${bam}

        rm -rf tmp || true
        """
}


process FEATURECOUNTS_MERGE {
    
    container = 'https://depot.galaxyproject.org/singularity/pandas%3A1.5.2'
    cpus = 1
    memory = 1.GB

    publishDir path: "${params.outdir}/featureCounts",
        mode: 'copy',
        failOnError: true

    input:
         // list of [(sample_name, counts_txt), ...] pairs
        val(counts_files)
    output:
        path('counts.star_featureCounts.tsv'), emit: counts

    script:
        """
        ${params.scripts_path}/merge_featurecounts.py --json='${counts_files}' >counts.star_featureCounts.tsv
        """
}


process SALMON_COUNTS_ADD_BIOTYPES {

    container = 'https://depot.galaxyproject.org/singularity/pandas%3A1.5.2'
    cpus = 1
    memory = 1.GB

    publishDir path: "${params.outdir}/${output_dir}",
        mode: 'copy',
        failOnError: true

    input:
        path("counts.star_featureCounts.tsv")
        path(salmon_counts)
        val(output_dir)
    output:
        path("*.biotypes.tsv"), emit: counts

    script:
        //// TODO: Alternatively, use a script in scripts/templates/merge_biotypes.py
        ////       or just put the script verbatim in here as #!/usr/bin/env python
        // template 'merge_biotypes.py'
        """
        # Merge the biotypes from featureCounts into the Salmon counts tables.
        ${params.scripts_path}/merge_biotypes.py \
            counts.star_featureCounts.tsv \
            ${salmon_counts} \
            >"${salmon_counts.getBaseName()}.biotypes.tsv"
        """
}


workflow {
    // We just take the first to infer strandedness here
    // TODO: Pair up each meta_info.json with the corresponding BAM,
    //       apply strandedness per-BAM rather than single value
    meta_info_file = Channel.fromPath(params.meta_info).first()

    // [sample_name, bam, bai]
    bams = Channel.fromPath(params.bams).map { [it.getSimpleName(), it, it + '.bai'] }.view()

    GET_SALMON_INFERRED_STRANDEDNESS(meta_info_file)
    strandedness = GET_SALMON_INFERRED_STRANDEDNESS.out.first()
    strandedness.view { "\nInferred strandedness from Salmon meta_info.json: $it" }


    PREPROCESS_ANNOTATION(params.annotation)
    annotation = PREPROCESS_ANNOTATION.out.first()

    FEATURECOUNTS(bams, annotation, params.paired, strandedness)

    // (sample_name, counts.txt)
    counts = FEATURECOUNTS.out.counts
        .map { [it[0].toString(), it[1].toString()] }
        .collect(flat: false)
        .map { JsonOutput.toJson(it) }
        .view()

    FEATURECOUNTS_MERGE(counts)

    // Common input file with biotypes:
    //   counts.star_featureCounts.tsv
    //
    // Generate biotype versions of:
    //   results/star_salmon/salmon.merged.gene_counts.tsv
    //   results/salmon/salmon.merged.gene_counts.tsv
    //   results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv
    //   results/salmon/salmon.merged.gene_counts_length_scaled.tsv
    //
    // Output filenames - replace .tsv with .biotypes.tsv
    // Put in results/${dir}/

    // Two synchronized channels:
    // - salmon_counts: path to counts output by nf-core/rnaseq
    // - merged_biotypes_publish_dirs: directory in publish dir to put result in (eg 'salmon' or 'star_salmon')

    // TODO: These should probably be a commandline param
    Channel.fromPath(
            [
                "${workflow.launchDir}/results/star_salmon/salmon.merged.gene_counts.tsv",
                "${workflow.launchDir}/results/salmon/salmon.merged.gene_counts.tsv",
                "${workflow.launchDir}/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv",
                "${workflow.launchDir}/results/salmon/salmon.merged.gene_counts_length_scaled.tsv"
            ],
    )
    .tap { salmon_counts }
    .view { "Using counts at path: $it" }
    .map { it.getParent().getBaseName() }
    .tap { merged_biotypes_publish_dirs }
    .view { "Biotypes merged output folder: $it" }

    //merged_biotypes_publish_dirs = Channel.fromList(['star_salmon', 'salmon', 'star_salmon', 'salmon'])

    // nf-core/rnaseq Salmon output does not contain biotypes, so we merge the featureCounts biotypes by gene
    SALMON_COUNTS_ADD_BIOTYPES(
        FEATURECOUNTS_MERGE.out.counts.first(), 
        salmon_counts, 
        merged_biotypes_publish_dirs)
}
