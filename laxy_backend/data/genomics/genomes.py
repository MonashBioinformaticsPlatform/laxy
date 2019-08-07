# This maps reference identifiers, sent via web API requests, to a relative path containing
# the reference genome (iGenomes directory structure), like {id: path}.
# TODO: This should be a default config somewhere, pipeline/plugin specific.
#       Each compute resource should be able to override this setting.
# For Python backend, validation
REFERENCE_GENOME_MAPPINGS = {

    # TODO: Remove this. Temporary Acinetobacter genome until better mechanism for custom genomes is added
    "Acinetobacter_baumannii/Custom/ATCC19606": "Acinetobacter_baumannii/Custom/ATCC19606",

    "Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0": "Aedes_aegypti/NCBI/GCF_002204515.2_AaegL5.0",

    "Arabidopsis_thaliana/Ensembl/TAIR10": "Arabidopsis_thaliana/Ensembl/TAIR10",
    "Arabidopsis_thaliana/Ensembl/TAIR9": "Arabidopsis_thaliana/Ensembl/TAIR9",
    "Arabidopsis_thaliana/NCBI/TAIR10": "Arabidopsis_thaliana/NCBI/TAIR10",
    "Arabidopsis_thaliana/NCBI/build9.1": "Arabidopsis_thaliana/NCBI/build9.1",

    "Bacillus_cereus_ATCC_10987/NCBI/2004-02-13": "Bacillus_cereus_ATCC_10987/NCBI/2004-02-13",

    "Bacillus_subtilis_168/Ensembl/EB2": "Bacillus_subtilis_168/Ensembl/EB2",

    "Bos_taurus/Ensembl/Btau_4.0": "Bos_taurus/Ensembl/Btau_4.0",
    "Bos_taurus/Ensembl/UMD3.1": "Bos_taurus/Ensembl/UMD3.1",
    "Bos_taurus/NCBI/Btau_4.2": "Bos_taurus/NCBI/Btau_4.2",
    "Bos_taurus/NCBI/Btau_4.6.1": "Bos_taurus/NCBI/Btau_4.6.1",
    "Bos_taurus/NCBI/UMD_3.1": "Bos_taurus/NCBI/UMD_3.1",
    "Bos_taurus/NCBI/UMD_3.1.1": "Bos_taurus/NCBI/UMD_3.1.1",
    "Bos_taurus/UCSC/bosTau4": "Bos_taurus/UCSC/bosTau4",
    "Bos_taurus/UCSC/bosTau6": "Bos_taurus/UCSC/bosTau6",
    "Bos_taurus/UCSC/bosTau7": "Bos_taurus/UCSC/bosTau7",
    "Bos_taurus/UCSC/bosTau8": "Bos_taurus/UCSC/bosTau8",

    "Caenorhabditis_elegans/Ensembl/WBcel215": "Caenorhabditis_elegans/Ensembl/WBcel215",
    "Caenorhabditis_elegans/Ensembl/WBcel235": "Caenorhabditis_elegans/Ensembl/WBcel235",
    "Caenorhabditis_elegans/Ensembl/WS210": "Caenorhabditis_elegans/Ensembl/WS210",
    "Caenorhabditis_elegans/Ensembl/WS220": "Caenorhabditis_elegans/Ensembl/WS220",
    "Caenorhabditis_elegans/NCBI/WS190": "Caenorhabditis_elegans/NCBI/WS190",
    "Caenorhabditis_elegans/NCBI/WS195": "Caenorhabditis_elegans/NCBI/WS195",
    "Caenorhabditis_elegans/UCSC/ce10": "Caenorhabditis_elegans/UCSC/ce10",
    "Caenorhabditis_elegans/UCSC/ce6": "Caenorhabditis_elegans/UCSC/ce6",

    "Canis_familiaris/Ensembl/BROADD2": "Canis_familiaris/Ensembl/BROADD2",
    "Canis_familiaris/Ensembl/CanFam3.1": "Canis_familiaris/Ensembl/CanFam3.1",
    "Canis_familiaris/NCBI/build2.1": "Canis_familiaris/NCBI/build2.1",
    "Canis_familiaris/NCBI/build3.1": "Canis_familiaris/NCBI/build3.1",
    "Canis_familiaris/UCSC/canFam2": "Canis_familiaris/UCSC/canFam2",
    "Canis_familiaris/UCSC/canFam3": "Canis_familiaris/UCSC/canFam3",

    "Chelonia_mydas/NCBI/CheMyd_1.0": "Chelonia_mydas/NCBI/CheMyd_1.0",

    "Danio_rerio/Ensembl/GRCz11.97-noalt": "Danio_rerio/Ensembl/GRCz11.97-noalt",
    # "Danio_rerio/Ensembl/GRCz11.97": "Danio_rerio/Ensembl/GRCz11.97",
    "Danio_rerio/Ensembl/GRCz10": "Danio_rerio/Ensembl/GRCz10",
    "Danio_rerio/Ensembl/Zv9": "Danio_rerio/Ensembl/Zv9",
    "Danio_rerio/NCBI/GRCz10": "Danio_rerio/NCBI/GRCz10",
    "Danio_rerio/NCBI/Zv9": "Danio_rerio/NCBI/Zv9",
    "Danio_rerio/UCSC/danRer10": "Danio_rerio/UCSC/danRer10",
    "Danio_rerio/UCSC/danRer7": "Danio_rerio/UCSC/danRer7",

    "Drosophila_melanogaster/Ensembl/BDGP5": "Drosophila_melanogaster/Ensembl/BDGP5",
    "Drosophila_melanogaster/Ensembl/BDGP5.25": "Drosophila_melanogaster/Ensembl/BDGP5.25",
    "Drosophila_melanogaster/Ensembl/BDGP6": "Drosophila_melanogaster/Ensembl/BDGP6",
    "Drosophila_melanogaster/NCBI/build4.1": "Drosophila_melanogaster/NCBI/build4.1",
    "Drosophila_melanogaster/NCBI/build5": "Drosophila_melanogaster/NCBI/build5",
    "Drosophila_melanogaster/NCBI/build5.3": "Drosophila_melanogaster/NCBI/build5.3",
    "Drosophila_melanogaster/NCBI/build5.41": "Drosophila_melanogaster/NCBI/build5.41",
    "Drosophila_melanogaster/UCSC/dm3": "Drosophila_melanogaster/UCSC/dm3",
    "Drosophila_melanogaster/UCSC/dm6": "Drosophila_melanogaster/UCSC/dm6",

    "Enterobacteriophage_lambda/NCBI/1993-04-28": "Enterobacteriophage_lambda/NCBI/1993-04-28",

    "Equus_caballus/Ensembl/EquCab2": "Equus_caballus/Ensembl/EquCab2",
    "Equus_caballus/NCBI/EquCab2.0": "Equus_caballus/NCBI/EquCab2.0",
    "Equus_caballus/UCSC/equCab2": "Equus_caballus/UCSC/equCab2",

    "Escherichia_coli_K_12_DH10B/Ensembl/EB1": "Escherichia_coli_K_12_DH10B/Ensembl/EB1",
    "Escherichia_coli_K_12_DH10B/NCBI/2008-03-17": "Escherichia_coli_K_12_DH10B/NCBI/2008-03-17",

    "Escherichia_coli_K_12_MG1655/NCBI/2001-10-15": "Escherichia_coli_K_12_MG1655/NCBI/2001-10-15",

    "Gallus_gallus/Ensembl/Galgal4": "Gallus_gallus/Ensembl/Galgal4",
    "Gallus_gallus/Ensembl/WASHUC2": "Gallus_gallus/Ensembl/WASHUC2",
    "Gallus_gallus/NCBI/build2.1": "Gallus_gallus/NCBI/build2.1",
    "Gallus_gallus/NCBI/build3.1": "Gallus_gallus/NCBI/build3.1",
    "Gallus_gallus/UCSC/galGal3": "Gallus_gallus/UCSC/galGal3",
    "Gallus_gallus/UCSC/galGal4": "Gallus_gallus/UCSC/galGal4",

    "Glycine_max/Ensembl/Gm01": "Glycine_max/Ensembl/Gm01",

    "Homo_sapiens/Ensembl/GRCh38": "Homo_sapiens/Ensembl/GRCh38",
    "Homo_sapiens/Ensembl/GRCh37": "Homo_sapiens/Ensembl/GRCh37",
    "Homo_sapiens/NCBI/GRCh38": "Homo_sapiens/NCBI/GRCh38",
    "Homo_sapiens/NCBI/GRCh38Decoy": "Homo_sapiens/NCBI/GRCh38Decoy",
    "Homo_sapiens/NCBI/build36.3": "Homo_sapiens/NCBI/build36.3",
    "Homo_sapiens/NCBI/build37.1": "Homo_sapiens/NCBI/build37.1",
    "Homo_sapiens/NCBI/build37.2": "Homo_sapiens/NCBI/build37.2",
    "Homo_sapiens/UCSC/hg18": "Homo_sapiens/UCSC/hg18",
    "Homo_sapiens/UCSC/hg19": "Homo_sapiens/UCSC/hg19",
    "Homo_sapiens/UCSC/hg38": "Homo_sapiens/UCSC/hg38",

    "Macaca_mulatta/Ensembl/Mmul_1": "Macaca_mulatta/Ensembl/Mmul_1",

    "Mus_musculus/Ensembl/GRCm38": "Mus_musculus/Ensembl/GRCm38",
    "Mus_musculus/Ensembl/NCBIM37": "Mus_musculus/Ensembl/NCBIM37",
    "Mus_musculus/NCBI/GRCm38": "Mus_musculus/NCBI/GRCm38",
    "Mus_musculus/NCBI/build37.1": "Mus_musculus/NCBI/build37.1",
    "Mus_musculus/NCBI/build37.2": "Mus_musculus/NCBI/build37.2",
    "Mus_musculus/UCSC/mm10": "Mus_musculus/UCSC/mm10",
    "Mus_musculus/UCSC/mm9": "Mus_musculus/UCSC/mm9",

    "Mycobacterium_tuberculosis_H37RV/Ensembl/H37Rv.EB1": "Mycobacterium_tuberculosis_H37RV/Ensembl/H37Rv.EB1",
    "Mycobacterium_tuberculosis_H37RV/NCBI/2001-09-07": "Mycobacterium_tuberculosis_H37RV/NCBI/2001-09-07",

    "Oryza_sativa_japonica/Ensembl/IRGSP-1.0": "Oryza_sativa_japonica/Ensembl/IRGSP-1.0",
    "Oryza_sativa_japonica/Ensembl/MSU6": "Oryza_sativa_japonica/Ensembl/MSU6",

    "Pan_troglodytes/Ensembl/CHIMP2.1": "Pan_troglodytes/Ensembl/CHIMP2.1",
    "Pan_troglodytes/Ensembl/CHIMP2.1.4": "Pan_troglodytes/Ensembl/CHIMP2.1.4",
    "Pan_troglodytes/NCBI/build2.1": "Pan_troglodytes/NCBI/build2.1",
    "Pan_troglodytes/NCBI/build3.1": "Pan_troglodytes/NCBI/build3.1",
    "Pan_troglodytes/UCSC/panTro2": "Pan_troglodytes/UCSC/panTro2",
    "Pan_troglodytes/UCSC/panTro3": "Pan_troglodytes/UCSC/panTro3",
    "Pan_troglodytes/UCSC/panTro4": "Pan_troglodytes/UCSC/panTro4",

    "PhiX/Illumina/RTA": "PhiX/Illumina/RTA",
    "PhiX/NCBI/1993-04-28": "PhiX/NCBI/1993-04-28",

    "Pseudomonas_aeruginosa_PAO1/NCBI/2000-09-13": "Pseudomonas_aeruginosa_PAO1/NCBI/2000-09-13",

    "Rattus_norvegicus/Ensembl/RGSC3.4": "Rattus_norvegicus/Ensembl/RGSC3.4",
    "Rattus_norvegicus/Ensembl/Rnor_5.0": "Rattus_norvegicus/Ensembl/Rnor_5.0",
    "Rattus_norvegicus/Ensembl/Rnor_6.0": "Rattus_norvegicus/Ensembl/Rnor_6.0",
    "Rattus_norvegicus/NCBI/RGSC_v3.4": "Rattus_norvegicus/NCBI/RGSC_v3.4",
    "Rattus_norvegicus/NCBI/Rnor_5.0": "Rattus_norvegicus/NCBI/Rnor_5.0",
    "Rattus_norvegicus/NCBI/Rnor_6.0": "Rattus_norvegicus/NCBI/Rnor_6.0",
    "Rattus_norvegicus/UCSC/rn4": "Rattus_norvegicus/UCSC/rn4",
    "Rattus_norvegicus/UCSC/rn5": "Rattus_norvegicus/UCSC/rn5",
    "Rattus_norvegicus/UCSC/rn6": "Rattus_norvegicus/UCSC/rn6",

    "Rhodobacter_sphaeroides_2.4.1/NCBI/2005-10-07": "Rhodobacter_sphaeroides_2.4.1/NCBI/2005-10-07",

    "Saccharomyces_cerevisiae/Ensembl/EF2": "Saccharomyces_cerevisiae/Ensembl/EF2",
    "Saccharomyces_cerevisiae/Ensembl/EF3": "Saccharomyces_cerevisiae/Ensembl/EF3",
    "Saccharomyces_cerevisiae/Ensembl/EF4": "Saccharomyces_cerevisiae/Ensembl/EF4",
    "Saccharomyces_cerevisiae/Ensembl/R64-1-1": "Saccharomyces_cerevisiae/Ensembl/R64-1-1",
    "Saccharomyces_cerevisiae/NCBI/build2.1": "Saccharomyces_cerevisiae/NCBI/build2.1",
    "Saccharomyces_cerevisiae/NCBI/build3.1": "Saccharomyces_cerevisiae/NCBI/build3.1",
    "Saccharomyces_cerevisiae/UCSC/sacCer2": "Saccharomyces_cerevisiae/UCSC/sacCer2",
    "Saccharomyces_cerevisiae/UCSC/sacCer3": "Saccharomyces_cerevisiae/UCSC/sacCer3",

    "Schizosaccharomyces_pombe/Ensembl/EF1": "Schizosaccharomyces_pombe/Ensembl/EF1",
    "Schizosaccharomyces_pombe/Ensembl/EF2": "Schizosaccharomyces_pombe/Ensembl/EF2",

    "Sorangium_cellulosum_So_ce_56/NCBI/2007-11-27": "Sorangium_cellulosum_So_ce_56/NCBI/2007-11-27",

    "Sorghum_bicolor/Ensembl/Sbi1": "Sorghum_bicolor/Ensembl/Sbi1",

    "Staphylococcus_aureus_NCTC_8325/NCBI/2006-02-13": "Staphylococcus_aureus_NCTC_8325/NCBI/2006-02-13",

    "Sus_scrofa/Ensembl/Sscrofa10.2": "Sus_scrofa/Ensembl/Sscrofa10.2",
    "Sus_scrofa/Ensembl/Sscrofa9": "Sus_scrofa/Ensembl/Sscrofa9",
    "Sus_scrofa/NCBI/Sscrofa10": "Sus_scrofa/NCBI/Sscrofa10",
    "Sus_scrofa/NCBI/Sscrofa10.2": "Sus_scrofa/NCBI/Sscrofa10.2",
    "Sus_scrofa/NCBI/Sscrofa9.2": "Sus_scrofa/NCBI/Sscrofa9.2",
    "Sus_scrofa/UCSC/susScr2": "Sus_scrofa/UCSC/susScr2",
    "Sus_scrofa/UCSC/susScr3": "Sus_scrofa/UCSC/susScr3",

    "Zea_mays/Ensembl/AGPv2": "Zea_mays/Ensembl/AGPv2",
    "Zea_mays/Ensembl/AGPv3": "Zea_mays/Ensembl/AGPv3",
}
