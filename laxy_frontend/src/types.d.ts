declare function require(path: string): any;

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

declare interface MdDialog extends Element {
    open: Function;
    close: Function;
}

declare interface LaxyFile {
            id: string;
            name: string;
            path: string;
            location: string;
            owner: number | string;
            checksum: string;
            metadata: any;
            type_tags: string[];
}

declare interface LaxyFileSet {
            id: string;
            name: string;
            owner: number | string;
            files: LaxyFile[];
}
