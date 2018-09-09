// import {LaxyFile} from './model';

// declare function require(path: string): any;

declare interface ENASample {
    // pair?: ENASample,
    run_accession?: string;
    study_accession?: string;
    experiment_accession?: string;
    sample_accession?: string;
    library_strategy?: string;
    instrument_platform?: string;
    read_count?: number;
    fastq_bytes?: number;
    fastq_md5?: string;
    fastq_ftp?: any[];
}

declare interface ReferenceGenome {
    id: string;
    organism: string;
}

declare interface ILaxyFile {
    id: string;
    name: string;
    path: string;
    location: string;
    owner: number | string;
    checksum: string | null;
    fileset: string | null;
    metadata: any;
    type_tags: string[];
    // fullPath: string;
}

declare interface LaxyFileSet {
    id: string;
    name: string;
    owner: number | string;
    files: ILaxyFile[];
}

declare interface ViewMethod {
    text: string;
    icon: string;
    tags: string[];
    method: Function;
}
