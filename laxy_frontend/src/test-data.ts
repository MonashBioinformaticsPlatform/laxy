// Test data
import {SampleSet, ComputeJob} from './model';

export const DummySampleList: SampleSet = {
    id: undefined,
    name: 'Dummyset',
    items: [
        {
            'id': 'kazd4mZvmYX0OXw07dGfnV',
            'name': 'SampleA',
            'metadata': {'condition': 'wildtype'},
            'files': [
                {
                    'R1': 'ftp://example.com/sampleA_lane1_R1.fastq.gz',
                    'R2': 'ftp://example.com/sampleA_lane1_R2.fastq.gz'
                },
            ],
        },
        {
            'id': 'lezd4mZvmYX0OXw07dGfnV',
            'name': 'SampleB',
            'metadata': {'condition': 'mutant'},
            'files': [
                {
                    'R1': 'ftp://example.com/sampleB_lane1_R1.fastq.gz',
                    'R2': 'ftp://example.com/sampleB_lane1_R2.fastq.gz'
                },
                {
                    'R1': 'ftp://example.com/sampleB_lane4_R1.fastq.gz',
                    'R2': 'ftp://example.com/sampleB_lane4_R2.fastq.gz'
                }

            ]
        },
        {
            'id': 'food4mZvmYX0OXw07dGfnV',
            'name': 'sample_wildtype',
            'metadata': {'condition': 'wildtype'},
            'files': [
                {
                    'R1': '2VSd4mZvmYX0OXw07dGfnV',
                    'R2': '3XSd4mZvmYX0OXw07dGfmZ'
                },
                {
                    'R1': 'Toopini9iPaenooghaquee',
                    'R2': 'Einanoohiew9ungoh3yiev'
                }]
        },
        {
            'id': 'bla7eiPhaiwion6ohniek3',
            'name': 'sample_mutant',
            'metadata': {'condition': 'mutant'},
            'files': [
                {
                    'R1': 'zoo7eiPhaiwion6ohniek3',
                    'R2': 'ieshiePahdie0ahxooSaed'
                },
                {
                    'R1': 'nahFoogheiChae5de1iey3',
                    'R2': 'Dae7leiZoo8fiesheech5s'
                }]
        }
    ]
} as SampleSet;

export const DummyPipelineConfig = {
    'sample_set': '3NNIIOt8skAuS1w2ZfgOq',
    'sample_metadata': {
        'kazd4mZvmYX0OXw07dGfnV': {'condition': 'wildtype'},
        'lezd4mZvmYX0OXw07dGfnV': {'condition': 'mutant'},
        'food4mZvmYX0OXw07dGfnV': {'condition': 'wildtype'},
        'bla7eiPhaiwion6ohniek3': {'condition': 'mutant'},
    },
    'params': {
        'genome': 'mm10'
    },
    'pipeline': 'rnasik',
    'comment': 'some string'
};

export const ENADummySampleList: ENASample[] = [
    {
        run_accession: 'SRRFAKE0001',
        sample_accession: 'SAMFAKE0001',
        library_strategy: 'RNA-Seq',
        read_count: 12346
    },
    {
        run_accession: 'SRRFAKE0001',
        sample_accession: 'SAMFAKE0001',
        library_strategy: 'RNA-Seq',
        read_count: 1234567
    },
    {
        run_accession: 'SRRFAKE0001',
        sample_accession: 'SAMFAKE0001',
        library_strategy: 'RNA-Seq',
        read_count: 12345678
    },
    {
        run_accession: 'SRRFAKE0001',
        sample_accession: 'SAMFAKE0001',
        library_strategy: 'RNA-Seq',
        read_count: 123456789
    },
];

export const DummyJobList: ComputeJob[] = [
    {
        'id': '4bS75UgK4BIkYT2nmnv9BF',
        'owner': 1,
        'input_fileset_id': '5cUMhEHPl7tusyWQWRdXCV',
        'output_fileset_id': 'lte5G15TXSkfmF6dlP1aj',
        'params': {
            'id': '2CjwU7RJtFq8u60DBiORik',
            'owner': 1,
            'params': {
                'genome': 'hg19'
            },
            'pipeline': 'rnasik',
            'sample_set': {
                'id': '461UrmNeZaVe64pJYG9S5q',
                'name': 'CSV uploaded on 2018-04-24T05:00:10.531287',
                'owner': 1,
                'samples': [
                    {
                        'name': 'SAMN03375745',
                        'files': [
                            {
                                'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR181/008/SRR1819888/SRR1819888_1.fastq.gz'
                            },
                            {
                                'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR181/008/SRR1819888/SRR1819888_2.fastq.gz'
                            }
                        ],
                        'metadata': {
                            'ena': {
                                'fastq_ftp': [
                                    {
                                        'R1':
                                        'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                        'SRR181/008/SRR1819888/SRR1819888_1.fastq.gz'
                                    },
                                    {
                                        'R2':
                                        'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                        'SRR181/008/SRR1819888/SRR1819888_2.fastq.gz'
                                    }
                                ],
                                'fastq_md5': [
                                    '58a845ac61ae48efdb704bff2df2576f',
                                    'cfc8334c8892ebe8c02d4c192dd49740'
                                ],
                                'run_alias': 'RNA-Seq of C. fleckeri tentacle RNA',
                                'base_count': '9439794108',
                                'read_count': 46731654,
                                'broker_name': '',
                                'center_name': 'QIMR Berghofer MRI',
                                'fastq_bytes': [
                                    3719354690,
                                    3730960959
                                ],
                                'study_alias': 'PRJNA276493',
                                'library_name': '',
                                'sample_alias': 'Cfleckeri Tentacle',
                                'run_accession': 'SRR1819888',
                                'library_layout': 'PAIRED',
                                'library_source': 'TRANSCRIPTOMIC',
                                'study_accession': 'PRJNA276493',
                                'experiment_alias': 'Tentacle sequencing',
                                'instrument_model': 'Illumina HiSeq 2000',
                                'library_strategy': 'RNA-Seq',
                                'sample_accession': 'SAMN03375745',
                                'library_selection': 'unspecified',
                                'instrument_platform': 'ILLUMINA',
                                'experiment_accession': 'SRX891607'
                            },
                            'condition': 'uninfected'
                        }
                    },
                    {
                        'name': 'SAMN02315078',
                        'files': [
                            {
                                'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR950/SRR950078/SRR950078_1.fastq.gz'
                            },
                            {
                                'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR950/SRR950078/SRR950078_2.fastq.gz'
                            }
                        ],
                        'metadata': {
                            'ena': {
                                'fastq_ftp': [
                                    {
                                        'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/' +
                                        'fastq/SRR950/SRR950078/SRR950078_1.fastq.gz'
                                    },
                                    {
                                        'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/' +
                                        'fastq/SRR950/SRR950078/SRR950078_2.fastq.gz'
                                    }
                                ],
                                'fastq_md5': [
                                    'eee21620ca17744147ff66cdd2529066',
                                    '39763f20027f17eb83ab00dc7d2da65c'
                                ],
                                'run_alias': 'GSM1206234_r1',
                                'base_count': '20278176020',
                                'read_count': 100387010,
                                'broker_name': '',
                                'center_name': 'GEO',
                                'fastq_bytes': [
                                    8584375694,
                                    8650136401
                                ],
                                'study_alias': 'GSE49712',
                                'library_name': '',
                                'sample_alias': 'GSM1206234',
                                'run_accession': 'SRR950078',
                                'library_layout': 'PAIRED',
                                'library_source': 'TRANSCRIPTOMIC',
                                'study_accession': 'PRJNA214799',
                                'experiment_alias': 'GSM1206234',
                                'instrument_model': 'Illumina HiSeq 2000',
                                'library_strategy': 'RNA-Seq',
                                'sample_accession': 'SAMN02315078',
                                'library_selection': 'cDNA',
                                'instrument_platform': 'ILLUMINA',
                                'experiment_accession': 'SRX333347'
                            },
                            'condition': 'zombie'
                        }
                    }
                ]
            },
            'description': 'Yet another test',
            'created_time': new Date('2018-04-24T05:00:10.635698Z'),
            'modified_time': new Date('2018-04-24T05:00:10.642215Z')
        },
        'compute_resource': 'rML9cZ45bs4PdNanqdArU',
        'created_time': new Date('2018-04-24T05:00:10.757888Z'),
        'modified_time': new Date('2018-04-24T05:00:11.985785Z'),
        'secret': 'txKZkVWhD7chpPofZet19pTPugKazZ5vx2INVjGZPf34BHRFYkwzlOTs' +
        '8DLGaOQ3oSRtQIKUun7T3zecgD3PAeTP2kW3DQA5NkQefPgzZK9gJk3ocd6E41oVMkP' +
        'Ydi8WtkGzpK2CgrA96EK3fnTVjmxwSZswv9VqDPCaKRw5XzcINvAIWVgVkk3HLDPhihF' +
        'u9L5aPz2imiq9xD4lmBLRC3kAyCZchFLJ3GFZeUozLYpeHNShCC5dHjNnsE7OsBL',
        'status': 'running',
        'latest_event': 'INPUT_DATA_DOWNLOAD_STARTED',
        'exit_code': null,
        'remote_id': '6035',
        'completed_time': null
    },
    {
        'id': '5bcs2P4W79KKEj43jA85G3',
        'owner': 1,
        'input_fileset_id': '3mcv4wK66q6xwPuLhLSlc0',
        'output_fileset_id': '1ZoPXThJx8zniui7Fg2k1q',
        'params': {
            'id': '4AZpf19PMqDrq9clvID1DY',
            'owner': 1,
            'params': {
                'genome': 'R64-1-1'
            },
            'pipeline': 'rnasik',
            'sample_set': {
                'id': '13kkLzwmPt0QehRE5FfqGd',
                'name': 'CSV uploaded on 2018-05-02T06:53:12.655648',
                'owner': 1,
                'samples': [
                    {
                        'name': 'SAMN02596468',
                        'files': [
                            {
                                'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR117/' +
                                '002/SRR1174042/SRR1174042_1.fastq.gz'
                            },
                            {
                                'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR117/' +
                                '002/SRR1174042/SRR1174042_2.fastq.gz'
                            }
                        ],
                        'metadata': {
                            'ena': {
                                'fastq_ftp': [
                                    {
                                        'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/' +
                                        'fastq/SRR117/002/SRR1174042/SRR1174042_1.fastq.gz'
                                    },
                                    {
                                        'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/' +
                                        'fastq/SRR117/002/SRR1174042/SRR1174042_2.fastq.gz'
                                    }
                                ],
                                'fastq_md5': [
                                    '81963251d9255cbb394d660433d89773',
                                    'd65e117fa9f8b11f44e669811cfb5276'
                                ],
                                'run_alias': 'phage phiPsa267',
                                'base_count': '168868242',
                                'read_count': 560601,
                                'broker_name': '',
                                'center_name': 'University of Otago',
                                'fastq_bytes': [
                                    58690363,
                                    63592951
                                ],
                                'study_alias': 'PRJNA236447',
                                'library_name': '',
                                'sample_alias': 'phiPsa267',
                                'run_accession': 'SRR1174042',
                                'library_layout': 'PAIRED',
                                'library_source': 'GENOMIC',
                                'study_accession': 'PRJNA236447',
                                'experiment_alias': 'Phage phiPsa267',
                                'instrument_model': 'Illumina MiSeq',
                                'library_strategy': 'WGS',
                                'sample_accession': 'SAMN02596468',
                                'library_selection': 'unspecified',
                                'instrument_platform': 'ILLUMINA',
                                'experiment_accession': 'SRX474241'
                            },
                            'condition': ''
                        }
                    },
                    {
                        'name': 'SAMN02597546',
                        'files': [
                            {
                                'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR117/009/SRR1174149/SRR1174149_1.fastq.gz'
                            },
                            {
                                'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                'SRR117/009/SRR1174149/SRR1174149_2.fastq.gz'
                            }
                        ],
                        'metadata': {
                            'ena': {
                                'fastq_ftp': [
                                    {
                                        'R1': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                        'SRR117/009/SRR1174149/SRR1174149_1.fastq.gz'
                                    },
                                    {
                                        'R2': 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/' +
                                        'SRR117/009/SRR1174149/SRR1174149_2.fastq.gz'
                                    }
                                ],
                                'fastq_md5': [
                                    'f3db10378960bd84d5ded87ad3429f99',
                                    'c169c3a0bf64d3bb96c2245aa5b17453'
                                ],
                                'run_alias': 'Phage phiPsa300',
                                'base_count': '201119849',
                                'read_count': 667814,
                                'broker_name': '',
                                'center_name': 'University of Otago',
                                'fastq_bytes': [
                                    70299965,
                                    76880258
                                ],
                                'study_alias': 'PRJNA236447',
                                'library_name': '',
                                'sample_alias': 'phiPsa300',
                                'run_accession': 'SRR1174149',
                                'library_layout': 'PAIRED',
                                'library_source': 'GENOMIC',
                                'study_accession': 'PRJNA236447',
                                'experiment_alias': 'Phage phiPsa300',
                                'instrument_model': 'Illumina MiSeq',
                                'library_strategy': 'WGS',
                                'sample_accession': 'SAMN02597546',
                                'library_selection': 'unspecified',
                                'instrument_platform': 'ILLUMINA',
                                'experiment_accession': 'SRX474369'
                            },
                            'condition': ''
                        }
                    }
                ]
            },
            'description': 'LePhages',
            'created_time': new Date('2018-05-02T06:53:28.418655Z'),
            'modified_time': new Date('2018-05-02T07:21:01.865453Z')
        },
        'compute_resource': 'rML9cZ45bs4PdNanqdArU',
        'created_time': new Date('2018-05-02T07:21:01.966905Z'),
        'modified_time': new Date('2018-05-02T07:21:41.496303Z'),
        'secret': 'zltTOkOVjuA9wfPrAtw1oVYxioe9R06mxqzzeQ0whlea2Pvn9QUUbn8TGFmjn' +
        'sOSetj8DDcbrALpEy2OB4qKHX0Hi6ShQwcXI6DXd3SMgWgZZaozgfqlxKBpkVeIa8xiuZRUz' +
        'exMMkEMTE26pBGHJrLSB7qNSIvr4YcO6124nfwKLW31U1F4UNedGZ5Yq1TbAIkN5xii7R6DX' +
        '7OwipZZAfaR0afXmk0ApHff5bpDSY7wlSFfatF83ueNYrFrqTW',
        'status': 'failed',
        'latest_event': 'JOB_PIPELINE_FAILED',
        'exit_code': 1,
        'remote_id': '2910',
        'completed_time': null
    }
];

export const DummyFileSet = {
    'id': '25iqJL3P5KGcW9UwOb5eP3',
    'name': 'Output files for job: 5CKQI21a9cHVTmPjnxgl03',
    'owner': 1,
    'files': [
        {
            'id': '26snbeaSatILEwUhCa778U',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/' +
            '5CKQI21a9cHVTmPjnxgl03/' +
            'output/RNAsik.bds.20180514_153905_725.report.html',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2Yw2IlHmQugzMZhnNiR2on',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/download.log',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '7bPJVogGXqQx23G7LZaBXC',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/job_env.out',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '67BWICTJPVBuAc07tRTsBt',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/job.out',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '48bRO0bBcyVycFigU1C2au',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725.dag.js',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '7Yd0foqRfDGm6x9s6p8e59',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.exitCode',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '66C2HYNkzdRiTmkQmQfeMv',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Make_chrom_sizes_file.line_131.id_11.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'PdWEG6ydU7ULA8Z5FoupB',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Making_dictionary_File.line_110.id_9.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4sc5XhaOlpz4PyKQHWNOQ9',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.exitCode',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'eCUbUieHlUx42KL4BFD1a',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'RpoIynnCHNGqaRaiC0eNn',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Indexing_FASTA_file.line_122.id_13.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'HPHKdLAmYtIaq8sZnR8TJ',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Making_dictionary_File.line_110.id_9.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4LMcHAeWVCpT9pI6G7PLXr',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '44oaImELtS61JPAQEqlhlu',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/samples/fqFiles',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1XrfUpisr1CVN3LRdS37B5',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/samples/samplesSheet',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2tSO8jxkvZUDbzxLL2IYTP',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1o4DU1jbJTnCZLnGuSngxD',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.exitCode',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1gimnZ3KJbSDtvbOq7rX1L',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Make_chrom_sizes_file.line_131.id_11.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5Jbe8NG95JgGbhVsQQviSD',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Make_chrom_sizes_file.line_131.id_11.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1xR3AN6ATTbHFlLQ7baAZl',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Indexing_FASTA_file.line_122.id_13.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1NSmjqmaBjZv1KUJySMir8',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1K8PrQOMEC0VH8qVHlQT9s',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '36H4eTjUs86xJdIklbLg2M',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Making_dictionary_File.line_110.id_9.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2VTfxVAiEMOfpfh2ZM8JOc',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'iCDaypkWYsvmDn8vrJHca',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Indexing_FASTA_file.line_122.id_13.exitCode',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5NBHxgNsOCX6M4cxCoz9Wk',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '7ZutHntfzZigT0R0aESxUC',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stderr',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '78JB2gPYpPoF32zG0CuRj9',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Make_chrom_sizes_file.line_131.id_11.exitCode',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '3nvxUoY7HJRVfUHgWKCMVE',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Copying_.._.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stdout',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '7FEf5cMDDuQOr7c2cmKrp',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725/task.sikRefFiles.Indexing_FASTA_file.line_122.id_13.sh',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '3GZMcUqQwpgH28rNR2ePWc',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/RNAsik.bds.20180514_153905_725.report.yaml',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'aBPtINkdjPQvVQJqER50j',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/job.err',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '459Di6JsHLgseW7uP76BY9',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/toolsOpts/featureCounts',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5M3qK0cDmDcKssM8IzXort',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/addMetrics',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '65k80Kpajtr4saMXrQlcVQ',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/theBams',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '7kVXg9taZJFXv82qrCRzmP',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/featureCounts',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5XgG87f2bLiM0Mbg7oN7Bq',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/bams',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'oiJapkaFBjFTapV296XSq',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/mdupsBams',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4qMRkILDTJetg75DHgtYzS',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/data/covFiles',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6evWWqHPr8KYVGPD3zCCJp',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/other/annotation',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'yx40ah4jS2dhW9zlFC9Zc',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/samples/fqMap',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4Ph5AWzdyHyOdDDMDoSifk',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/ReorderSam',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '3OAEHwMhfDT6PfruDQF1cG',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/bwa',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2mg0fvaPfrsAK3B3lBxiTR',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/python',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4U6i9kiZLuyRUnrbpoUzgh',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/samtools',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6OHX5EuYULoeiHJhqNHZXV',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/multiqc',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6HSAdzglHDFJJDBiAumqq8',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/featureCounts',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1lv7xXFomzvpPPkP2sBA4N',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/bedtools2',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2kO6u4jW1lA5QxIFUOxQjY',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/fastqc',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '2PDWhwQvOPfzai49gGymhw',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/RNAsik',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '53rI7sYfRo50984BY6ZfTi',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/MarkDuplicates',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5IeoxqodAHOhzDoi0bfDBL',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/star',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '3aWdDviLnSwVN7pGKp9Dk9',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/SortSam',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6FSJTqG5i7SQMpQsgEp7gz',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/versions/qualimap',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '68D5iwLeFUpT0l1H7Skv9g',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/fai',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '5D6zQWhkscU7BBpaPpcYVW',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/chromSizes',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6KggMK6vQ7XOff08IFuPDk',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/fastaRef',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1dxeCzfU3H18wjPsvlxvuV',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/gtfFile',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '1AhaWN6tHFrnOnQP37zgxt',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/picardDictFile',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'QIbJZkzhDgm5Ijinnz5Sc',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/star',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4gcrShdiaRIfa2BxVxINU6',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/logs/refFiles/STAR',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '4UcN8BPPoxar1VfNbXrNdO',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/samplesSheet.txt',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': 'yFOlzlfTbZRiock8DHC25',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/refFiles/genome.chromSizes',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '58aJShuQMDbGofxj7gOFKF',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/refFiles/genome.fa',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '60GJMogjEORBwAVCjOcC3k',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/refFiles/genome.fa.fai',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        },
        {
            'id': '6CYpEI8wxADlRRN3IKr2wE',
            'name': null,
            'location': 'laxy+sftp://rML9cZ45bs4PdNanqdArU/5CKQI21a9cHVTmPjnxgl03/output/sikRun/refFiles/genes.gtf',
            'owner': 1,
            'checksum': null,
            'metadata': {}
        }
    ]
};
