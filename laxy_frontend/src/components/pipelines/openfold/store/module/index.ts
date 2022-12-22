import { make } from 'vuex-pathify';

//const pipeline_name = 'openfold';

const initial_state: any = {
    input: { fasta: ">GB1\nMQYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE\n" },
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