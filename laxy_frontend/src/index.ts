import 'file-loader?emitFile=false!../../.env';  // watch .env but DON'T output the file ! (emitFile=false)
// import 'file-loader?name=[name].[ext]!../index.html';
import 'file-loader?name=[name].[ext]?[hash]&outputPath=assets/!../assets/favicon.ico';
import 'vue-material/dist/vue-material.css';

import 'es6-promise';

const numeral = require('numeral');
import axios, {AxiosResponse, AxiosRequestConfig} from 'axios';

import Vue, {ComponentOptions} from 'vue';
import Vue2Filters from 'vue2-filters';  // https://github.com/freearhey/vue2-filters

const LAXY_ENV = process.env.LAXY_ENV === 'dev';
Vue.config.productionTip = LAXY_ENV;
Vue.config.devtools = LAXY_ENV;
Vue.config.performance = LAXY_ENV;
Vue.config.silent = !LAXY_ENV;

import Vuex from 'vuex';

Vue.use(Vuex);

import VueRouter, {RouterOptions} from 'vue-router';

Vue.use(VueRouter);

// import VueAxios from 'vue-axios';
const VueAxios = require('vue-axios');
Vue.use(VueAxios, axios);

const VueMaterial = require('vue-material');
// import VueMaterial from 'vue-material';
Vue.use(VueMaterial);

(Vue as any).material.registerTheme('default', {
    primary: 'blue',
    accent: 'pink',
    warn: 'deep-orange',
    background: 'white',
});

Vue.use(Vue2Filters);

import {browserLocale} from './util';
import * as moment from 'moment';
moment.locale(browserLocale());
const VueMoment = require('vue-moment');  // for date formatting
Vue.use(VueMoment);

import {WebAPI} from './web-api';
import {router} from './routes';

// Import per component, not globally
// import VueMarkdown from 'vue-markdown';
// Vue.component('vue-markdown', VueMarkdown);

import {AUTHENTICATE_USER, FETCH_USER_PROFILE, SET_USER_PROFILE, Store as store} from './store';
import {truncateString} from './util';

import InputDataForm from './components/InputFilesForm.vue';
import SampleCart from './components/SampleCart.vue';
import SampleTable from './components/SampleTable.vue';
import PipelineParams from './components/PipelineParams.vue';
import JobPage from './components/JobPage.vue';
import JobStatusCard from './components/JobStatusCard.vue';
import FileList from './components/FileList.vue';
import EventLog from './components/EventLog.vue';

Vue.component('input-files-form', InputDataForm);
Vue.component('sample-table', SampleTable);
Vue.component('sample-cart', SampleCart);
Vue.component('pipeline-params', PipelineParams);
Vue.component('file-list', FileList);
Vue.component('event-log', EventLog);
Vue.component('job-page', JobPage);
Vue.component('job-status-card', JobStatusCard);

import SpinnerCubeGrid from './components/spinners/SpinnerCubeGrid.vue';

Vue.component('spinner-cube-grid', SpinnerCubeGrid);

// import SpinnerEq from './components/spinners/SpinnerEq.vue';
// Vue.component('spinner-eq', SpinnerEq);

Vue.filter('numeral_format', function (value: number | string, format: string = '0 a') {
    if (!value) return '';
    return numeral(value).format(format);
});

Vue.filter('deunderscore', function (value: string) {
    if (!value) return '';
    value = value.replace('_', ' ');
    // capitalize first letter
    return value.charAt(0).toUpperCase() + value.slice(1);
});

Vue.filter('truncate', truncateString);

// The vue-moment docs claim that package adds this filter, but it doesn't
// seem to be the case. So, we add our own duration filter.
Vue.filter('duration', moment.duration);

const App = new Vue({
    el: '#app',
    router,
    store,
    data() {
        return {
            showHeaderMessage: true,  // process.env.LAXY_ENV === 'dev',
        };
    },
    async created() {
        await WebAPI.requestCsrfToken();

        WebAPI.fetcher.interceptors.request.use((config: AxiosRequestConfig) => {
            config.headers[config.xsrfHeaderName || 'X-CSRFToken'] = WebAPI._getStoredCsrfToken();
            return config;
        }, (error) => {
            return Promise.reject(error);
        });

        await this.$store.dispatch(FETCH_USER_PROFILE);
    },
    methods: {
        closeLoginDropdown() {
            ((this.$refs as any).loginMenu as any).close();
        },
        async logout(event: Event) {
            await WebAPI.logout();
            this.$store.commit(SET_USER_PROFILE, null);
            this.routeTo('home');
            this.closeLoginDropdown();
        },
        routeTo(name: string, params: any = {}) {
            this.$router.push({name: name, params: params});
        },
        toggleSidenav(refName: string) {
            ((this.$refs as any)[refName] as any).toggle();
        },
        open(ref: string) {
            // console.log('Opened: ' + ref);
        },
        close(ref: string) {
            // console.log('Closed: ' + ref);
        },
    },
    computed: {
        sample_cart_count(): number {
            return this.$store.getters.sample_cart_count;
        },
        user_profile(): any {
            return this.$store.state.user_profile;
        },
        logged_in(): boolean {
            return !!this.$store.getters.is_authenticated;
        }
    }
});
