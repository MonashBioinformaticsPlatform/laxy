declare function require(path: string): any;
// require('file-loader?name=[name].[ext]!../src/index.html');
import 'vue-material/dist/vue-material.css';
// import 'css/slider.css';

import 'es6-promise';

import Vue, {ComponentOptions} from "vue";
import VueRouter from 'vue-router';
const VueMaterial = require('vue-material');
const VueMoment = require('vue-moment');  // for date formatting

Vue.use(VueRouter);
Vue.use(VueMaterial);
Vue.use(VueMoment);

// sadly not working :/
/*
const VueMarkdown = require('vue-markdown');
Vue.use(VueMarkdown);
Vue.component('vue-markdown', VueMarkdown);
*/

import FrontPage from './components/FrontPage.vue';
import RNASeqSetup from './components/RNASeqSetup.vue';
import InputDataForm from './components/InputFilesForm.vue';
Vue.component('input-files-form', InputDataForm);

const router = new VueRouter({
  routes: [
    // { path: '/', redirect: '/rnaseq' },
    {
      path: '/',
      name: 'front',
      component: FrontPage,
    },
    {
      path: '/rnaseq',
      name: 'rnaseq',
      component: RNASeqSetup,
    },
  ],
  // mode: 'history',
});

interface MainApp extends Vue {
    logged_in: boolean,
    user_fullname: string,
}

const MainApp = new Vue({
    el: '#app',
    router,
    data() {
        return {
            logged_in: false,
            user_fullname: "John Monash",
        }
    },
    methods: {
        login() {
            (this.$data as MainApp).logged_in = true;
            router.push('rnaseq');
        },
        logout(event) {
            (this.$data as MainApp).logged_in = false;
            //this.$refs["avatarMenu"].close();
            router.push('/');
        },
        openProfile(event) {
            //this.$refs["avatarMenu"].close();
            router.push('profile');
        },
        toggleLeftSidenav() {
            (this.$refs.leftSidenav as any).toggle();
        },
        open(ref: string) {
            console.log('Opened: ' + ref);
        },
        close(ref: string) {
            console.log('Closed: ' + ref);
        },
    }
}) as ComponentOptions<MainApp>;
