#!/bin/bash

DRYRUN=no
SLURM_ACCOUNT=$(sacctmgr --parsable2 show user -s ${USER} | tail -1 | cut -f 2 -d '|')
REF_BASEPATH=/references/iGenomes

function make_index() {
    ref_subpath="${1}"
    cpus="${2:-16}"
    mem="${3:-64G}"
    hours="${4:-2}"
    basedir="${REF_BASEPATH}"/"${ref_subpath}"
    index_dir="${basedir}"/Sequence/STARIndex
    fasta="${basedir}/Sequence/WholeGenomeFasta/genome.fa"
    extra_star_args="${5:-}"
    SBATCH="sbatch --job-name='${ref_subpath}' --account=${SLURM_ACCOUNT} --time=0-${hours}:00 --cpus-per-task=${cpus} --mem=${mem} --wrap="
    STAR_CMD="STAR ${extra_star_args} --runThreadN 16 --runMode genomeGenerate --genomeDir ${index_dir} --genomeFastaFiles ${fasta} >${index_dir}/Log.out 2>${index_dir}/Log.err"
    
    mkdir -p "${index_dir}"
    
    if [[ ! -f ${index_dir}/SA ]]; then
        # pushd "${index_dir}"
        echo "${SBATCH}"\""${STAR_CMD}"\"
        if [[ "${DRYRUN}" != "yes" ]]; then
          eval "${SBATCH}"\""${STAR_CMD}"\"
          sleep 5
        fi
        # popd
    else
      echo "${index_dir}/SA exists, skipping."
    fi
}


make_index Homo_sapiens/Ensembl/GRCh38
make_index Homo_sapiens/UCSC/hg19
make_index Homo_sapiens/UCSC/hg38

make_index Saccharomyces_cerevisiae/Ensembl/R64-1-1       4  16G 1 "--genomeSAindexNbases 10"
make_index Caenorhabditis_elegans/Ensembl/WBcel235        8  32G 1 "--genomeSAindexNbases 12"
make_index Escherichia_coli_K_12_DH10B/Ensembl/EB1        4  16G 1 "--genomeSAindexNbases 10"

make_index Mus_musculus/Ensembl/GRCm38                   24  128G 3
make_index Mus_musculus/NCBI/GRCm38                      24  128G 3

make_index Acinetobacter_baumannii/Custom/AB307-0294      4  16G 1 "--genomeSAindexNbases 9"
make_index Acinetobacter_baumannii/Custom/ATCC19606       4  16G 1 "--genomeSAindexNbases 10"

make_index Aedes_aegypti/VectorBase/AaegL5.2             24  128G 3
make_index Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0   24  128G 3

make_index Danio_rerio/Ensembl/GRCz11.97                 24 192G 3 "--limitGenomeGenerateRAM 151278166400"
make_index Danio_rerio/Ensembl/GRCz11.97-noalt           24 192G 3 "--limitGenomeGenerateRAM 151278166400"

make_index Chelonia_mydas/NCBI/CheMyd_1.0-exon-contigs   16  64G 3 "--genomeChrBinNbits=14"

make_index Plasmodium_falciparum/PlasmoDB/3D7-release-39  4 16G 1 "--genomeSAindexNbases 11"
