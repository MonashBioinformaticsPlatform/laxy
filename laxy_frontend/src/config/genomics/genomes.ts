// From https://github.com/ewels/AWS-iGenomes
// Generated by scripts/igenomes_list.py

const available_genomes: ReferenceGenome[] = [
    {'id': 'Homo_sapiens/Ensembl/GRCh38', 'organism': 'Homo sapiens', 'recommended': true},
    {'id': 'Homo_sapiens/Ensembl/GRCh37', 'organism': 'Homo sapiens'},
    {'id': 'Homo_sapiens/NCBI/GRCh38', 'organism': 'Homo sapiens'},
    {'id': 'Homo_sapiens/NCBI/GRCh38Decoy', 'organism': 'Homo sapiens'},
    // {'id': 'Homo_sapiens/NCBI/build36.3', 'organism': 'Homo sapiens'},
    // {'id': 'Homo_sapiens/NCBI/build37.1', 'organism': 'Homo sapiens'},
    {'id': 'Homo_sapiens/NCBI/build37.2', 'organism': 'Homo sapiens'},
    // {'id': 'Homo_sapiens/UCSC/hg18', 'organism': 'Homo sapiens'},
    {'id': 'Homo_sapiens/UCSC/hg19', 'organism': 'Homo sapiens'},
    {'id': 'Homo_sapiens/UCSC/hg38', 'organism': 'Homo sapiens'},

    {'id': 'Mus_musculus/Ensembl/GRCm38', 'organism': 'Mus musculus', 'recommended': true},
    // {'id': 'Mus_musculus/Ensembl/NCBIM37', 'organism': 'Mus musculus'},
    {'id': 'Mus_musculus/NCBI/GRCm38', 'organism': 'Mus musculus'},
    // {'id': 'Mus_musculus/NCBI/build37.1', 'organism': 'Mus musculus'},
    {'id': 'Mus_musculus/NCBI/build37.2', 'organism': 'Mus musculus'},
    {'id': 'Mus_musculus/UCSC/mm10', 'organism': 'Mus musculus'},
    // {'id': 'Mus_musculus/UCSC/mm9', 'organism': 'Mus musculus'},

    {'id': 'Arabidopsis_thaliana/Ensembl/TAIR10', 'organism': 'Arabidopsis thaliana'},
    // {'id': 'Arabidopsis_thaliana/Ensembl/TAIR9', 'organism': 'Arabidopsis thaliana'},
    {'id': 'Arabidopsis_thaliana/NCBI/TAIR10', 'organism': 'Arabidopsis thaliana'},
    {'id': 'Arabidopsis_thaliana/NCBI/build9.1', 'organism': 'Arabidopsis thaliana'},

    // {'id': 'Bacillus_cereus_ATCC_10987/NCBI/2004-02-13', 'organism': 'Bacillus cereus ATCC 10987'},
    // {'id': 'Bacillus_subtilis_168/Ensembl/EB2', 'organism': 'Bacillus subtilis 168'},

    // {'id': 'Bos_taurus/Ensembl/Btau_4.0', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/Ensembl/UMD3.1', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/NCBI/Btau_4.2', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/NCBI/Btau_4.6.1', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/NCBI/UMD_3.1', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/NCBI/UMD_3.1.1', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/UCSC/bosTau4', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/UCSC/bosTau6', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/UCSC/bosTau7', 'organism': 'Bos taurus'},
    // {'id': 'Bos_taurus/UCSC/bosTau8', 'organism': 'Bos taurus'},

    // {'id': 'Caenorhabditis_elegans/Ensembl/WBcel215', 'organism': 'Caenorhabditis elegans'},
    {'id': 'Caenorhabditis_elegans/Ensembl/WBcel235', 'organism': 'Caenorhabditis elegans'},
    // {'id': 'Caenorhabditis_elegans/Ensembl/WS210', 'organism': 'Caenorhabditis elegans'},
    {'id': 'Caenorhabditis_elegans/Ensembl/WS220', 'organism': 'Caenorhabditis elegans'},
    // {'id': 'Caenorhabditis_elegans/NCBI/WS190', 'organism': 'Caenorhabditis elegans'},
    {'id': 'Caenorhabditis_elegans/NCBI/WS195', 'organism': 'Caenorhabditis elegans'},
    {'id': 'Caenorhabditis_elegans/UCSC/ce10', 'organism': 'Caenorhabditis elegans'},
    // {'id': 'Caenorhabditis_elegans/UCSC/ce6', 'organism': 'Caenorhabditis elegans'},

    // {'id': 'Canis_familiaris/Ensembl/BROADD2', 'organism': 'Canis familiaris'},
    // {'id': 'Canis_familiaris/Ensembl/CanFam3.1', 'organism': 'Canis familiaris'},
    // {'id': 'Canis_familiaris/NCBI/build2.1', 'organism': 'Canis familiaris'},
    // {'id': 'Canis_familiaris/NCBI/build3.1', 'organism': 'Canis familiaris'},
    // {'id': 'Canis_familiaris/UCSC/canFam2', 'organism': 'Canis familiaris'},
    // {'id': 'Canis_familiaris/UCSC/canFam3', 'organism': 'Canis familiaris'},

    {'id': 'Danio_rerio/Ensembl/GRCz10', 'organism': 'Danio rerio'},
    // {'id': 'Danio_rerio/Ensembl/Zv9', 'organism': 'Danio rerio'},
    {'id': 'Danio_rerio/NCBI/GRCz10', 'organism': 'Danio rerio'},
    // {'id': 'Danio_rerio/NCBI/Zv9', 'organism': 'Danio rerio'},
    {'id': 'Danio_rerio/UCSC/danRer10', 'organism': 'Danio rerio'},
    // {'id': 'Danio_rerio/UCSC/danRer7', 'organism': 'Danio rerio'},

    // {'id': 'Drosophila_melanogaster/Ensembl/BDGP5', 'organism': 'Drosophila melanogaster'},
    // {'id': 'Drosophila_melanogaster/Ensembl/BDGP5.25', 'organism': 'Drosophila melanogaster'},
    {'id': 'Drosophila_melanogaster/Ensembl/BDGP6', 'organism': 'Drosophila melanogaster'},
    // {'id': 'Drosophila_melanogaster/NCBI/build4.1', 'organism': 'Drosophila melanogaster'},
    // {'id': 'Drosophila_melanogaster/NCBI/build5', 'organism': 'Drosophila melanogaster'},
    // {'id': 'Drosophila_melanogaster/NCBI/build5.3', 'organism': 'Drosophila melanogaster'},
    {'id': 'Drosophila_melanogaster/NCBI/build5.41', 'organism': 'Drosophila melanogaster'},
    // {'id': 'Drosophila_melanogaster/UCSC/dm3', 'organism': 'Drosophila melanogaster'},
    {'id': 'Drosophila_melanogaster/UCSC/dm6', 'organism': 'Drosophila melanogaster'},

    /// {'id': 'Enterobacteriophage_lambda/NCBI/1993-04-28', 'organism': 'Enterobacteriophage lambda'},

    // {'id': 'Equus_caballus/Ensembl/EquCab2', 'organism': 'Equus caballus'},
    // {'id': 'Equus_caballus/NCBI/EquCab2.0', 'organism': 'Equus caballus'},
    // {'id': 'Equus_caballus/UCSC/equCab2', 'organism': 'Equus caballus'},

    {'id': 'Escherichia_coli_K_12_DH10B/Ensembl/EB1', 'organism': 'Escherichia coli K 12 DH10B'},
    {'id': 'Escherichia_coli_K_12_DH10B/NCBI/2008-03-17', 'organism': 'Escherichia coli K 12 DH10B'},
    {'id': 'Escherichia_coli_K_12_MG1655/NCBI/2001-10-15', 'organism': 'Escherichia coli K 12 MG1655'},

    {'id': 'Gallus_gallus/Ensembl/Galgal4', 'organism': 'Gallus gallus'},
    // {'id': 'Gallus_gallus/Ensembl/WASHUC2', 'organism': 'Gallus gallus'},
    // {'id': 'Gallus_gallus/NCBI/build2.1', 'organism': 'Gallus gallus'},
    {'id': 'Gallus_gallus/NCBI/build3.1', 'organism': 'Gallus gallus'},
    // {'id': 'Gallus_gallus/UCSC/galGal3', 'organism': 'Gallus gallus'},
    {'id': 'Gallus_gallus/UCSC/galGal4', 'organism': 'Gallus gallus'},

    {'id': 'Glycine_max/Ensembl/Gm01', 'organism': 'Glycine max'},

    // {'id': 'Macaca_mulatta/Ensembl/Mmul_1', 'organism': 'Macaca mulatta'},

    // {'id': 'Mycobacterium_tuberculosis_H37RV/Ensembl/H37Rv.EB1', 'organism': 'Mycobacterium tuberculosis H37RV'},
    // {'id': 'Mycobacterium_tuberculosis_H37RV/NCBI/2001-09-07', 'organism': 'Mycobacterium tuberculosis H37RV'},
    // {'id': 'Oryza_sativa_japonica/Ensembl/IRGSP-1.0', 'organism': 'Oryza sativa japonica'},
    // {'id': 'Oryza_sativa_japonica/Ensembl/MSU6', 'organism': 'Oryza sativa japonica'},
    // {'id': 'Pan_troglodytes/Ensembl/CHIMP2.1', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/Ensembl/CHIMP2.1.4', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/NCBI/build2.1', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/NCBI/build3.1', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/UCSC/panTro2', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/UCSC/panTro3', 'organism': 'Pan troglodytes'},
    // {'id': 'Pan_troglodytes/UCSC/panTro4', 'organism': 'Pan troglodytes'},

    // {'id': 'PhiX/Illumina/RTA', 'organism': 'PhiX'},
    // {'id': 'PhiX/NCBI/1993-04-28', 'organism': 'PhiX'},

    // {'id': 'Pseudomonas_aeruginosa_PAO1/NCBI/2000-09-13', 'organism': 'Pseudomonas aeruginosa PAO1'},

    // {'id': 'Rattus_norvegicus/Ensembl/RGSC3.4', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/Ensembl/Rnor_5.0', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/Ensembl/Rnor_6.0', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/NCBI/RGSC_v3.4', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/NCBI/Rnor_5.0', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/NCBI/Rnor_6.0', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/UCSC/rn4', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/UCSC/rn5', 'organism': 'Rattus norvegicus'},
    // {'id': 'Rattus_norvegicus/UCSC/rn6', 'organism': 'Rattus norvegicus'},

    // {'id': 'Rhodobacter_sphaeroides_2.4.1/NCBI/2005-10-07', 'organism': 'Rhodobacter sphaeroides 2.4.1'},

    // {'id': 'Saccharomyces_cerevisiae/Ensembl/EF2', 'organism': 'Saccharomyces cerevisiae'},
    // {'id': 'Saccharomyces_cerevisiae/Ensembl/EF3', 'organism': 'Saccharomyces cerevisiae'},
    // {'id': 'Saccharomyces_cerevisiae/Ensembl/EF4', 'organism': 'Saccharomyces cerevisiae'},
    {'id': 'Saccharomyces_cerevisiae/Ensembl/R64-1-1', 'organism': 'Saccharomyces cerevisiae', 'recommended': true},
    // {'id': 'Saccharomyces_cerevisiae/NCBI/build2.1', 'organism': 'Saccharomyces cerevisiae'},
    {'id': 'Saccharomyces_cerevisiae/NCBI/build3.1', 'organism': 'Saccharomyces cerevisiae'},
    // {'id': 'Saccharomyces_cerevisiae/UCSC/sacCer2', 'organism': 'Saccharomyces cerevisiae'},
    // {'id': 'Saccharomyces_cerevisiae/UCSC/sacCer3', 'organism': 'Saccharomyces cerevisiae'},
    // {'id': 'Schizosaccharomyces_pombe/Ensembl/EF1', 'organism': 'Schizosaccharomyces pombe'},
    // {'id': 'Schizosaccharomyces_pombe/Ensembl/EF2', 'organism': 'Schizosaccharomyces pombe'},
    // {'id': 'Sorangium_cellulosum_So_ce_56/NCBI/2007-11-27', 'organism': 'Sorangium cellulosum So ce 56'},
    // {'id': 'Sorghum_bicolor/Ensembl/Sbi1', 'organism': 'Sorghum bicolor'},
    // {'id': 'Staphylococcus_aureus_NCTC_8325/NCBI/2006-02-13', 'organism': 'Staphylococcus aureus NCTC 8325'},

    {'id': 'Sus_scrofa/Ensembl/Sscrofa10.2', 'organism': 'Sus scrofa'},
    // {'id': 'Sus_scrofa/Ensembl/Sscrofa9', 'organism': 'Sus scrofa'},
    // {'id': 'Sus_scrofa/NCBI/Sscrofa10', 'organism': 'Sus scrofa'},
    {'id': 'Sus_scrofa/NCBI/Sscrofa10.2', 'organism': 'Sus scrofa'},
    // {'id': 'Sus_scrofa/NCBI/Sscrofa9.2', 'organism': 'Sus scrofa'},
    // {'id': 'Sus_scrofa/UCSC/susScr2', 'organism': 'Sus scrofa'},
    {'id': 'Sus_scrofa/UCSC/susScr3', 'organism': 'Sus scrofa'},

    // {'id': 'Zea_mays/Ensembl/AGPv2', 'organism': 'Zea mays'},
    // {'id': 'Zea_mays/Ensembl/AGPv3', 'organism': 'Zea mays'},
];

export default available_genomes;
