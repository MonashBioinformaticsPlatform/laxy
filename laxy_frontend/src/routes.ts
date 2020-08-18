import VueRouter, { RouterOptions } from 'vue-router';
// const multiguard = require('vue-router-multiguard');

import { FETCH_USER_PROFILE, Store } from './store';

import FrontPage from './components/FrontPage.vue';
import LoginPage from './components/LoginPage.vue';
import RNASeqSetup from './components/RNASeqSetup.vue';
import RemoteFilesSelect from './components/RemoteSelect/RemoteFilesSelect.vue';
import SampleCart from './components/SampleCart.vue';
import ENAFlow from './components/ENA/ENAFlow.vue';
import JobList from './components/JobList.vue';
import JobPage from './components/JobPage.vue';
import PrivacyPolicy from './docs/PrivacyPolicy.vue';
import LoadingExternalPage from "./components/LoadingExternalPage.vue";

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
    if (Store.get('user_profile') === null) {
        try {
            await Store.dispatch(FETCH_USER_PROFILE);
        } catch (error) {
            next('/login');
            return;
        }
    }
    if (!Store.get('is_authenticated')) {
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
            path: '/redirect-external/:appName/:objectId',
            name: 'redirect-external',
            component: LoadingExternalPage,
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
        {
            path: '/remoteselect',
            name: 'remoteselect',
            component: RemoteFilesSelect,
            props: { showButtons: true },
            beforeEnter: requireAuth,
        },
        {
            path: '/cart',
            name: 'cart',
            component: SampleCart,
            props: true,
            beforeEnter: requireAuth,
        },
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
        const topOfPage = { x: 0, y: 0 };
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
