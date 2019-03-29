import VueRouter, {RouterOptions} from 'vue-router';
// const multiguard = require('vue-router-multiguard');

import {FETCH_USER_PROFILE, Store} from './store';

import FrontPage from './components/FrontPage.vue';
import LoginPage from './components/LoginPage.vue';
import RNASeqSetup from './components/RNASeqSetup.vue';
import RemoteFilesSelect from './components/RemoteSelect/RemoteFilesSelect.vue';
import SampleCart from './components/SampleCart.vue';
import ENAFlow from './components/ENA/ENAFlow.vue';
import JobList from './components/JobList.vue';
import JobPage from './components/JobPage.vue';
import PrivacyPolicy from './docs/PrivacyPolicy.vue';

async function requireAuth(to: any, from: any, next: Function) {
    // If profile isn't set, user MAY be authenticated (by existing an cookie/token) but
    // during a fresh page load where the Vuex store is empty the initial request
    // to grab the user profile may not be complete yet. We wait for the user profile request, when check
    // if we are actually authenticated and continue to requested route, or redirect to /login.
    //
    // If the incoming URL has an access_token in the query params, DON'T redirect to the login page,
    // but still try grabbing the user profile in case they are logged in.

    if (to.query.access_token != null) {
        next();
        return;
    }
    if (Store.state.user_profile === null) {
        try {
            await Store.dispatch(FETCH_USER_PROFILE);
        } catch (error) {
            next('/login');
            return;
        }
    }
    if (!Store.getters.is_authenticated) {
        next('/login');
        return;
    } else {
        next();
        return;
    }
}

/*
async function preserveQueryParams(to: any, from: any, next: Function) {
    // This preserves the query string when navigating between routes.
    // Eg, when navigating within 'tabs' on the same job, ?access_token will be maintained.
    if (from.query && JSON.stringify(from.query) !== JSON.stringify(to.query)) {
        next({name: to.name, query: from.query, params: to.params});
        // next();
    }
    next();
}
*/

export const router = new VueRouter({
    routes: [
        {
            path: '/',
            name: 'home',
            component: FrontPage,
            props: true,
        },
        {
            path: '/login',
            name: 'login',
            component: LoginPage,
            props: true,
        },
        {
            path: '/logout',
            name: 'logout',
            component: LoginPage,
            props: true,
        },
        {
            path: '/ENAflow',
            name: 'ENAflow',
            component: ENAFlow,
            props: true,
            beforeEnter: requireAuth,
        },
        {
            path: '/rnaseq',
            name: 'rnaseq',
            component: RNASeqSetup,
            props: true,
            beforeEnter: requireAuth,
        },
        // {
        //     path: '/enaselect',
        //     name: 'enaselect',
        //     component: ENAFileSelect,
        //     props: true,
        // },
        {
            path: '/remoteselect',
            name: 'remoteselect',
            component: RemoteFilesSelect,
            props: {showButtons: true},
            beforeEnter: requireAuth,
        },
        {
            path: '/cart',
            name: 'cart',
            component: SampleCart,
            props: true,
            beforeEnter: requireAuth,
        },
        // {
        //     path: '/setupRun',
        //     name: 'setupRun',
        //     component: PipelineParams,
        //     props: true,
        // },
        {
            path: '/jobs',
            name: 'jobs',
            component: JobList,
            props: true,
            beforeEnter: requireAuth,
        },
        {
            path: '/job/:jobId',
            name: 'job',
            component: JobPage,
            props: true,
            beforeEnter: requireAuth,
        },
        {
            path: '/job/:jobId/:showTab',
            name: 'jobTab',
            component: JobPage,
            props: true,
            beforeEnter: requireAuth,
        },
        {
            path: '/docs/privacy',
            name: 'privacy',
            component: PrivacyPolicy,
        },
    ],
    // 'history' mode requires extra server (eg nginx) config, breaks direct /job/{id} links
    // see: https://router.vuejs.org/guide/essentials/history-mode.html#html5-history-mode
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

export const degustLoaderPage =
    `<html><head>
    <link rel="shortcut icon" type="image/png" href="assets/favicon.ico"/>
    <link rel="stylesheet" href="//fonts.googleapis.com/css?family=Roboto:300,400,500,700,400italic">
    </head><body>
    <div style="position: absolute; margin: auto; width: 95%; top: 50%; text-align: center; font-family: 'Roboto', sans-serif; font-size: 32px">
    Loading counts in Degust ...
    <br/><br />
    <!-- <img src="https://cdnjs.cloudflare.com/ajax/libs/semantic-ui/0.16.1/images/loader-large.gif"> -->
    <img src="data:image/gif;base64,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" />
    </div>
    </body></html>`;
