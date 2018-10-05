import VueRouter, {RouterOptions} from 'vue-router';
import {FETCH_USER_PROFILE, Store} from './store';

import FrontPage from './components/FrontPage.vue';
import LoginPage from './components/LoginPage.vue';
import RNASeqSetup from './components/RNASeqSetup.vue';
import RemoteFilesSelect from './components/RemoteSelect/RemoteFilesSelect.vue';
import SampleCart from './components/SampleCart.vue';
import ENAFlow from './components/ENA/ENAFlow.vue';
import JobList from './components/JobList.vue';
import JobPage from './components/JobPage.vue';

async function requireAuth(to: any, from: any, next: Function) {
    // If profile isn't set, user MAY be authenticated (by existing an cookie/token) but
    // during a fresh page load where the Vuex stote is empty the initial request
    // to grab the user profile may not be complete yet. We wait for the user profile request, when check
    // if we are actually authenticated and continue to requested route, or redirect to /login.
    if (Store.state.user_profile === null) {
        try {
            await Store.dispatch(FETCH_USER_PROFILE);
        } catch (error) {
            next('/login');
        }
    }
    if (!Store.getters.is_authenticated) {
        next('/login');
    } else {
        next();
    }
}

export const router = new VueRouter({
    routes: [
        // { path: '/', redirect: '/rnaseq' },
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
