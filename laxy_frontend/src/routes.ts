import get from "lodash-es/get";

import VueRouter, { RouterOptions, RouteConfig } from 'vue-router';
// const multiguard = require('vue-router-multiguard');

import { FETCH_USER_PROFILE, Store } from './store';

import FrontPage from './components/FrontPage.vue';
import AboutPage from './components/AboutPage.vue';
import LoginPage from './components/LoginPage.vue';
import UserProfile from './components/UserProfile.vue';
import RNASeqSetup from './components/pipelines/rnasik/ui/RNASeqSetup.vue';
import SeqkitStatsSetup from './components/pipelines/seqkit_stats/ui/SeqkitStatsSetup.vue';
import NfCoreRnaSeqSetup from './components/pipelines/nf-core-rnaseq/ui/NfCoreRnaSeqSetup.vue';
import RemoteFilesSelect from './components/RemoteSelect/RemoteFilesSelect.vue';
import SampleCart from './components/SampleCart.vue';
import ENAFlow from './components/ENA/ENAFlow.vue';
import JobList from './components/JobList.vue';
import JobPage from './components/JobPage.vue';
import PrivacyPolicy from './docs/PrivacyPolicy.vue';
import LoadingExternalPage from "./components/LoadingExternalPage.vue";

export async function requireAuth(to: any, from: any, next: Function) {
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
            path: '/about',
            name: 'about',
            component: AboutPage,
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
            path: '/profile',
            name: 'profile',
            component: UserProfile,
            props: true,
        },
        {
            path: '/ENAflow',
            name: 'ENAflow',
            component: ENAFlow,
            props: true,
            beforeEnter: requireAuth,
        },
        // Now populated via routes.addPipelineRoutes() and WebAPI.getAvailablePipelines()
        // {
        //     path: '/run/rnasik',
        //     name: 'rnasik',
        //     component: RNASeqSetup,
        //     props: true,
        //     beforeEnter: requireAuth,
        // },
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


const _addedRoutes: string[] = [];
/*
* A wrapper around VueRouter.addRoutes that tracks already added routes by path,
* silently ignores those already added.
*/
export function addRoute(route: RouteConfig) {
    if (!_addedRoutes.includes(route.path)) {
        router.addRoutes([route]);
        _addedRoutes.push(route.path);
    }
}

export function addPipelineRoutes(pipelines: { name: string }[]) {
    const pipelineComponentMapping = {
        'rnaseq': RNASeqSetup,
        'rnasik': RNASeqSetup,
        'seqkit_stats': SeqkitStatsSetup,
        'nf-core-rnaseq': NfCoreRnaSeqSetup,
    };
    const routes = [];
    for (let p of pipelines) {
        // if (state.availablePipelines.includes(p.name)) continue;

        const r = {
            path: `/run/${encodeURIComponent(p.name.replace('_', '-'))}`,
            name: p.name,
            component: get(pipelineComponentMapping, p.name, FrontPage),
            props: true,
            beforeEnter: requireAuth,
        } as RouteConfig;
        // routes.push(r);
        addRoute(r);
    }

    // router.addRoutes(routes);
}