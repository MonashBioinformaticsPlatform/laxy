import Vuex from 'vuex';
import {SampleSet} from './model';

export const ADD_SAMPLES = 'add_samples';
export const SET_SAMPLES = 'set_samples';
export const SET_PIPELINE_PARAMS = 'set_pipeline_params';
export const SET_PIPELINE_DESCRIPTION = 'set_pipeline_description';

export const Store = new Vuex.Store({
    strict: true,
    state: {
        samples: new SampleSet(),
        pipelineParams: {
            reference_genome: 'hg19',
            description: '',
        },
    },
    getters: {
        samples: state => {
            return state.samples;
        },
        pipelineParams: state => {
            return state.pipelineParams;
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
        },
        [SET_PIPELINE_PARAMS](state, params: any) {
            state.pipelineParams = params;
        },
        [SET_PIPELINE_DESCRIPTION](state, txt: any) {
            state.pipelineParams.description = txt;
        }
    },
    actions: {
        add_samples({commit, state}, samples) {
            commit(ADD_SAMPLES, samples);
        },
        [SET_SAMPLES]({commit, state}, samples) {
            commit(SET_SAMPLES, samples);
        },
        [SET_PIPELINE_PARAMS]({commit, state}, params: any) {
            commit(SET_PIPELINE_PARAMS, params);
        }
    },
});
