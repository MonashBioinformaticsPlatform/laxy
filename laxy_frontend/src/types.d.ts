declare function require(path: string): any;

declare interface Sample {
    id?: string;
    name: string;
    files: any[];
    condition?: string;
}

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
        fastq_ftp?: string;
    }

declare interface ReferenceGenome {
    id: string;
    organism: string;
}

declare interface MdDialog extends Element {
    open: Function;
    close: Function;
}
