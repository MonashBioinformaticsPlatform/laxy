// import * as _ from 'lodash';
import filter from 'lodash-es/filter';
import pick from 'lodash-es/pick';
import cloneDeep from 'lodash-es/cloneDeep';
import update from 'lodash-es/update';
import head from 'lodash-es/head';
import keyBy from 'lodash-es/keyBy';

import Vue from 'vue';
import Vuex from 'vuex';

import pathify, { make } from 'vuex-pathify';

import axios, { AxiosResponse } from 'axios';
import { ComputeJob, LaxyFile, Sample, SampleCartItems } from './model';
import { WebAPI } from './web-api';
import { vueAuth, AuthOptions } from './auth';

import AVAILABLE_GENOMES from "./config/genomics/genomes";
import { ILaxyFile, LaxyFileSet, ISample } from './types';
import { addPipelineRoutes } from './routes';

export const SET_ONLINE_STATUS = 'set_online_status';
export const SET_BACKEND_VERSION = 'set_backend_version';
export const SET_POPUPS_ARE_BLOCKED = 'set_popups_are_blocked';
export const SET_POPUP_BLOCKER_TESTED = 'set_popup_blocker_tested';
export const SET_POPUP_WARNING_DISMISSED = 'set_popup_warning_dismissed';
export const AUTHENTICATE_USER = 'authenticate_user';
export const SET_USER_PROFILE = 'set_user_profile';
export const ADD_SAMPLES = 'add_samples';
export const SET_SAMPLES = 'set_samples';
export const CLEAR_SAMPLE_CART = 'clear_sample_cart';
export const SET_SAMPLES_ID = 'set_samples_id';
export const SET_PIPELINE_PARAMS = 'set_pipeline_params';
export const SET_PIPELINE_PARAMS_VALID = 'set_pipeline_params_valid';
export const SET_PIPELINE_DESCRIPTION = 'set_pipeline_description';
export const SET_PIPELINE_GENOME = 'set_pipeline_genome';
export const SET_JOBS = 'set_jobs';
export const SET_FILESET = 'set_fileset';
export const SET_VIEWED_JOB = 'set_viewed_job';
export const SET_API_URL = 'set_api_url';
export const SET_JOB_ACCESS_TOKEN = 'set_job_access_token';
export const SET_GLOBAL_SNACKBAR = 'set_global_snackbar';
export const SET_PIPELINES = 'set_pipelines';

export const PING_BACKEND = 'ping_backend';
export const FETCH_USER_PROFILE = 'fetch_user_profile';
export const FETCH_JOBS = 'fetch_jobs';
export const FETCH_FILESET = 'fetch_fileset';
export const FETCH_JOB = 'fetch_job';
export const FETCH_PIPELINES = 'fetch_pipelines';

interface JobsPage {
    total: number;  // total number of jobs on all pages
    jobs: ComputeJob[];    // jobs for just the page we've retrieved
}

Vue.use(Vuex);

const initial_state: any = {
    //export const Store = new Vuex.Store({
    //strict: true,
    //state: {
    online: false,
    backend_version: '',
    popupsAreBlocked: false,
    popupBlockerTested: false,
    popupWarningDismissed: false,
    user_profile: null as any,
    samples: new SampleCartItems(),
    availablePipelines: {},
    pipelineParams: {
        // a list of files the backend will fetch as input
        fetch_files: [] as ILaxyFile[],
        genome: AVAILABLE_GENOMES[0].id,
        user_genome: {
            fasta_url: '',
            annotation_url: '',
        },
        description: '',
        pipeline_version: '1.5.4',
        pipeline_aligner: 'star',
    },
    pipelineParams_valid: false,
    use_custom_genome: false,
    genome_values_valid: true,
    jobs: { total: 0, jobs: [] as ComputeJob[] } as JobsPage,
    filesets: {} as { [key: string]: LaxyFileSet },
    currentViewedJob: {} as ComputeJob,
    jobAccessTokens: {} as any,
    api_url: 'http://dev-api.laxy.io:8001',
    global_snackbar_message: '',
    global_snackbar_duration: 2000,
    //}
};

const getters: any = {
    is_authenticated: (state: any) => {
        return !!state.user_profile;
    },
    userId: (state: any): string | null => {
        if (state.user_profile) {
            return state.user_profile.id;
        }
        return null;
    },
    samples: (state: any) => {
        return state.samples;
    },
    pipelineParams: (state: any) => {
        return state.pipelineParams;
    },
    sample_cart_count: (state: any) => {
        if (state.samples.items != undefined) {
            return state.samples.items.length;
        }
        return 0;
    },
    jobs: (state: any) => {
        return state.jobs;
    },
    currentJobFiles: (state: any, getters: any) => {
        const job = state.currentViewedJob;
        if (!job) {
            return [];
        }
        const getFileset = getters.fileset;
        const infileset = getFileset(job.input_fileset_id);
        const outfileset = getFileset(job.output_fileset_id);
        const filez = [];
        filez.push(...(infileset && infileset.files || []));
        filez.push(...(outfileset && outfileset.files || []));
        return filez;
    },
    // Call like: this.$store.getters.fileset('SomeBlafooLongId')
    fileset: (state: any) => {
        return (fileset_id: string) => {
            return state.filesets[fileset_id];
        };
    },
    filesets: (state: any) => {
        return state.filesets;
    },
    // currentInputFileset: (state, getters) => {
    //     return state.filesets[(state.currentViewedJob as any).input_fileset_id];
    // },
    // currentOutputFileset: (state, getters) => {
    //     return state.filesets[(state.currentViewedJob as any).output_fileset_id];
    // },
    fileById: (state: any) => {
        return (file_id: string, fileset: LaxyFileSet | null): ILaxyFile | undefined => {
            // if the fileset isn't specified we can still retrieve the file object by searching
            // all filesets in the store.
            // TODO: make this more efficient (maybe keep an index of {file_id: file})
            if (fileset == null && state.filesets) {
                for (const fs in state.filesets) {
                    if (fs) {
                        const file = head(filter(state.filesets[fs].files, (f) => f.id === file_id));
                        if (file) return file;
                    }
                }
            }
            if (fileset != null) {
                return head(filter(fileset.files, (f: ILaxyFile) => {
                    return f.id === file_id;
                }));
            }
            return undefined;
        };
    },
    jobAccessToken: (state: any) => {
        return (job_id: string) => {
            return state.jobAccessTokens[job_id] || null;
        };
    },
    ...make.getters(initial_state),
};

const mutations: any = {
    [SET_ONLINE_STATUS](state: any, connected: boolean) {
        state.online = connected;
    },
    [SET_BACKEND_VERSION](state: any, version: string) {
        state.backend_version = version;
    },
    [SET_POPUPS_ARE_BLOCKED](state: any, blocked: boolean) {
        state.popupsAreBlocked = blocked;
    },
    [SET_POPUP_BLOCKER_TESTED](state: any, tested: boolean) {
        state.popupBlockerTested = tested;
    },
    [SET_POPUP_WARNING_DISMISSED](state: any, dismissed: boolean) {
        state.popupWarningDismissed = dismissed;
    },
    [SET_GLOBAL_SNACKBAR](state: any, params: any) {
        state.global_snackbar_message = params.message || null;
        state.global_snackbar_duration = params.duration || 2000;
    },
    [SET_API_URL](state: any, url: string) {
        state.api_url = url;
    },
    [SET_USER_PROFILE](state: any, profile_info: {}) {
        state.user_profile = profile_info;
    },
    [ADD_SAMPLES](state: any, samples: ISample[]) {
        // if (state.samples.items == undefined)
        state.samples.items.push(...samples);
    },
    [SET_SAMPLES](state: any, samples: SampleCartItems) {
        state.samples = samples;
    },
    [SET_SAMPLES_ID](state: any, id: string) {
        state.samples.id = id;
    },
    [SET_PIPELINE_PARAMS](state: any, params: any) {
        state.pipelineParams = params;
    },
    [SET_PIPELINE_PARAMS_VALID](state: any, valid: any) {
        state.pipelineParams_valid = valid;
    },
    [SET_PIPELINE_DESCRIPTION](state: any, txt: any) {
        state.pipelineParams.description = txt;
    },
    [SET_PIPELINE_GENOME](state: any, genome_id: any) {
        state.pipelineParams.genome = genome_id;
    },
    [SET_JOBS](state: any, jobs: JobsPage) {
        state.jobs = jobs;
    },
    [SET_FILESET](state: any, fileset: LaxyFileSet) {
        // state.filesets[fileset.id] = fileset; // doesn't preserve reactivity
        Vue.set(state.filesets, fileset.id, fileset); // reactive
    },
    [SET_VIEWED_JOB](state: any, job: ComputeJob) {
        state.currentViewedJob = job;
    },
    [SET_JOB_ACCESS_TOKEN](state: any, params: any) {
        const { job_id, token } = params;
        Vue.set(state.jobAccessTokens, job_id, token);
    },
    [SET_PIPELINES](state: any, pipelines: any) {
        addPipelineRoutes(pipelines);
        Vue.set(state, 'availablePipelines', keyBy(pipelines, p => p.name));
    },
    ...make.mutations(initial_state),
};

const actions: any = {

    async [PING_BACKEND]({ commit, state }: any) {
        try {
            const response = await WebAPI.ping();
            commit(SET_ONLINE_STATUS, response.data.status === 'online');
            commit(SET_BACKEND_VERSION, response.data.version);
        } catch (error) {
            commit(SET_ONLINE_STATUS, false);
            commit(SET_BACKEND_VERSION, 'unknown');
            throw error;
        }
    },
    async [AUTHENTICATE_USER]({ commit, state, dispatch }: any, payload: any) {
        try {
            if (payload.provider === 'laxy') {
                const response = await WebAPI.login(payload.username, payload.password);
            }
            if (payload.provider === 'google') {
                const response = await vueAuth.authenticateSession(
                    payload.provider,
                    { provider: 'google-oauth2' },
                    {});
            }

            const providerOverrides: any = AuthOptions.providers[payload.provider];
            if (providerOverrides && providerOverrides.name) {
                const response = await vueAuth.authenticateSession(
                    providerOverrides.name,
                    {
                        provider: providerOverrides.provider,
                    },
                    providerOverrides);
            }
            await dispatch(FETCH_USER_PROFILE);
        } catch (error) {
            throw error;
        }
    },
    async [FETCH_USER_PROFILE]({ commit, state }: any) {
        try {
            const response = await WebAPI.getUserProfile();
            const profile_info = pick(response.data,
                ['id', 'full_name', 'username', 'email', 'profile_pic']);
            commit(SET_USER_PROFILE, profile_info);
        } catch (error) {
            throw error;
        }
    },
    async [SET_SAMPLES]({ commit, state }: any, samples: SampleCartItems) {
        const preCommit = cloneDeep(state.samples);
        if (preCommit.id != null && samples.id == null) {
            samples.id = preCommit.id;
        }
        // optimistically commit the state
        commit(SET_SAMPLES, samples);
        const data = {
            name: samples.name,
            samples: samples.items
        };
        try {
            if (samples.id == null) {
                const response = await WebAPI.fetcher.post('/api/v1/samplecart/', data) as AxiosResponse;
                // samples.id = response.data.id;
                // commit(SET_SAMPLES, samples);
                commit(SET_SAMPLES_ID, response.data.id);
            } else {
                const response = await WebAPI.fetcher.put(
                    `/api/v1/samplecart/${samples.id}/`, data) as AxiosResponse;
            }
        } catch (error) {
            // rollback to saved copy if server update fails
            commit(SET_SAMPLES, preCommit);
            throw error;
        }
    },
    async [CLEAR_SAMPLE_CART]({ commit, state }: any) {
        // commit NOT dispatch, since the dispatch action would update the serverside object too !
        commit(SET_SAMPLES, new SampleCartItems());
    },
    async [SET_PIPELINE_PARAMS]({ commit, state }: any, params: any) {
        commit(SET_PIPELINE_PARAMS, params);
    },
    async [FETCH_JOBS]({ commit, state }: any, pagination = { page: 1, page_size: 10 }) {
        try {
            const response = await WebAPI.getJobs(
                pagination.page,
                pagination.page_size);
            const jobs: JobsPage = {
                total: response.data.count,
                jobs: response.data.results as ComputeJob[]
            };
            // ISO date strings to Javascipt Date objects
            for (const key of ['created_time', 'modified_time', 'completed_time']) {
                update(jobs, key, function (d_str: string) {
                    return new Date(d_str);
                });
            }
            commit(SET_JOBS, jobs);
        } catch (error) {
            throw error;
        }
    },
    async [FETCH_FILESET]({ commit, state }: any, fileset_id: string) {
        try {
            const response = await WebAPI.getFileSet(fileset_id);
            commit(SET_FILESET, response.data);
        } catch (error) {
            throw error;
        }
    },
    async [FETCH_JOB]({ commit, state }: any, params: any) {
        const { job_id, access_token } = params;
        if (access_token) commit(SET_JOB_ACCESS_TOKEN, { job_id: job_id, token: access_token });
        try {
            const response = await WebAPI.getJob(job_id, access_token);
            commit(SET_VIEWED_JOB, response.data);
        } catch (error) {
            throw error;
        }
    },
    async [FETCH_PIPELINES]({ commit, state }: any) {
        try {
            const response = await WebAPI.getAvailablePipelines();
            if (response.data.next != null) {
                throw new Error("WebAPI.getAvailablePipelines returned more than one page of results, but pagination is not yet implemented.")
            }
            commit(SET_PIPELINES, response.data.results);
        } catch (error) {
            throw error;
        }
    },
};

export const Store = new Vuex.Store({
    plugins: [pathify.plugin],
    strict: true,
    state: initial_state,
    getters: getters,
    mutations: mutations,
    actions: actions,
});

(window as any).store = Store;