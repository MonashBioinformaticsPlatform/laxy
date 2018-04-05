// Test data
import {SampleSet} from './model';

export const DummySampleList: SampleSet = {
    name: 'Dummyset',
    items: [
        {
            'id': 'kazd4mZvmYX0OXw07dGfnV',
            'name': 'SampleA',
            'condition': 'wildtype',
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
            'condition': 'mutant',
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
            'condition': 'wildtype',
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
            'condition': 'mutant',
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
