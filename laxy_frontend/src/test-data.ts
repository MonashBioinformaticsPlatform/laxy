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
        'exit_code': 1,
        'remote_id': '2910',
        'completed_time': null
    }
];
