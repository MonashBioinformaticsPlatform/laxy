import { make } from 'vuex-pathify';

const initial_state: any = {
    //flags: { all: false },
    strandedness: 'auto',
    debug_mode: false,
    has_umi: false,
    min_mapped_reads: 5,
    save_reference_genome: true,
    save_genome_index: false,
    skip_trimming: false,
};

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

export const storeModule = {
    namespaced: true,
    //name: pipeline_name,
    state: initial_state,
    getters: getters,
    mutations: mutations,
    actions: actions,
}

export default storeModule;