import Vuex from 'vuex';
import {SampleSet} from './model';

export const ADD_SAMPLES = 'add_samples';
export const SET_SAMPLES = 'set_samples';

export const Store = new Vuex.Store({
    strict: true,
    state: {
        samples: new SampleSet(),
    },
    getters: {
        samples: state => {
            return state.samples;
        },
        sample_cart_count: state => {
            if (state.samples.items != undefined) {
                return state.samples.items.length;
            }
            return 0;
        }
    },
    mutations: {
        [ADD_SAMPLES](state, samples: Sample[]) {
            // if (state.samples.items == undefined)
            state.samples.items.push(...samples);
        },
        [SET_SAMPLES](state, samples: SampleSet) {
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
