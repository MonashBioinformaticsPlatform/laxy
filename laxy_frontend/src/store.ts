import Vuex from 'vuex';

export const ADD_SAMPLES = 'add_samples';
export const SET_SAMPLES = 'set_samples';

export const Store = new Vuex.Store({
    strict: true,
    state: {
        samples: [] as Sample[],
    },
    getters: {
        samples: state => {
            return state.samples;
        }
    },
    mutations: {
        [ADD_SAMPLES](state, samples: Sample[]) {
            state.samples.push(...samples);
        },
        [SET_SAMPLES](state, samples: Sample[]) {
            state.samples = samples;
        }
    },
    actions: {
        add_samples({commit, state}, samples) {
            commit(ADD_SAMPLES, samples);
        },
        [SET_SAMPLES]({commit, state}, samples) {
            commit(SET_SAMPLES, samples);
        },
    },
});
