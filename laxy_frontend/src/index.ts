declare function require(path: string): any;

// require('file-loader?name=[name].[ext]!../src/index.html');
import 'vue-material/dist/vue-material.css';
// import 'css/slider.css';

import 'es6-promise';

const numeral = require('numeral');

import axios, {AxiosResponse} from 'axios';

import Vue, {ComponentOptions} from 'vue';
import Vuex from 'vuex';
import VueRouter, {RouterOptions} from 'vue-router';

const VueMaterial = require('vue-material');
const VueMoment = require('vue-moment');  // for date formatting

Vue.use(Vuex);
Vue.use(VueRouter);
Vue.use(VueMaterial);
Vue.use(VueMoment);

// sadly not working :/
/*
const VueMarkdown = require('vue-markdown');
Vue.use(VueMarkdown);
Vue.component('vue-markdown', VueMarkdown);
*/

import {FETCH_USER_PROFILE, SET_USER_PROFILE, Store as store} from './store';
import {WebAPI} from './web-api';

import FrontPage from './components/FrontPage.vue';
import FileBrowser from './components/FileBrowser.vue';
import RNASeqSetup from './components/RNASeqSetup.vue';
import InputDataForm from './components/InputFilesForm.vue';
import ENAFileSelect from './components/ENAFileSelect.vue';
import SampleCart from './components/SampleCart.vue';
import SampleTable from './components/SampleTable.vue';
import PipelineParams from './components/PipelineParams.vue';
import ENAFlow from './components/ENAFlow.vue';
import JobList from './components/JobList.vue';
import JobPage from './components/JobPage.vue';
import FileList from './components/FileList.vue';
import EventLog from './components/EventLog.vue';

Vue.component('input-files-form', InputDataForm);
Vue.component('sample-table', SampleTable);
Vue.component('ena-search', ENAFileSelect);
Vue.component('sample-cart', SampleCart);
Vue.component('pipeline-params', PipelineParams);
Vue.component('file-list', FileList);
Vue.component('event-log', EventLog);
Vue.component('job-page', JobPage);

import SpinnerCubeGrid from './components/spinners/SpinnerCubeGrid.vue';
Vue.component('spinner-cube-grid', SpinnerCubeGrid);

// import SpinnerEq from './components/spinners/SpinnerEq.vue';
// Vue.component('spinner-eq', SpinnerEq);

Vue.filter('numeral_format', function(value: number | string, format: string = '0 a') {
    if (!value) return '';
    return numeral(value).format(format);
});

Vue.filter('deunderscore', function(value: string) {
    if (!value) return '';
    value = value.replace('_', ' ');
    // capitalize first letter
    return value.charAt(0).toUpperCase() + value.slice(1);
});

const router = new VueRouter({
    routes: [
        // { path: '/', redirect: '/rnaseq' },
        {
            path: '/',
            name: 'home',
            component: FrontPage,
        },
        {
            path: '/ENAflow',
            name: 'ENAflow',
            component: ENAFlow,
        },
        {
            path: '/files',
            name: 'files',
            component: FileBrowser,
        },
        {
            path: '/rnaseq',
            name: 'rnaseq',
            component: RNASeqSetup,
        },
        {
            path: '/enaselect',
            name: 'enaselect',
            component: ENAFileSelect,
        },
        {
            path: '/cart',
            name: 'cart',
            component: SampleCart,
        },
        {
            path: '/setupRun',
            name: 'setupRun',
            component: PipelineParams,
        },
        {
            path: '/jobs',
            name: 'jobs',
            component: JobList,
        },
        {
            path: '/job/:jobId',
            name: 'job',
            component: JobPage,
            props: true,
        },
    ],
    // mode: 'history',
    scrollBehavior(to, from, savedPosition) {
        // This does smooth scrolling to the top of the page
        // when we navigate to a new route.
        //
        // The "behaviour: 'smooth'" option is a draft spec and might be
        // unsupported in some old/crappy browsers.
        // https://developer.mozilla.org/en-US/docs/Web/API/Window/scrollTo
        const topOfPage = {x: 0, y: 0};
        const duration = 300; // ms
        return new Promise((resolve, reject) => {
            window.scrollTo({
                top: topOfPage.y,
                left: topOfPage.x,
                behavior: 'smooth'
            });
            setTimeout(() => {
                resolve(topOfPage);
            }, duration);
        });
        // return {x: 0, y: 0};
    }
} as RouterOptions);

interface MainApp extends Vue {
    logged_in: boolean;
    user_fullname: string;
    login_form_username: string;
    login_form_password: string;
    sample_cart_count: number;
}

const App = new Vue({
    el: '#app',
    router,
    store,
    data() {
        return {
            logged_in: false,
            user_fullname: '',
            login_form_username: '',
            login_form_password: '',
        };
    },
    async created() {
        await this.$store.dispatch(FETCH_USER_PROFILE);
        if (this.$store.state.user_profile) {
            this.logged_in = true;
        } else {
            this.logged_in = false;
        }
        // WebAPI.isLoggedIn().then((result) => {
        //     this.logged_in = result;
        // });
    },
    methods: {
        async login() {
            const data = (this.$data as MainApp);
            try {
                const response = await WebAPI.login(data.login_form_username, data.login_form_password);
                await this.$store.dispatch(FETCH_USER_PROFILE);
                ((this.$refs as any).loginMenu as any).close();
                (this as any).become_logged_in();
            } catch (error) {
                throw error;
            }
        },
        become_logged_in() {
            const data = (this.$data as MainApp);
            data.login_form_username = '';
            data.login_form_password = '';
            data.logged_in = true;
            // router.push('rnaseq');
        },
        async logout(event: Event) {
            sessionStorage.setItem('accessToken', '');
            await WebAPI.logout();
            (this.$data as MainApp).logged_in = false;
            this.$store.commit(SET_USER_PROFILE, {});
            // this.$refs["avatarMenu"].close();
            router.push('/');
        },
        routeTo(name: string) {
            this.$router.push({name: name});
        },
        toggleLeftSidenav() {
            ((this.$refs as any).leftSidenav as any).toggle();
        },
        open(ref: string) {
            console.log('Opened: ' + ref);
        },
        close(ref: string) {
            console.log('Closed: ' + ref);
        },
    },
    computed: {
        sample_cart_count(): number {
            return this.$store.getters.sample_cart_count;
        },
        user_profile(): any {
            return this.$store.state.user_profile;
        },
     }
}) as ComponentOptions<MainApp>;
