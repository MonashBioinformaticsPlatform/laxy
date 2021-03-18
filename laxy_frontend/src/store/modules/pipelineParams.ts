import { make } from 'vuex-pathify';

import { ILaxyFile, LaxyFileSet, ISample } from '../../types';

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
    // exampleGetter(state: any, getters: any, rootState: any, rootGetters: any) { },
    ...make.getters(initial_state),
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