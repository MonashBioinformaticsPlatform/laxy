import * as _ from 'lodash';
import Vuex from 'vuex';
import axios, {AxiosResponse} from 'axios';
import {SampleSet} from './model';
import {WebAPI} from './web-api';

export const ADD_SAMPLES = 'add_samples';
export const SET_SAMPLES = 'set_samples';
export const SET_SAMPLES_ID = 'set_samples_id';
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
        [SET_SAMPLES_ID](state, id: string) {
            state.samples.id = id;
        },
        [SET_PIPELINE_PARAMS](state, params: any) {
            state.pipelineParams = params;
        },
        [SET_PIPELINE_DESCRIPTION](state, txt: any) {
            state.pipelineParams.description = txt;
        }
    },
    actions: {
        async [SET_SAMPLES]({commit, state}, samples) {
            const preCommit = _.cloneDeep(state.samples);
            // optimistically commit the state
            commit(SET_SAMPLES, samples);
            const data = {
                name: samples.name,
                samples: samples.items
            };
            try {
                if (samples.id == null) {
                    const response = await WebAPI.fetcher.post('/api/v1/sampleset/', data) as AxiosResponse;
                    // samples.id = response.data.id;
                    // commit(SET_SAMPLES, samples);
                    commit(SET_SAMPLES_ID, response.data.id);
                } else {
                    const response = await WebAPI.fetcher.put(
                        `/api/v1/sampleset/${samples.id}/`, data) as AxiosResponse;
                }
            } catch (error) {
                // rollback to saved copy if server update fails
                commit(SET_SAMPLES, preCommit);
                console.log(error);
            }
        },
        async [SET_PIPELINE_PARAMS]({commit, state}, params: any) {
            commit(SET_PIPELINE_PARAMS, params);
        }
    },
});
