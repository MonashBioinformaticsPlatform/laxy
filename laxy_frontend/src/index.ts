// import 'file-loader?emitFile=false!../../.env';  // watch .env but DON'T output the file ! (emitFile=false)
try {
    require('file-loader?emitFile=false!../../.env');  // watch .env but DON'T output the file ! (emitFile=false)
} catch {
    // pass
}

// import 'file-loader?name=[name].[ext]!../index.html';
import 'file-loader?name=[name].[ext]?[hash]&outputPath=assets/!../assets/favicon.ico';
import '../assets/Monash_Big_M_42x96.png';
import 'vue-material/dist/vue-material.css';

import 'es6-promise';

import get from "lodash-es/get";

const numeral = require('numeral');
import axios, { AxiosResponse, AxiosRequestConfig } from 'axios';

import Vue, { ComponentOptions } from 'vue';
import Vue2Filters from 'vue2-filters';  // https://github.com/freearhey/vue2-filters

const LAXY_ENV = process.env.LAXY_ENV === 'dev';
Vue.config.productionTip = LAXY_ENV;
Vue.config.devtools = LAXY_ENV;
Vue.config.performance = LAXY_ENV;
Vue.config.silent = !LAXY_ENV;

import Vuex from 'vuex';

Vue.use(Vuex);

import VueRouter, { RouterOptions, RouteConfig } from 'vue-router';

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

import { browserLocale } from './util';
import * as moment from 'moment';

moment.locale(browserLocale());
const VueMoment = require('vue-moment');  // for date formatting
Vue.use(VueMoment);

import { WebAPI } from './web-api';
import { router, requireAuth } from './routes';

// Import per component, not globally
// import VueMarkdown from 'vue-markdown';
// Vue.component('vue-markdown', VueMarkdown);

import {
    AUTHENTICATE_USER,
    FETCH_USER_PROFILE,
    FETCH_PIPELINES,
    PING_BACKEND,
    SET_GLOBAL_SNACKBAR,
    SET_USER_PROFILE,
    Store as store
} from './store';
import { truncateString, widthAwareStringTruncate } from './util';

import MainSidenav from './components/MainSidenav.vue';
import SampleCart from './components/SampleCart.vue';
import SampleTable from './components/SampleTable.vue';
import JobPage from './components/JobPage.vue';
import JobStatusCard from './components/JobStatusCard.vue';
import FileList from './components/FileList.vue';
import EventLog from './components/EventLog.vue';

Vue.component('main-sidenav', MainSidenav);
Vue.component('sample-table', SampleTable);
Vue.component('sample-cart', SampleCart);
Vue.component('file-list', FileList);
Vue.component('event-log', EventLog);
Vue.component('job-page', JobPage);
Vue.component('job-status-card', JobStatusCard);

import SpinnerCubeGrid from './components/spinners/SpinnerCubeGrid.vue';
import { Snackbar } from "./snackbar";

Vue.component('spinner-cube-grid', SpinnerCubeGrid);

// import SpinnerEq from './components/spinners/SpinnerEq.vue';
// Vue.component('spinner-eq', SpinnerEq);

Vue.filter('numeral_format', function (value: number | string, format: string = '0 a') {
    if (!value) return '';
    return numeral(value).format(format);
});

// Based on: https://stackoverflow.com/a/14919494
Vue.filter('humanize_bytes', function humanFileSize(bytes: number, si: boolean = true) {
    const thresh = si ? 1000 : 1024;
    if (Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    const units = si
        ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    let u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);

    return `${bytes.toFixed(1)} ${units[u]}`;
});

Vue.filter('deunderscore', function (value: string) {
    if (!value) return '';
    value = value.replace('_', ' ');
    // capitalize first letter
    return value.charAt(0).toUpperCase() + value.slice(1);
});

Vue.filter('truncate', truncateString);
Vue.filter('magic_truncate', widthAwareStringTruncate);

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
            showFooterMessage: true,
            appVersion: process.env.LAXY_VERSION,
            pingPollerId: -1,
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

        try {
            await this.$store.dispatch(FETCH_USER_PROFILE);
        } catch (e) {
            console.warn(e)
        }
        try {
            await this.$store.dispatch(FETCH_PIPELINES);
        } catch (e) {
            console.warn(e)
        }
    },
    mounted() {
        const snackbar = (this.$refs.global_snackbar as any);
        Snackbar.component = snackbar;
        snackbar.$on('close', () => {
            this.$store.commit(SET_GLOBAL_SNACKBAR, { message: '', duration: 2000 });
        });

        this.$store.dispatch(PING_BACKEND);
        this.pingPollerId = setInterval(() => {
            this.$store.dispatch(PING_BACKEND);
        }, 30000);  // ms
    },
    beforeDestroy() {
        if (this.pingPollerId !== -1) clearInterval(this.pingPollerId);
    },
    methods: {
        closeLoginDropdown() {
            const loginMenu = ((this.$refs as any).loginMenu as any);
            if (loginMenu) loginMenu.close();
        },
        async logout(event: Event) {
            await WebAPI.logout();
            this.$store.commit(SET_USER_PROFILE, null);
            this.routeTo('home');
            this.closeLoginDropdown();
        },
        routeTo(name: string, params: any = {}) {
            this.$router.push({ name: name, params: params });
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
        online(): boolean {
            return get(this.$store.state, "online", false);
        },
        backendVersion(): string {
            return this.$store.state.backend_version;
        },
        sample_cart_count(): number {
            return this.$store.getters.sample_cart_count;
        },
        user_profile(): any {
            return this.$store.state.user_profile;
        },
        logged_in(): boolean {
            return !!this.$store.getters.is_authenticated;
        },
        snackbar_message(): string {
            return this.$store.state.global_snackbar_message;
        },
        snackbar_duration(): number {
            return this.$store.state.global_snackbar_duration;
        },
        statusMessage(): string {
            return get(this.$store.state, "system_status.message", "");
        },
        systemStatus(): string {
            return get(this.$store.state, "system_status", null);
        }
    }
});
