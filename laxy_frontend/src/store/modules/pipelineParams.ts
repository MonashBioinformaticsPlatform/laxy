import cloneDeep from 'lodash-es/cloneDeep';
import { make } from 'vuex-pathify';

import { ILaxyFile, LaxyFileSet, ISample } from '../../types';
import { filenameFromUrl } from '../../util';

const initial_state: any = {
    // a list of files the backend will fetch as input
    fetch_files: [] as ILaxyFile[],
    description: '',

    // params: {},

    // genome: AVAILABLE_GENOMES[0].id,
    // user_genome: {
    //     fasta_url: '',
    //     annotation_url: '',
    // },
    // pipeline_version: '1.5.4',
    // pipeline_aligner: 'star',
}

const getters: any = {
    ...make.getters(initial_state),
    // exampleGetter(state: any, getters: any, rootState: any, rootGetters: any) { },
    generateFetchFilesList: (state: any, getters: any, rootState: any, rootGetters: any) => {
        const fetch_files: ILaxyFile[] = [];

        let fastaUrl = '';
        let annotUrl = '';
        if (rootState.use_custom_genome && state.user_genome != null) {
            fastaUrl = state.user_genome.fasta_url;
            annotUrl = state.user_genome.annotation_url;
        }

        if (rootState.use_custom_genome && fastaUrl && annotUrl) {
            let annotType = "annotation";
            if (annotUrl.includes(".gff")) {
                annotType = "gff";
            } else if (annotUrl.includes(".gtf")) {
                annotType = "gtf";
            }

            fetch_files.push(
                ...[
                    {
                        name: filenameFromUrl(fastaUrl) || "", //"genome.fa.gz",
                        location: fastaUrl.trim(),
                        type_tags: ["reference_genome", "genome_sequence", "fasta"],
                    } as ILaxyFile,
                    {
                        name: filenameFromUrl(annotUrl) || "", //"genes.gff.gz",
                        location: annotUrl.trim(),
                        type_tags: ["reference_genome", "genome_annotation", annotType],
                    } as ILaxyFile,
                ]
            );
        }

        const samples = rootState.samples;
        for (let i of samples.items) {
            for (let f of i.files) {
                // ['R1', 'R2']
                for (let pair of Object.keys(f)) {
                    const sampleFile: ILaxyFile = cloneDeep(f[pair]);

                    if (sampleFile == null) continue;
                    if (sampleFile.location == null) continue;

                    sampleFile.metadata = sampleFile.metadata || {};
                    sampleFile.type_tags = sampleFile.type_tags || [];
                    sampleFile.metadata["read_pair"] = pair;

                    let doppelganger = pair == "R1" ? "R2" : "R1";
                    if (f[doppelganger] != null) {
                        sampleFile.metadata["paired_file"] = f[doppelganger].name;
                    }

                    sampleFile.type_tags.push("ngs_reads");

                    fetch_files.push(sampleFile);
                }
            }
        }

        return fetch_files;
    }
};

const mutations: any = {
    ...make.mutations(initial_state),
};

const actions: any = {
    // async exampleAction({ state, commit, rootState, rootGetters}: any, params: any) { }
};

export const pipelineParamsModule = {
    namespaced: true,
    state: initial_state,
    getters: getters,
    mutations: mutations,
    actions: actions,
}

export default pipelineParamsModule;