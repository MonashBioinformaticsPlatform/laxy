# flake8: noqa
# Reference genomes: each key is the genome id (API / job parameter). Each value must include:
#   "location" — iGenomes-style relative path under the references root, or later an https/ftp URL; not
#   assumed to equal the id. Other keys are returned by GET /api/v1/genomes/ (recommended, files, tags, …).
# TODO: This should be default config somewhere, pipeline/plugin specific.
#       Each compute resource should be able to override this setting.
REFERENCE_GENOMES = {
    'Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0': {'location': 'Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0'},
    'Aedes_aegypti/VectorBase/AaegL5.2': {
        'location': 'Aedes_aegypti/VectorBase/AaegL5.2',
        'recommended': True,
    },
    'Arabidopsis_thaliana/Ensembl/TAIR10': {'location': 'Arabidopsis_thaliana/Ensembl/TAIR10'},
    'Arabidopsis_thaliana/Ensembl/TAIR9': {'location': 'Arabidopsis_thaliana/Ensembl/TAIR9'},
    'Arabidopsis_thaliana/NCBI/TAIR10': {'location': 'Arabidopsis_thaliana/NCBI/TAIR10'},
    'Arabidopsis_thaliana/NCBI/build9.1': {'location': 'Arabidopsis_thaliana/NCBI/build9.1'},
    'Bacillus_cereus_ATCC_10987/NCBI/2004-02-13': {'location': 'Bacillus_cereus_ATCC_10987/NCBI/2004-02-13'},
    'Bacillus_subtilis_168/Ensembl/EB2': {'location': 'Bacillus_subtilis_168/Ensembl/EB2'},
    'Bos_taurus/Ensembl/Btau_4.0': {'location': 'Bos_taurus/Ensembl/Btau_4.0'},
    'Bos_taurus/Ensembl/UMD3.1': {'location': 'Bos_taurus/Ensembl/UMD3.1'},
    'Bos_taurus/NCBI/Btau_4.2': {'location': 'Bos_taurus/NCBI/Btau_4.2'},
    'Bos_taurus/NCBI/Btau_4.6.1': {'location': 'Bos_taurus/NCBI/Btau_4.6.1'},
    'Bos_taurus/NCBI/UMD_3.1': {'location': 'Bos_taurus/NCBI/UMD_3.1'},
    'Bos_taurus/NCBI/UMD_3.1.1': {'location': 'Bos_taurus/NCBI/UMD_3.1.1'},
    'Bos_taurus/UCSC/bosTau4': {'location': 'Bos_taurus/UCSC/bosTau4'},
    'Bos_taurus/UCSC/bosTau6': {'location': 'Bos_taurus/UCSC/bosTau6'},
    'Bos_taurus/UCSC/bosTau7': {'location': 'Bos_taurus/UCSC/bosTau7'},
    'Bos_taurus/UCSC/bosTau8': {'location': 'Bos_taurus/UCSC/bosTau8'},
    'Caenorhabditis_elegans/Ensembl/WBcel215': {'location': 'Caenorhabditis_elegans/Ensembl/WBcel215'},
    'Caenorhabditis_elegans/Ensembl/WBcel235': {'location': 'Caenorhabditis_elegans/Ensembl/WBcel235'},
    'Caenorhabditis_elegans/Ensembl/WS210': {'location': 'Caenorhabditis_elegans/Ensembl/WS210'},
    'Caenorhabditis_elegans/Ensembl/WS220': {'location': 'Caenorhabditis_elegans/Ensembl/WS220'},
    'Caenorhabditis_elegans/NCBI/WS190': {'location': 'Caenorhabditis_elegans/NCBI/WS190'},
    'Caenorhabditis_elegans/NCBI/WS195': {'location': 'Caenorhabditis_elegans/NCBI/WS195'},
    'Caenorhabditis_elegans/UCSC/ce10': {'location': 'Caenorhabditis_elegans/UCSC/ce10'},
    'Caenorhabditis_elegans/UCSC/ce6': {'location': 'Caenorhabditis_elegans/UCSC/ce6'},
    'Canis_familiaris/Ensembl/BROADD2': {'location': 'Canis_familiaris/Ensembl/BROADD2'},
    'Canis_familiaris/Ensembl/CanFam3.1': {'location': 'Canis_familiaris/Ensembl/CanFam3.1'},
    'Canis_familiaris/NCBI/build2.1': {'location': 'Canis_familiaris/NCBI/build2.1'},
    'Canis_familiaris/NCBI/build3.1': {'location': 'Canis_familiaris/NCBI/build3.1'},
    'Canis_familiaris/UCSC/canFam2': {'location': 'Canis_familiaris/UCSC/canFam2'},
    'Canis_familiaris/UCSC/canFam3': {'location': 'Canis_familiaris/UCSC/canFam3'},
    'Chelonia_mydas/NCBI/CheMyd_1.0': {'location': 'Chelonia_mydas/NCBI/CheMyd_1.0'},
    'Danio_rerio/Ensembl/GRCz11.97-noalt': {
        'location': 'Danio_rerio/Ensembl/GRCz11.97-noalt',
        'recommended': True,
    },
    'Danio_rerio/Ensembl/GRCz10': {'location': 'Danio_rerio/Ensembl/GRCz10'},
    'Danio_rerio/Ensembl/Zv9': {'location': 'Danio_rerio/Ensembl/Zv9'},
    'Danio_rerio/NCBI/GRCz10': {'location': 'Danio_rerio/NCBI/GRCz10'},
    'Danio_rerio/NCBI/Zv9': {'location': 'Danio_rerio/NCBI/Zv9'},
    'Danio_rerio/UCSC/danRer10': {'location': 'Danio_rerio/UCSC/danRer10'},
    'Danio_rerio/UCSC/danRer7': {'location': 'Danio_rerio/UCSC/danRer7'},
    'Drosophila_melanogaster/Ensembl/BDGP5': {'location': 'Drosophila_melanogaster/Ensembl/BDGP5'},
    'Drosophila_melanogaster/Ensembl/BDGP5.25': {'location': 'Drosophila_melanogaster/Ensembl/BDGP5.25'},
    'Drosophila_melanogaster/Ensembl/BDGP6': {'location': 'Drosophila_melanogaster/Ensembl/BDGP6'},
    'Drosophila_melanogaster/NCBI/build4.1': {'location': 'Drosophila_melanogaster/NCBI/build4.1'},
    'Drosophila_melanogaster/NCBI/build5': {'location': 'Drosophila_melanogaster/NCBI/build5'},
    'Drosophila_melanogaster/NCBI/build5.3': {'location': 'Drosophila_melanogaster/NCBI/build5.3'},
    'Drosophila_melanogaster/NCBI/build5.41': {'location': 'Drosophila_melanogaster/NCBI/build5.41'},
    'Drosophila_melanogaster/UCSC/dm3': {'location': 'Drosophila_melanogaster/UCSC/dm3'},
    'Drosophila_melanogaster/UCSC/dm6': {'location': 'Drosophila_melanogaster/UCSC/dm6'},
    'Enterobacteriophage_lambda/NCBI/1993-04-28': {'location': 'Enterobacteriophage_lambda/NCBI/1993-04-28'},
    'Equus_caballus/Ensembl/EquCab2': {'location': 'Equus_caballus/Ensembl/EquCab2'},
    'Equus_caballus/NCBI/EquCab2.0': {'location': 'Equus_caballus/NCBI/EquCab2.0'},
    'Equus_caballus/UCSC/equCab2': {'location': 'Equus_caballus/UCSC/equCab2'},
    'Escherichia_coli/Ensembl/GCA_000019425.1__release-46': {'location': 'Escherichia_coli/Ensembl/GCA_000019425.1__release-46'},
    'Escherichia_coli/Ensembl/GCA_000005845.2__release-46': {'location': 'Escherichia_coli/Ensembl/GCA_000005845.2__release-46'},
    'Gallus_gallus/Ensembl/Galgal4': {'location': 'Gallus_gallus/Ensembl/Galgal4'},
    'Gallus_gallus/Ensembl/WASHUC2': {'location': 'Gallus_gallus/Ensembl/WASHUC2'},
    'Gallus_gallus/NCBI/build2.1': {'location': 'Gallus_gallus/NCBI/build2.1'},
    'Gallus_gallus/NCBI/build3.1': {'location': 'Gallus_gallus/NCBI/build3.1'},
    'Gallus_gallus/UCSC/galGal3': {'location': 'Gallus_gallus/UCSC/galGal3'},
    'Gallus_gallus/UCSC/galGal4': {'location': 'Gallus_gallus/UCSC/galGal4'},
    'Glycine_max/Ensembl/Gm01': {'location': 'Glycine_max/Ensembl/Gm01'},
    'Homo_sapiens/Ensembl/GRCh38.release-109': {
        'location': 'Homo_sapiens/Ensembl/GRCh38.release-109',
        'recommended': True,
        'identifiers': {
            'genbank': 'GCA_000001405.28',
            'assembly_name': 'GRCh38.p13',
        },
        'source': 'http://Feb2023.archive.ensembl.org/Homo_sapiens/Info/Annotation',
        'files': [
            {
                'location': 'https://ftp.ensembl.org/pub/release-109/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna_sm.primary_assembly.fa.gz',
                'name': 'Homo_sapiens.GRCh38.dna_sm.primary_assembly.fa.gz',
                'checksum': 'md5:239580e6119c7b16865d934f78b20a08',
                'type_tags': [
                    'fasta',
                ],
            },
            {
                'location': 'https://ftp.ensembl.org/pub/release-109/gtf/homo_sapiens/Homo_sapiens.GRCh38.109.gtf.gz',
                'name': 'Homo_sapiens.GRCh38.109.gtf.gz',
                'checksum': 'md5:e35a6f36d6a03d1b673659f72f1fbb3b',
                'type_tags': [
                    'gtf',
                    'annotation',
                ],
            },
        ],
        'tags': [
            'external',
            'rnaseq',
        ],
    },
    'Homo_sapiens/Ensembl/GRCh38': {'location': 'Homo_sapiens/Ensembl/GRCh38'},
    'Homo_sapiens/Ensembl/GRCh37': {'location': 'Homo_sapiens/Ensembl/GRCh37'},
    'Homo_sapiens/NCBI/GRCh38': {'location': 'Homo_sapiens/NCBI/GRCh38'},
    'Homo_sapiens/NCBI/GRCh38Decoy': {'location': 'Homo_sapiens/NCBI/GRCh38Decoy'},
    'Homo_sapiens/NCBI/build36.3': {'location': 'Homo_sapiens/NCBI/build36.3'},
    'Homo_sapiens/NCBI/build37.1': {'location': 'Homo_sapiens/NCBI/build37.1'},
    'Homo_sapiens/NCBI/build37.2': {'location': 'Homo_sapiens/NCBI/build37.2'},
    'Homo_sapiens/UCSC/hg18': {'location': 'Homo_sapiens/UCSC/hg18'},
    'Homo_sapiens/UCSC/hg19': {'location': 'Homo_sapiens/UCSC/hg19'},
    'Homo_sapiens/UCSC/hg38': {'location': 'Homo_sapiens/UCSC/hg38'},
    'Macaca_mulatta/Ensembl/Mmul_1': {'location': 'Macaca_mulatta/Ensembl/Mmul_1'},
    'Mus_musculus/Ensembl/GRCm39.release-109': {
        'location': 'Mus_musculus/Ensembl/GRCm39.release-109',
        'recommended': True,
        'identifiers': {
            'genbank': 'GCA_000001635.9',
            'assembly_name': 'GRCm39',
        },
        'source': 'http://Feb2023.archive.ensembl.org/Mus_musculus/Info/Annotation',
        'files': [
            {
                'location': 'https://ftp.ensembl.org/pub/release-109/fasta/mus_musculus/dna/Mus_musculus.GRCm39.dna_sm.primary_assembly.fa.gz',
                'name': 'Mus_musculus.GRCm39.dna_sm.primary_assembly.fa.gz',
                'checksum': 'md5:',
                'type_tags': [
                    'fasta',
                ],
            },
            {
                'location': 'https://ftp.ensembl.org/pub/release-109/gtf/mus_musculus/Mus_musculus.GRCm39.109.gtf.gz',
                'name': 'Mus_musculus.GRCm39.109.gtf.gz',
                'checksum': 'md5:',
                'type_tags': [
                    'gtf',
                    'annotation',
                ],
            },
        ],
        'tags': [
            'external',
            'rnaseq',
        ],
    },
    'Mus_musculus/Ensembl/GRCm38.release-102': {
        'location': 'Mus_musculus/Ensembl/GRCm38.release-102',
        'identifiers': {
            'genbank': 'GCA_000001635.8',
            'assembly_name': 'GRCm38',
        },
        'source': 'http://nov2020.archive.ensembl.org/Mus_musculus/Info/Annotation',
        'files': [
            {
                'location': 'https://ftp.ensembl.org/pub/release-102/fasta/mus_musculus/dna/Mus_musculus.GRCm38.dna_sm.primary_assembly.fa.gz',
                'name': 'Mus_musculus.GRCm38.dna_sm.primary_assembly.fa.gz',
                'checksum': 'md5:',
                'type_tags': [
                    'fasta',
                ],
            },
            {
                'location': 'https://ftp.ensembl.org/pub/release-102/gtf/mus_musculus/Mus_musculus.GRCm38.102.gtf.gz',
                'name': 'Mus_musculus.GRCm38.102.gtf.gz',
                'checksum': 'md5:',
                'type_tags': [
                    'gtf',
                    'annotation',
                ],
            },
        ],
        'tags': [
            'external',
            'rnaseq',
        ],
    },
    'Mus_musculus/Ensembl/GRCm38': {
        'location': 'Mus_musculus/Ensembl/GRCm38',
        'recommended': True,
    },
    'Mus_musculus/Ensembl/NCBIM37': {'location': 'Mus_musculus/Ensembl/NCBIM37'},
    'Mus_musculus/NCBI/GRCm38': {'location': 'Mus_musculus/NCBI/GRCm38'},
    'Mus_musculus/NCBI/build37.1': {'location': 'Mus_musculus/NCBI/build37.1'},
    'Mus_musculus/NCBI/build37.2': {'location': 'Mus_musculus/NCBI/build37.2'},
    'Mus_musculus/UCSC/mm10': {'location': 'Mus_musculus/UCSC/mm10'},
    'Mus_musculus/UCSC/mm9': {'location': 'Mus_musculus/UCSC/mm9'},
    'Mycobacterium_tuberculosis_H37RV/Ensembl/H37Rv.EB1': {'location': 'Mycobacterium_tuberculosis_H37RV/Ensembl/H37Rv.EB1'},
    'Mycobacterium_tuberculosis_H37RV/NCBI/2001-09-07': {'location': 'Mycobacterium_tuberculosis_H37RV/NCBI/2001-09-07'},
    'Oryza_sativa_japonica/Ensembl/IRGSP-1.0': {'location': 'Oryza_sativa_japonica/Ensembl/IRGSP-1.0'},
    'Oryza_sativa_japonica/Ensembl/MSU6': {'location': 'Oryza_sativa_japonica/Ensembl/MSU6'},
    'Pan_troglodytes/Ensembl/CHIMP2.1': {'location': 'Pan_troglodytes/Ensembl/CHIMP2.1'},
    'Pan_troglodytes/Ensembl/CHIMP2.1.4': {'location': 'Pan_troglodytes/Ensembl/CHIMP2.1.4'},
    'Pan_troglodytes/NCBI/build2.1': {'location': 'Pan_troglodytes/NCBI/build2.1'},
    'Pan_troglodytes/NCBI/build3.1': {'location': 'Pan_troglodytes/NCBI/build3.1'},
    'Pan_troglodytes/UCSC/panTro2': {'location': 'Pan_troglodytes/UCSC/panTro2'},
    'Pan_troglodytes/UCSC/panTro3': {'location': 'Pan_troglodytes/UCSC/panTro3'},
    'Pan_troglodytes/UCSC/panTro4': {'location': 'Pan_troglodytes/UCSC/panTro4'},
    'PhiX/Illumina/RTA': {'location': 'PhiX/Illumina/RTA'},
    'PhiX/NCBI/1993-04-28': {'location': 'PhiX/NCBI/1993-04-28'},
    'Plasmodium_falciparum/PlasmoDB/3D7-release-39': {'location': 'Plasmodium_falciparum/PlasmoDB/3D7-release-39'},
    'Pseudomonas_aeruginosa_PAO1/NCBI/2000-09-13': {'location': 'Pseudomonas_aeruginosa_PAO1/NCBI/2000-09-13'},
    'Rattus_norvegicus/Ensembl/RGSC3.4': {'location': 'Rattus_norvegicus/Ensembl/RGSC3.4'},
    'Rattus_norvegicus/Ensembl/Rnor_5.0': {'location': 'Rattus_norvegicus/Ensembl/Rnor_5.0'},
    'Rattus_norvegicus/Ensembl/Rnor_6.0': {'location': 'Rattus_norvegicus/Ensembl/Rnor_6.0'},
    'Rattus_norvegicus/NCBI/RGSC_v3.4': {'location': 'Rattus_norvegicus/NCBI/RGSC_v3.4'},
    'Rattus_norvegicus/NCBI/Rnor_5.0': {'location': 'Rattus_norvegicus/NCBI/Rnor_5.0'},
    'Rattus_norvegicus/NCBI/Rnor_6.0': {'location': 'Rattus_norvegicus/NCBI/Rnor_6.0'},
    'Rattus_norvegicus/UCSC/rn4': {'location': 'Rattus_norvegicus/UCSC/rn4'},
    'Rattus_norvegicus/UCSC/rn5': {'location': 'Rattus_norvegicus/UCSC/rn5'},
    'Rattus_norvegicus/UCSC/rn6': {'location': 'Rattus_norvegicus/UCSC/rn6'},
    'Rhodobacter_sphaeroides_2.4.1/NCBI/2005-10-07': {'location': 'Rhodobacter_sphaeroides_2.4.1/NCBI/2005-10-07'},
    'Saccharomyces_cerevisiae/Ensembl/EF2': {'location': 'Saccharomyces_cerevisiae/Ensembl/EF2'},
    'Saccharomyces_cerevisiae/Ensembl/EF3': {'location': 'Saccharomyces_cerevisiae/Ensembl/EF3'},
    'Saccharomyces_cerevisiae/Ensembl/EF4': {'location': 'Saccharomyces_cerevisiae/Ensembl/EF4'},
    'Saccharomyces_cerevisiae/Ensembl/R64-1-1': {
        'location': 'Saccharomyces_cerevisiae/Ensembl/R64-1-1',
        'recommended': True,
    },
    'Saccharomyces_cerevisiae/NCBI/build2.1': {'location': 'Saccharomyces_cerevisiae/NCBI/build2.1'},
    'Saccharomyces_cerevisiae/NCBI/build3.1': {'location': 'Saccharomyces_cerevisiae/NCBI/build3.1'},
    'Saccharomyces_cerevisiae/UCSC/sacCer2': {'location': 'Saccharomyces_cerevisiae/UCSC/sacCer2'},
    'Saccharomyces_cerevisiae/UCSC/sacCer3': {'location': 'Saccharomyces_cerevisiae/UCSC/sacCer3'},
    'Schizosaccharomyces_pombe/Ensembl/EF1': {'location': 'Schizosaccharomyces_pombe/Ensembl/EF1'},
    'Schizosaccharomyces_pombe/Ensembl/EF2': {'location': 'Schizosaccharomyces_pombe/Ensembl/EF2'},
    'Sorangium_cellulosum_So_ce_56/NCBI/2007-11-27': {'location': 'Sorangium_cellulosum_So_ce_56/NCBI/2007-11-27'},
    'Sorghum_bicolor/Ensembl/Sbi1': {'location': 'Sorghum_bicolor/Ensembl/Sbi1'},
    'Staphylococcus_aureus_NCTC_8325/NCBI/2006-02-13': {'location': 'Staphylococcus_aureus_NCTC_8325/NCBI/2006-02-13'},
    'Sus_scrofa/Ensembl/Sscrofa10.2': {'location': 'Sus_scrofa/Ensembl/Sscrofa10.2'},
    'Sus_scrofa/Ensembl/Sscrofa9': {'location': 'Sus_scrofa/Ensembl/Sscrofa9'},
    'Sus_scrofa/NCBI/Sscrofa10': {'location': 'Sus_scrofa/NCBI/Sscrofa10'},
    'Sus_scrofa/NCBI/Sscrofa10.2': {'location': 'Sus_scrofa/NCBI/Sscrofa10.2'},
    'Sus_scrofa/NCBI/Sscrofa9.2': {'location': 'Sus_scrofa/NCBI/Sscrofa9.2'},
    'Sus_scrofa/UCSC/susScr2': {'location': 'Sus_scrofa/UCSC/susScr2'},
    'Sus_scrofa/UCSC/susScr3': {'location': 'Sus_scrofa/UCSC/susScr3'},
    'Zea_mays/Ensembl/AGPv2': {'location': 'Zea_mays/Ensembl/AGPv2'},
    'Zea_mays/Ensembl/AGPv3': {'location': 'Zea_mays/Ensembl/AGPv3'},
}


def reference_genome_location(genome_id: str) -> str:
    """Where this reference lives: relative path under references, or a URL."""
    return REFERENCE_GENOMES[genome_id]["location"]


def organism_label_from_genome_id(genome_id: str) -> str:
    parts = genome_id.split("/")
    if len(parts) >= 2:
        return parts[0].replace("_", " ")
    return genome_id


def reference_genomes_for_api() -> list[dict]:
    """Records for GET /api/v1/genomes/ (excludes internal ``location``)."""
    rows: list[dict] = []
    for genome_id, meta in REFERENCE_GENOMES.items():
        row: dict = {
            "id": genome_id,
            "organism": organism_label_from_genome_id(genome_id),
        }
        for key, value in meta.items():
            if key == "location":
                continue
            row[key] = value
        rows.append(row)
    return rows
