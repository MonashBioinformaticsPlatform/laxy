// Test data
import {SampleSet, ComputeJob, LaxyFile} from './model';

// For testing Element UI Tree
const demoTreeData: any[] = [{
    id: 1,
    label: 'Level one 1',
    children: [{
        id: 4,
        label: 'Level two 1-1',
        children: [{
            id: 9,
            label: 'Level three 1-1-1'
        }, {
            id: 10,
            label: 'Level three 1-1-2'
        }]
    }]
}, {
    id: 2,
    label: 'Level one 2',
    children: [{
        id: 5,
        label: 'Level two 2-1'
    }, {
        id: 6,
        label: 'Level two 2-2'
    }]
}, {
    id: 3,
    label: 'Level one 3',
    children: [{
        id: 7,
        label: 'Level two 3-1'
    }, {
        id: 8,
        label: 'Level two 3-2'
    }]
}];

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

export const DummyFileSet: LaxyFileSet = {
    'id': '2a5rRC13IqBZLXva9CnMkS',
    'name': 'input',
    'owner': '51f6boKqYKhlm9S0CoCFOt',
    'files': [{
        'id': '3aeoDptaRuQfq4X4GlcmxR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.bam',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.bam',
        'checksum': 'md5:5dc000d353c3159772cd569efaeca41c',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['bam', 'alignment'],
        'metadata': {}
    } as LaxyFile, {
        'id': '4xmDTGPfuQfoV5MhWduDu0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.bai',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.bai',
        'checksum': 'md5:cb6af0cd8d49f248c62a45500a40700b',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['bai'],
        'metadata': {}
    } as LaxyFile, {
        'id': '12sREqaoL9WVW7Z8hkaaWe',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.bai',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.bai',
        'checksum': 'md5:7671aad1c1a69fea7dd0f0b135aa5a22',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['bai'],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ACDncmnXezOHusleYDKCB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.bam',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.bam',
        'checksum': 'md5:8b9e5a7ecc9161707712a8d7bfb56faa',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['bam', 'alignment'],
        'metadata': {}
    } as LaxyFile, {
        'id': '2q9k7R2znyNtKVccDX5n9g',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_report.html',
        'path': 'output/sikRun',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_report.html',
        'checksum': 'md5:6908603dc260a931d4e867897594658b',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['multiqc', 'html', 'report'],
        'metadata': {}
    } as LaxyFile, {
        'id': '4RBxbQsXi4yDcDJQwE2Jzn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'RNAsik.bds.20180718_161751_947.report.html',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947.report.html',
        'checksum': 'md5:dcaaaf46ae8f3c691d5bc5bd53225415',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['bds', 'logs', 'html', 'report'],
        'metadata': {}
    } as LaxyFile, {
        'id': 'AUa8AYvWc6nOPkRpXZVC9',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ForwardStrandedCounts.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/ForwardStrandedCounts.txt',
        'checksum': 'md5:166d2ada33d594cfe70590bbca33fbe9',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['counts', 'degust'],
        'metadata': {}
    } as LaxyFile, {
        'id': '4OyibJ6GqYPaOZu54RuZ3n',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'NonStrandedCounts.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/NonStrandedCounts.txt',
        'checksum': 'md5:03749e9c9f1182607c1793b0bc649b91',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['counts', 'degust'],
        'metadata': {}
    } as LaxyFile, {
        'id': 'oSqbAX6Ny3kA4PQYC9V4o',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'NonStrandedCounts-withNames.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/NonStrandedCounts-withNames.txt',
        'checksum': 'md5:01d638a1563d632cd29e86108b957f2b',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['counts', 'degust'],
        'metadata': {}
    } as LaxyFile, {
        'id': '76nJHXsFIOUo1SCmAl3E1e',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'NonStrandedCounts-withNames-proteinCoding.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/NonStrandedCounts-withNames-proteinCoding.txt',
        'checksum': 'md5:f12293f1e0633d00461357d795f93c04',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['counts', 'degust'],
        'metadata': {}
    } as LaxyFile, {
        'id': 'eGJICyvldGFJyMKk0kAoa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2vNlUR2GS8ipeovF3Xod3T',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1nCOIqghRKkdcAIaYtzGS5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ReverseStrandedCounts.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/ReverseStrandedCounts.txt',
        'checksum': 'md5:5eb50449274b01754962afd89cf31adf',
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': ['counts', 'degust'],
        'metadata': {}
    } as LaxyFile, {
        'id': '2UQTPOx3bQxeKHQeET2fOo',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2xPAvJWURuKNFejpfTJeG1',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'pygments.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/pygments.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1kDzP1Ln3ZyqZaqLn3cP7d',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5ZPJQQdzoxGBejMamX0GAK',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6MeAlIL8ajqcyUp9A044i',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'ljz7cC9aSUTx3AfeANv2p',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3yTUOmXcml5YfflrycDGK4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.Making_STAR_index.line_31.id_16.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.Making_STAR_index.line_31.id_16.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'nU2q4Z4VQ4sEFF2zHx8Zc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fastaRef',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/fastaRef',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5JfWWWVVrFOZIyYjZCwAX8',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_28.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_28.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Q5BecePfEGL5U4pXioJf3',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_insert_size_hist.pdf',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_insert_size_hist.pdf',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3KswSs2Jwr1iqAq8tCHJX0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'chrStart.txt',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/chrStart.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '83OiRwlFppg8qAuzUpy3A',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'chrNameLength.txt',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/chrNameLength.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2tgDb5Lgn7FawcyHbGyqYs',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.idxstats',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.idxstats',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ChO7HQKbtTiWwrK29Ya9s',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_all_features.line_109.id_58.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_all_features.line_109.id_58.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '45awoQR5vA1JibEKdJHU5Y',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'btMkh76DCT0Bhj8gTSdxn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'up-pressed.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/up-pressed.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4VZWZQ5r0HHV31zFYlKlq2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1V7PLFUvKzltFTzu5LlV6l',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'addMetrics',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/addMetrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Wz5hk6o6CZekaUnve2OzI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4e9o0R9ciOJpIWmqXv8Op0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'plus.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/plus.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3pccTfhxwnxebqczrVz7ze',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'degust',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/degust',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'KRH7JJ5ZtUrpnO6u75Y6r',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_2.siklog',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/.SRR1658460_2.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6kbD3ElzyEyyRU1ZVSb4C3',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_1.siklog',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/.SRR1658460_1.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7FEOqMB92uVTgAQ97wnV0P',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '34HZFotcBeIj7mf4nUCoaL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2NCkxMNKVg5L8IqNqU9Jbw',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'NonStrandedCounts.txt.summary',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/NonStrandedCounts.txt.summary',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4qfrJCzUm0i4U3uTVVeQ10',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_15.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_15.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5Ew1cOkuO8tsG37MD1OAtu',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '69HjXgBID5sByaVvUbZFmm',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_49.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_49.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1myCdDhJQg0A6AWKLfFhzp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2tAP0otmkWVdecbIls2wuV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4hsvIGhHAg5qUX6yOhhGYM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_geneIds.txt_file.line_77.id_57.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_geneIds.txt_file.line_77.id_57.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4HOeEJ90RaB166otcKe6Gy',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_5.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_5.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5N8cgyPtTXqHVqlHiYMHgO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualiMap',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/qualiMap',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1S0qlbJcZHxYwZQyqdrWWl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.multiqc.siklog',
        'path': 'output/sikRun',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/.multiqc.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1h9olMAOnyGW6bPHDGfGyV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_sorted_mdups_lib_complex.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658460_sorted_mdups_lib_complex.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'rmFAR0Yt7l0uQPLskNql7',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/multiqc',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1PFOldy15Uq8G4CmBoXduc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bwa',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/bwa',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5ftaHoZhrOpAcC6rAaer3H',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bgtop.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/bgtop.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6qbx0pb1NkM98p8E991tfu',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'searchtools.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/searchtools.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3hZEpWqUdnpNXrJs3tGz5d',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'down.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/down.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3V4vRCTVRC4bOx9KS3BggP',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_sorted_mdups_insert_size.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658454_sorted_mdups_insert_size.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7ASbYuBS1g8aKDFoCbaMMz',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/comment.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4H6YfzRDzxb9h6AJHqt6Ac',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_72.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_72.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2eMwikZzgA4El3EOfsMPW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'RNAsik',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/RNAsik',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2jCw1WCJoechAlD4PYmujR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_2_fastqc.zip',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658460_2_fastqc.zip',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7crDCtKNX2y6M2dNBAdPWb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'python',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/python',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2CxQgeLAhoDt0a6YBIYRbp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '75AKC8edWeLcnzRYrpqcal',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_1_fastqc.zip',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658454_1_fastqc.zip',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '21hypFaR5rJURi0jtEHLxL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_sorted_mdups_lib_complex.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658454_sorted_mdups_lib_complex.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '71zQ6zjlXqknvRQjkb1jaT',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Sg76gGBmnmtotC6f8j3GE',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5hW7ATGeev6qZQa5XGPDvd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_61.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_61.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '61NHaiQQ0bX0oVWXfsdeg2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Log.out',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/Log.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '29izjeKBLAYT2EGwnXKO0g',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4wLidNr9B8rrv5LbZ5NhHL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ForwardStrandedCounts.txt.summary',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/ForwardStrandedCounts.txt.summary',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'E3DLkHUjtbJsfwBMdr5Td',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1WXmO0UVTt1QQzKs3U0iiG',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '24pfybtAgerYnsTHt4ymZl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '39qmOln4tTms1e27Mpj5sW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_lib_complex.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_lib_complex.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6bCE9R3OeMER1Vb4qvRz7Q',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'plus.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/plus.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '49vS5D6FTWKtlRAxoO0UPi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'pairedBool',
        'path': 'output/sikRun/logs/other',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/other/pairedBool',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2j4n8sI7covFFStbgDDlhl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'pygments.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/pygments.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'PYRK5QylfFNQxXS2D0pAL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5yds05FhPu9UJimW4Kha8w',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1z01FEM4l9lf3PAXaE05Cl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_48.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_48.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '50iEacT947GNSwoF0X8bmA',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualimap_logo_small.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/qualimap_logo_small.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ybdemOMyEeazZ5DyHcSbz',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'covFiles',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/covFiles',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'GpTJupeFEAmUnAwHV4UZU',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_29.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_29.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'aDqdew1wxpjzGePAkFxQJ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_align.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_align.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1Qb5dmCf3YOZJ4O0JxHHwM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fai',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/fai',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5QIfwgzFbNYEUXrpWdKIz2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_insert_size.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_insert_size.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5nlB0dhkleDApKvECGehYk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5OQ8TosStZh4qtKDarNmPM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2RMF9k5TF1UvozY4OPWBOd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_picard_AlignmentSummaryMetrics.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_picard_AlignmentSummaryMetrics.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4tnDDMbGSOf4mfNMt5peeD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_Log.progress.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658460_Log.progress.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'SFh70AoHrFwWrEJmiCt3e',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_reverseStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658460_reverseStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5W4cPvWObYKV38cH0pYeNu',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_samtools_flagstat.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_samtools_flagstat.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4aREusrD1Zx4IROY2PBXnf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bedtools2',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/bedtools2',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4WIyiKqNv188PRJsBhDbui',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genome.fa.fai',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.fa.fai',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5IK6z8pnY2ZSix0DVsf3Nr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fqFiles',
        'path': 'output/sikRun/logs/samples',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/samples/fqFiles',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6DQOVL7mBENs9AAahboG4t',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'MarkDuplicates',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/MarkDuplicates',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'nofjkmiMEHUCNYrAWTYw4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'jquery.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/jquery.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4WBCndaDwt1dgsBKhco5aQ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'down-pressed.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/down-pressed.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1aoHjf0jhJE1ZAj5witrRr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ajax-loader.gif',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/ajax-loader.gif',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6EHfRFOftgp0DvCrY3d2HI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_general_stats.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_general_stats.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7KJPaFFYKu6qsMrWEGsa48',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2zXh1ZKfDQdspPna3DoD8J',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_sorted_mdups_gc.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658460_sorted_mdups_gc.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'psXXu5nAR6F3tAko0BRJw',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Making_dictionary_File.line_113.id_9.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Making_dictionary_File.line_113.id_9.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1giqIDOOJiyQIioO0ypjCt',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3CGHJqMsjIJqfRjKode9V5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6ktQLHmDTMCFPuFhKgBVv6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'websupport.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/websupport.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6VaTvjGLegWqMY0713glHZ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fastqc',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/fastqc',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51fGbwV10XEt0OsTCtXIka',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.Making_STAR_index.line_31.id_16.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.Making_STAR_index.line_31.id_16.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '598W1k9ry2GKb5GOGQO54n',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4VGuawuB4WPbPOXKcFAgSb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'geneIds.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/geneIds.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5fRFNG3K5Nsm5bvtqvlmk5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '108qXswUxhKkPvE75PVXQH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '39LZ3QHvxvRoktpPkXTeh9',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'up-pressed.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/up-pressed.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6iEan95PlAwkfkHghPLuky',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'basic.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/basic.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3fXaIfKVa2nL0NqTk2VHA4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_sorted_mdups_align.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658454_sorted_mdups_align.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1MUQHrMfTVd70ZY80VKg2D',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(high).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport/coverage_profile_along_genes_(high).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Z54xQgcreu8rGjQaX4PUW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.idxstats',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.idxstats',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2q42VqI13Zu42xOLUSI5dY',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ajax-loader.gif',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/ajax-loader.gif',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6jKbSxpgN6AXflFNBSK48w',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7SIUbcyVCo9kXoxQc2NV0z',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5YeMKOu0jYhqqzFwGe07qr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3SwBXWpvEQB6mcN6AHKA6u',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5IiBdUxgnk8Qst5hU3cI29',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_insert_size.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_insert_size.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6nDnIwnHVVeEARPSCipWPA',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'strandInfo.txt',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/strandInfo.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5rjvwERAsrE9KI0l3Nlvr2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3LrXPSwS8pxm0MlSVP3d49',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SortSam',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/SortSam',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'rNE94TjL7FnvUjZQzPDd2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment-bright.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/comment-bright.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2FQwoaAoBixV4KgC4fb29o',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2pyif99V6rhcPjo4U5RyTa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_sorted_mdups_align.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658460_sorted_mdups_align.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6FrEyq0gojVnGwH5th5QQq',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'report.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/report.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2lkwziDiACeVTlqj53sAWQ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bams',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/bams',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2u4oVMe3yBGwpBxzxr7sbc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_counts.txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658454',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/SRR1658454_counts.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'O53yzidVXzfQCPrA1XtSd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '48PVq81hIC7d8YUyB1zGUp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/comment.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'XFQqNf4dKJvI2IYMIMYOq',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4OpTLdnFpjnapf8QsYrBfT',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1p48LkCYrRvtrnC0GhtiW2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '28BV5eRMDViBliVvvKnjQ9',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1ZGPk3qw0IdfKErBXwt4vY',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_1_fastqc.zip',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658460_1_fastqc.zip',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1JNF9bF7XrebHoT4IL2WM5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7HEVVpzghu6v8wb8VVq3fj',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_8.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_8.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '202UGv1iFiX3bQ7wZ8TVEa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Generating_MultiQC_report.line_57.id_73.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Generating_MultiQC_report.line_57.id_73.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5c9B2stXB09gNxCiUvosI0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc.log',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc.log',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1sAX44aKJpIFSQAufd7Awn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '21uXYemJH4dBAJqRXhClad',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1ftRKrlj6qHVqMUfJO1PQB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4f8UwZ39RfwkkwbYYW0xy7',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6WC2StUKZ7bdgTjAZpZpo4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'job.out',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/job.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4LpVsb8CIAhtjwbKK6VXap',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_gc.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_gc.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7dwN6o2tM7UXh1P0tPsGKb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_fastqc.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_fastqc.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2w9Ga1mVuHfbcP12O4bF2i',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3VXBZU7Ay1Uut5xJS5XmGC',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'CtOkU0Cz5SbZUeyIT3u1c',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_41.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_41.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7Dtwz9nrHiOU38RrSUFH4l',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Making_dictionary_File.line_113.id_9.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Making_dictionary_File.line_113.id_9.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1n1uzP0kG1Bhu3Ei01nWSc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'chrLength.txt',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/chrLength.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '12jwZ90pL4qKR1VCGW6TOC',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'gv9XEmwypV1MWsvEL5MrS',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'RidB1htunhLXp0YLA99Cc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'RrekMxdbzD2nZ700tGC4q',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6nEbkSrmJ0xCYATnQ6E91v',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'report.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/report.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3xpiXhmJwRXwMFJro2twwY',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Generating_MultiQC_report.line_57.id_73.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Generating_MultiQC_report.line_57.id_73.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1Lio28C4jmIXQlwx5YtOvO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_10.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_10.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5vDP22THyJFBa1CDhzv3ri',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'annotation',
        'path': 'output/sikRun/logs/other',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/other/annotation',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1zNVQvF9Y7JrzHI4XFapl0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1E8ZghUOPOhH0rLicdEy1r',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_star.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_star.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3XEKMt5s3jrgQhATUb5Pbd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_reverseStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658454_reverseStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2lCvAbPwfH8RgO4YQTwkHW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Junction Analysis.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Junction Analysis.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'fs8zkHJvK6o0Uo5NBugLj',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6lL6CRN0ciOzTPa2ftJx1J',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'star',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/star',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1O7OhYg4NLBAUIG2CvrohE',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(total).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport/coverage_profile_along_genes_(total).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4h2H2FfYi0jImiydrvaHZG',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (High).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Coverage Profile Along Genes (High).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '57nVFgPLsaEqdjdIa2Oykm',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'file.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/file.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2zUoTftkOEp0i0WfBZ0W96',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Genome',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/Genome',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6j0kLKrbJH5PMiXi5rDXzS',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_1_fastqc.html',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658454_1_fastqc.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1VfOQiQY94T0oPinRYaHNC',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7egtlsEqtflhOB1IlLD5f4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2KpA9A4PvsbsvFJm9C0L1d',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'doctools.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/doctools.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5E5cmPkmdKLQImsmgjzHA8',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5OIk9kgaxBpH07NH51vFuO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4u1K00cP9ZUXiANBmn2LOV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_strand_info.line_14.id_54.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_strand_info.line_14.id_54.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'ONPpcRDqIUonIO03zRmkZ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(low).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/raw_data_qualimapReport/coverage_profile_along_genes_(low).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '56nLL4fVECY4LwEAeHdOaa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'h2URGWhOijj4eRCIT6iro',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'searchtools.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/searchtools.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1eKVCLNgPVbg8t3JlaunBC',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_align.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_align.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6KAoKWjSLkUqe9HKIoeeGD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3B8qF1DNtVUciNZlVo2E4D',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'mdupsBams',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/mdupsBams',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4yZrHrWfTtYDfzLNmwpffc',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (Total).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Coverage Profile Along Genes (Total).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4sX8LcVQqyhhrl5EjJrbHS',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4WndyRD8TuzABAu3Q9J2pz',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Making_dictionary_File.line_113.id_9.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Making_dictionary_File.line_113.id_9.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'MToXdlltPRRuxBQbcMVF4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5IxexhyLSkmdPAhf93z41y',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'wbWdvrgbgNhnPbKUPFphf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2qIzsLRlitn0kk2b3bVQtB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_forwardStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658454_forwardStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '72b15UNsXw6WPYfkt8lA1u',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_22.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_22.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1PcA7bI16u7j0lYi4VcTZ0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6kvazVuW88P9HtkpeqVsr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Junction Analysis.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Junction Analysis.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5ETf0DnjjPeTiSbtRHQ7Fp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.flagstat',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.flagstat',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'O4gMBQ6Hfr32gDHoRL9KL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_lib_complex.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_lib_complex.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2z8dVRDPs8kz9Fw6rOfaB5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bgfooter.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/bgfooter.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '77vXjckechWAkQ2q2dPwgm',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3yDpSSH4O1wHumthXe3dxH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'mdA9lFnLtLKblKh992vWv',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'samplesSheet.txt',
        'path': 'output/sikRun',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/samplesSheet.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ZNnjjSbtjFngJYr7smyxM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2PUl6z2xoQf3bC9OjzT2ap',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genes.gtf',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genes.gtf',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'eG8VR83QD1dHOqOOxgc0o',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_all_features.line_109.id_58.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_all_features.line_109.id_58.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4wPiivFHGinA4csyBM09y8',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_2_fastqc.html',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658454_2_fastqc.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'XLT2J2TQ3xToHtnVDtNhp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4qSBWsmFp4hcUvWUXhif0L',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Generating_MultiQC_report.line_57.id_73.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Generating_MultiQC_report.line_57.id_73.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5SiEe3lddSyQhfO2tLbBHB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(low).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport/coverage_profile_along_genes_(low).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1FIPUXPU7nZYIbKeSWyLiO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_60.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_60.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '44H0fuuD9wyaOCf3E2Bjmb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'wvzcFyXB1TE8YESGybuwV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc',
        'path': 'output/sikRun/logs/toolsOpts',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/toolsOpts/multiqc',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4GhQLuoX3R9tc9CtJHgOn6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5Oszc8B1RSZlsWl3xsQo5Z',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_1_fastqc.html',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658460_1_fastqc.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6kcJvUQKEtwXuodmz2BM64',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ReverseStrandedCounts.txt.summary',
        'path': 'output/sikRun/countFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/countFiles/ReverseStrandedCounts.txt.summary',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51XkoiuNIQguNx1lyyKK0f',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '14PO83Yn2YbEshPZ3ANiI1',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ReverseStrandedCounts.txt.line_59.id_52.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6fu0a12I44uTT88UGdM0in',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_nonStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658460_nonStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'oR8Nna8KO4TNLil5dyXas',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_63.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6DDBGD2wcyuEXOKlKaRKMb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_featureCounts.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_featureCounts.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5VGzwUjwZmQJRfjlrSU8PJ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_all_features.line_109.id_58.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_all_features.line_109.id_58.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4LfXZiYVhSKUFq9COBghci',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6jWIgCs02j3RapynLnAVhs',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1wvWWvE3Crz8fg0N8U09U4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fastqc',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/fastqc',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6fOskSz2Nqi8lGPPZIqo6t',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_17.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_17.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4jzpnZLIfmd0PzOExdlcys',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658460.line_88.id_21.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7KHWkkE3zvYtPvvznutwS5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.Making_STAR_index.line_31.id_16.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.Making_STAR_index.line_31.id_16.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6G3uG09z8SBylErTxjCZdp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(high).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport/coverage_profile_along_genes_(high).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5nWyIuNzbEcojBN35ol7cI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'job.err',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/job.err',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1q1cY1mYRs3R8E0dijIPXi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.flagstat',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.flagstat',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7TmDjafACKxxa3yMYAx96u',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_nonStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658454_nonStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5zfpUfoVfyPvdpL6O9hcy5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualimap',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/qualimap',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6jHAMQWaQnrYJ9jDKjCxzo',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'rnaseq_qc_results.txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658454',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/rnaseq_qc_results.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3VLizHWyR2Tk76hFNVqQmJ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (High).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Coverage Profile Along Genes (High).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1QUbGR4BhDqvwFDaZZhMZ1',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51yjXvVjlpKcnEEznzZWna',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6qdq1hlPSs25c44uFF2z48',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'theBams',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/theBams',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1cvXGFZSXV71KHmo1tjBge',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_geneIds.txt_file.line_77.id_57.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_geneIds.txt_file.line_77.id_57.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4YE3GAD8DoQxEWQDPOy2LI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '9F3Q1XHz6VkQYMxQPbILD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_sources.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_sources.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'Hk9nwJkV4vrrP9ZKP3Txd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Transcript coverage histogram.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Transcript coverage histogram.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6yzfrUjT4bTCxBUCaa15TV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikLog.Getting_versions_of_tools_in_use.line_132.id_1.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'ogbtsG13fop2VnfzGL1tF',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Indexing_FASTA_file.line_125.id_13.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1RSSgUTcBytxqc2S7fCYKf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_66.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_66.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4F4mzXCkVZeApSQeNsIbdK',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_SJ.out.tab',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658460_SJ.out.tab',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3vVLaYo9HF1vGTmVjBFAjm',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_forwardStranded.bw',
        'path': 'output/sikRun/coverageFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/coverageFiles/SRR1658460_forwardStranded.bw',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5W2TFRXj4KztYEd2xsuAPM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'download.log',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/download.log',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2PotbhY3LwSfe1sDdhbbJ3',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'down-pressed.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/down-pressed.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '24DRt6UG0JT3qv0DLqufYh',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_Log.final.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658454_Log.final.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51STqBICEnT2iMH4IjekS8',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3YFsLppkOvh9kvpoSaMOVg',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_samtools_stats.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_samtools_stats.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3pG4SPVSFEu7gWSWVhFNIy',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups.stats',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups.stats',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Tqiz1y2qn8DFdJK9FbPNQ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups.stats',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups.stats',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4rTy031KVyBoUfdokG6B1K',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_18.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_18.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51h12fpdHh645htKPIGcpK',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'RpSn8zBtyM4SRGutHsU6l',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genome.dict',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.dict',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3KgqDwhIvtAkI4gKLu5pY2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_14.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_14.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'xzeKOVEuxcbqh2CU8pkUD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_55.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_55.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6STMFJM5dcsh26QWYsIZmi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4pYVW2bMTxqlnnIz0VN2Sk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (Low).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Coverage Profile Along Genes (Low).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1Xfna0TrECTfWCU4PnsW7K',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_62.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_62.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1QUTvg8s7gi3GcTKwIXcBk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'minus.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/minus.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '17cqatHjU2OnBxcmKaUc1L',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_geneIds.txt_file.line_77.id_57.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_geneIds.txt_file.line_77.id_57.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '11UMLu2rB5slUIrkH41W5z',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_data.json',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_data.json',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '42tsbbIt58hB4ZV5kLLzEM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5AZW3sE8YeBuE0QRtqtGSM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6ZbGJRBZUDSNjXJ60SkgWN',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_samtools_idxstats.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_samtools_idxstats.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1uvlyHBFGkd2s2H3PeLZGx',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'doctools.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/doctools.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '679uGtBQ7Tc8KEQn0i8jVr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '646y2EfmYBJLlntfnMDjCW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_7.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_7.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4Ejpq5PtS8MPwLDU4eJEh6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5sa19cXOAPWuvXThxgOv09',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SA',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/SA',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4SZF1Mj1QmNeq9wIe69rJ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6rgSD1Nh7i6jZwoE5v2xwi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_picard_dups.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_picard_dups.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3ztCcU4KMvfXELmae6xyqY',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'jquery.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/jquery.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '73UDv8oEfUFxAHg2g1ghN4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7ObZ0ESleK88ZFsMfcKCng',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_1.siklog',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/.SRR1658454_1.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5DeTPX0RhvLWtmhD4dSZrC',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'down.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/down.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'zz6iq0bsfYQ4PEuYmwkVA',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genome.chromSizes',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.chromSizes',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4EYYwk3Ye00kPIe6WafAa6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3EUuEZ3yh2pSfjCrzXAJ0u',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6W1Nzn64nfc28ZmA9PsmD9',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'nWct4EvrOnursYbqok6ca',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1LWI837pZHcVNLSmz5kTWZ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'up.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/up.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2wlk3Hu4M2vb0wd6ur9LAs',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_65.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_65.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4fTt56NiOoscySN6v2aUME',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment-close.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/comment-close.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5VAIPx0QiqUVv3TB3WWYNW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4bxBcTaPwbGq7u9jusCKYs',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1KKg6IqmyAtR8yexOuHEfX',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2vtQbvWA5fD9AkS3lA81Sq',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_56.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_56.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1FKdZgyLWsPeq9M07LDYYF',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_2.siklog.line_39.id_68.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5Nb55wWnj2E9hzmrYxQ0rY',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_Log.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658460_Log.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2WQ0yuzEY5J2vCVdRUVV2a',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5yU3xxlFK0B2pY9ec6nSVE',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_all_features.line_109.id_58.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_all_features.line_109.id_58.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '23YL1ZJgAxQChJ8k9eAsuo',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_gc_summary.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_gc_summary.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'aQprBzd9WJgZnDwaCYNg4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_111.id_37.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6Ps2SffKBFmAdoEWnAyB3m',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'star',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/star',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5JzUZaUE2iWJVDlnBLex0K',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_160.id_30.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2oJDm2szmYBqU36PVQiZgQ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualiMap',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/qualiMap',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3z7gsWwz56VVmUYefsBWaL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.Making_STAR_index.line_31.id_16.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.Making_STAR_index.line_31.id_16.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3bDLQ1wEbTr2eCr3ExqjnR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1mGaIvmlVzq2ugEdmtUgbH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_124.id_39.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '33aESVCFLm7EzKkgP8sMSp',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_132.id_40.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1yUaVRhyISjZbL0ZbiQksn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5LovWymrRKCPlNgm9C9RLk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_insert_size_hist.pdf',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_insert_size_hist.pdf',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1Yw0qaKyLYExI7qLn50Zwf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_gc_summary.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_gc_summary.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7Ig02BQXdTLD5qpUlCjcXU',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (Low).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Coverage Profile Along Genes (Low).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7WgLiMwGIPUjFBcON0hJii',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_SJ.out.tab',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658454_SJ.out.tab',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4mYSKzROUAUONAVmNAd6wE',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'agogo.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/agogo.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5kRNJs5aHdtP3RhkY9bVKq',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7gHfu3flUq8B5p9R1Lpq75',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_124.id_35.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '102MPcwDIXEaT7lXrFgMyk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7fZoJ2sTZrmdSo1SdnUuC0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'coverage_profile_along_genes_(total).txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/raw_data_qualimapReport/coverage_profile_along_genes_(total).txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5N6p0b1gRtAeArC3PzXRK2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4VdheG7LeYg4vjWMIF82Gt',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_111.id_33.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1mv5xulx52FFmGqz1jm237',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6KpvRE9U5QDPXkasrn2hlO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Coverage Profile Along Genes (Total).png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Coverage Profile Along Genes (Total).png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'wndjCLVwv7FgoTDDrw1b4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_picard_insertSize.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_picard_insertSize.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'RkRKWyfUyRWYQp5uaOVwF',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '550kWk9u3ppK6DrmNeBBbk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'strandInfo',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/strandInfo',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1N98ncUbZcVQ86fSt5IrRa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658454_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658454_1.siklog.line_39.id_67.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'OqqQV6TtSJkekqCBeghVa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment-bright.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/comment-bright.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6JYJ4Ixns6GnQeTwNkvSb0',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'comment-close.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/comment-close.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2ZbXyAxYd23pdqhhEGLZOv',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '49I04Qw9WNz1EnyVSPEL2d',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '62lYIjOKrkwHLW0XoDMl3P',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_strand_info.line_14.id_54.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_strand_info.line_14.id_54.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6mcNaOcRUkXLWasX6V1L5p',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genome.fa',
        'path': 'output/sikRun/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.fa',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6cMVv4n5uaAXZbcmrusceI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_118.id_38.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6ksCyuuY3tdDMAri3pSPum',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_sorted_mdups_gc.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658454_sorted_mdups_gc.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'xTYFE1hD0jJ62CFNai9al',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'STAR',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/STAR',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '39clb0N8fWg7l2f0zuCPiT',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_44.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5Mg642cRMn8upoFYbbvzkl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_2_fastqc.html',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658460_2_fastqc.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1e4AKS7GR6C4NuVA1abDnn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6V8gCzmkV4ucil5AMJtqNW',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3tGdAtaQJrFzTImsdtIDDi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_19.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_19.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6emMzBnUw2LOYM3OzdZ3zV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'genomeParameters.txt',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/genomeParameters.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1FADUAuQ3ECDjxcGpdyDgR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fastqc',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/fastqc',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3K1vHgWvkyPDxY6WNm94Hf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'underscore.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/underscore.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'ljN6yMEKqtDQNWg8IZ61f',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_geneIds.txt_file.line_77.id_57.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_geneIds.txt_file.line_77.id_57.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '16oU5rS1HeZ2i5afssO1AZ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_ForwardStrandedCounts.txt.line_59.id_51.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2Rw4WGYz85FPHi3lNfJxvP',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'chrName.txt',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/chrName.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3XdM8u3yTfyyTi3UGNNANS',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_118.id_34.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4rI3sbeFhyXeB3nqFIy72K',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'chromSizes',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/chromSizes',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2f61UQ58Uo7yMq4GReCXwv',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'xIAKpPMz3LZfWlofuaBgH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikExonicRate.getting_Int_ra_er_genic_rates_forsikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_64.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ayHYTf748mVI6mnQ3lhXL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_Log.progress.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658454_Log.progress.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3Tf1rBN6fVZsl1gwe5wK2y',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'gtfFile',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/gtfFile',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'sAo6i0KJSHZFcvkuAGZQM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658460_sorted_mdups_insert_size.siklog',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/.SRR1658460_sorted_mdups_insert_size.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5XtP254hy9AM6biESWlvqr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.samtools_flagstat_metrics_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_160.id_31.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'MmatP1nExN2M1L0MMGlQD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'rnaseq_qc_results.txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658460',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/rnaseq_qc_results.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4bWhRoTmqvo4mjt4b1kIQt',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Annotation_Genes_genes.gtf_to_sikRun_refFiles.line_51.id_6.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6VPV402f43GBFXyITm89UR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_1.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_1.siklog.line_39.id_69.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6NW3a0Oo6d48rvrM7tHdDo',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Copying_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_.._references_iGenomes_Saccharomyces_cerevisiae_Ensembl_R64_1_1_Sequence_WholeGenomeFasta_genome.fa_to_sikRun_refFiles.line_51.id_4.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1oQMwTxNCJEo6LcNiAURoH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_gc.metrics',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_gc.metrics',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2g59NDAaXW3MHFgx8PJXjN',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_53.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_53.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4PN3zOjl2R5sXjphyBxRMh',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_sorted_mdups_gc.pdf',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658454_sorted_mdups_gc.pdf',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1ggdiqw3mWM6jsQaqUdOiT',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'job_env.out',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/job_env.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7KcpwDaMQm6XAsECfaVuz3',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4p2Kz8rMifEP3BZ3tGXNi2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '155uaBA87Yb4qoJuC1AXrI',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_2.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_2.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'ldw9MojOWtzXWYuomefp4',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'basic.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/basic.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6tiEJpMQlwRTKEopoqR0FU',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_12.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_12.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3pyIK8M0fviLAQa07dzAUJ',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.Counting_features_sikRun_countFiles_NonStrandedCounts.txt.line_59.id_50.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'TlN3u3Cd474Ett8Ye9OOd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_strand_info.line_14.id_54.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_strand_info.line_14.id_54.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6vEKppS7ifIRvviCfCrF7Q',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_2_fastqc.zip',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/SRR1658454_2_fastqc.zip',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4fBkOUBqf1py1xKFr8PtHL',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'websupport.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/websupport.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4xQrgVCx4TIpzqT57d0Rfi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Reads Genomic Origin.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/images_qualimapReport/Reads Genomic Origin.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6Y01ZK8ycLRE0T2kzYDZh5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Generating_MultiQC_report.line_57.id_73.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Generating_MultiQC_report.line_57.id_73.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'BWjc9CI9OaS1YeR1QT0MR',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SAindex',
        'path': 'output/sikRun/refFiles/genome.starIdx',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/refFiles/genome.starIdx/SAindex',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6YrYuU43mSP1nY1Oio4dRn',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_Log.final.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658460_Log.final.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1MxcaMrQWBvp3k0FMCeS4p',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualimapReport.html',
        'path': 'output/sikRun/qualiMapResults/SRR1658460',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/qualimapReport.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2dq3HMIB0OGHz6MPnheoLB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_71.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_71.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4Rs9OFB2sHhkPklUxIofqM',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_sorted_mdups_gc.pdf',
        'path': 'output/sikRun/bamFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/bamFiles/SRR1658460_sorted_mdups_gc.pdf',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '20BRhMm0dh33OxAf8WeOKV',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6D1uNbVJHB67V74wkXVOcu',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.making_degust_file_with_protein_coding_features.line_115.id_59.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7Ad10dgKYTsQ9R17emti7l',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualimap_logo_small.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/qualimap_logo_small.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7UH215jvmDQzX73m4oSJCq',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'samtools',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/samtools',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6xQRVz45TDVwpFykYIAnoi',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'picardDictFile',
        'path': 'output/sikRun/logs/refFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/refFiles/picardDictFile',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5SLXWWORCFMk11CC2GFgMg',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'file.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/file.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7SWJTKJXBSKu7BUH856iCd',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'up.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/up.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '238zR8LEnqBNF3RMNcU0jK',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'multiqc_picard_gcbias.txt',
        'path': 'output/sikRun/multiqc_data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/multiqc_data/multiqc_picard_gcbias.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1fskFildwY1ZukUz4sWVK6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'fqMap',
        'path': 'output/sikRun/logs/samples',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/samples/fqMap',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '338pvhtwA6XFlvJe9vHGbl',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Reads Genomic Origin.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Reads Genomic Origin.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1A2FZ9xFI0TAK3eh9pfOJt',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Making_dictionary_File.line_113.id_9.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Making_dictionary_File.line_113.id_9.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2EIJPstxGz4fYgkkbqU5MB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_25.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_25.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7WM2PVSAZ3Eyah0SDYcdA3',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'ReorderSam',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/ReorderSam',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '67CMIrIjiWHIX5eHwo1uzO',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'samplesSheet',
        'path': 'output/sikRun/logs/samples',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/samples/samplesSheet',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3MYFNVMCyOW9yp880UoBLk',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658460_counts.txt',
        'path': 'output/sikRun/qualiMapResults/SRR1658460',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/SRR1658460_counts.txt',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4dZe5HtQ4U0qlmbahWImK5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'agogo.css',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/agogo.css',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2TXFWaiyFDS78lVI16Lmhh',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'Transcript coverage histogram.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/images_qualimapReport/Transcript coverage histogram.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3GTckEUA1dV2X5tzO2U1Lr',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikSTARaligner.STAR_aligning_SRR1658454.line_88.id_20.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'W5CKl61WxPjoQz9h0avUa',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_47.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ftEc2btLmV5Vp5Pr2swHP',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7hS1K0VpV6S9YENilx54p5',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'underscore.js',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/underscore.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6gEHYMSjIfCo7SX31fZFJB',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'featureCounts',
        'path': 'output/sikRun/logs/toolsOpts',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/toolsOpts/featureCounts',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '51fZFdcRVmz2pGyu1nxFDD',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_45.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6GDX8DodhNWUaHjQjl5uz7',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_32.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_32.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '69qIw00WPPEuKq5YJf8vlz',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3LnssjC6T2KjE0cH2hC1w1',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bgfooter.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658454/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/css/bgfooter.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '50N9X2x94RUf5oO89T7cNy',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658460_Aligned.out.bam.line_33.id_24.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '23RU9t6zQrunJO24LE9Yjy',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'RNAsik.bds.20180718_161751_947.dag.js',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947.dag.js',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5e2yV3tFotmTJv2iaVucA2',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'featureCounts',
        'path': 'output/sikRun/logs/data',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/data/featureCounts',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '67x7SKrLIAu1RnYJUel5cP',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658460_sorted_mdups.bam.line_40.id_46.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ac7OG8yvyrEldbcG2OE8K',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'RNAsik.bds.20180718_161751_947.report.yaml',
        'path': 'output',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947.report.yaml',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4iUujPk8mxIoYej61hPUf',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': '.SRR1658454_2.siklog',
        'path': 'output/sikRun/fastqcReport',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/fastqcReport/.SRR1658454_2.siklog',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '30mwjBGOffHhCvU21jaMOy',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.sorting_with_samtools_sikRun_alignerFiles_SRR1658454_Aligned.out.bam.line_33.id_23.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '5xYmwIS3Bsa6YqqV28Mso6',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'sys.sikLog.line_74.id_3.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/sys.sikLog.line_74.id_3.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '4ob3UFnIWHXWN91XHJth7V',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.Running_FastQC_on_scratch_df22_andrewpe_laxytest_4wUnYkwDz4j0mm4kyd0qIn_output_.._input_SRR1658460_2.fastq.gz_and_logging_to_sikRun_fastqcReport_.SRR1658460_2.siklog.line_39.id_70.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '29j5Tcy1IyFk9z1a1CIn4Y',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'SRR1658454_Log.out',
        'path': 'output/sikRun/alignerFiles',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/alignerFiles/SRR1658454_Log.out',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '48faj47vG2PSGE2PdpJl9E',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.stderr',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_42.stderr',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'dClhCdhtFGbXO1m4T5JoH',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikQC.gathering_metrics_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_132.id_36.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '7Juh3cdvBlRLs8khGwZkvU',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'minus.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/minus.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1bBjv2S1NLfKfwKcjxMY7i',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'bgtop.png',
        'path': 'output/sikRun/qualiMapResults/SRR1658460/css',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658460/css/bgtop.png',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2uUp20aLTPoL7KpYpyrCvF',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'qualimapReport.html',
        'path': 'output/sikRun/qualiMapResults/SRR1658454',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/qualiMapResults/SRR1658454/qualimapReport.html',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'aTQxOeh9SJZ06LFGvQ26g',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.sh',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCoverage.Getting_coverage_files_bigWig_for_strand_strand_for_sikRun_bamFiles_SRR1658454_sorted_mdups.bam.line_40.id_43.sh',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '1CiQCUCkrCoLHBaqz5raRb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.exitCode',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658460_sorted.bam.line_72.id_27.exitCode',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '6P55YzMm36dNbDrNbT5HEb',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikRefFiles.Make_chrom_sizes_file.line_134.id_11.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': 'eRQ8LCrbCRFfO4KBgAV4V',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'featureCounts',
        'path': 'output/sikRun/logs/versions',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/sikRun/logs/versions/featureCounts',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '2KQDMytgsfI6X6cPXaSZ3X',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikProcBam.markiing_duplicates_with_picard_MarkDuplicates_sikRun_bamFiles_SRR1658454_sorted.bam.line_72.id_26.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    } as LaxyFile, {
        'id': '3YJPMRKP9VABBaH2eTxHoN',
        'owner': '51f6boKqYKhlm9S0CoCFOt',
        'name': 'task.sikCounts.getting_strand_info.line_14.id_54.stdout',
        'path': 'output/RNAsik.bds.20180718_161751_947',
        'location': 'laxy+sftp://7j4BZgcDZcRZGfXZismNCB/4wUnYkwDz4j0mm4kyd0qIn/output/RNAsik.bds.20180718_161751_947/task.sikCounts.getting_strand_info.line_14.id_54.stdout',
        'checksum': null,
        'fileset': '2a5rRC13IqBZLXva9CnMkS',
        'type_tags': [],
        'metadata': {}
    }]
};
