// const VueAuthenticate = require('vue-authenticate');  // without TypeScript types
import {VueAuthenticate, AuthenticateOptions, ProviderOptions} from 'vue-authenticate';

import {WebAPI} from './web-api';

export const AuthOptions: AuthenticateOptions = {
    // we MUST include withCredentials: true, otherwise the cookies returned by the VueAuthenticate.authenticateSession
    // POST request won't be stored by the browser. The VueAuthenticate.authenticateSession method enforces this,
    // but the token-auth equivalent VueAuthenticate.authenticate requires this to be explicit.
    withCredentials: true,

    baseUrl: WebAPI.baseUrl,
    authCheckUrl: `/accounts/profile/`,

    // Token auth settings (not in use)
    // storageType: 'localStorage',
    // tokenPrefix: null,
    // tokenName: WebAPI.authTokenName,
    // tokenType: 'Bearer', // for JWT
    // tokenType: 'Token', // for DRF

    providers: {
        // We are essentially using the flow as depicted here (without using any of Google's provided Javascript):
        // https://developers.google.com/identity/sign-in/web/server-side-flow
        google: {
            clientId: '474709025289-vm2t2ikg08ij9mvl3h813l86nng1e4eh.apps.googleusercontent.com',

            // redirectUri must match a redirect_uri defined at
            // https://console.developers.google.com/apis/credentials
            // We use the URL to the frontend as the redirect if we are capturing the authorization code returned via
            // in the frontend popup (rather than having Google hit laxy_backend directly)
            redirectUri: WebAPI.apiSettings.frontendUrl ||
                `http://${window.location.hostname}:${window.location.port}/`,

            // We can also have Google redirect to laxy_backend directly (using a view from
            // django-rest-framework-social-oauth2 to authenticate). In this case the redirectUri should
            // set the session cookie, and then redirect itself to the laxy_frontend URL. This isn't ideal,
            // since the browser tab won't be the same one the user clicked 'Login' in (we will now have two
            // laxy_frontend tabs).
            // redirectUri: `${WebAPI.baseUrl}/auth/complete/google-oauth2/`,

            // This is used for receiving as token via Django username/password login. We probably won't use it.
            // loginUrl: `${WebAPI.baseUrl}/login/`,

            // This is the url that the frontend POSTs the authorization code (`code`) provided by Google to.
            // This endpoint is responsible for validating the authorization code (the backend makes a request to Google
            // to exchange this code for an access code), and returning 200 if everything went okay. It MAY return a
            // token (DRF or JWT) for localStorage or sessionStorage, if we are using token auth (eg,
            // the rest_social_auth `login/social/token_user/google-oauth2/` and `login/social/jwt_user/google-oauth2/`
            // endpoints).
            // It should also set a session cookie if we are using this for authentication (eg the .rest_social_auth
            // `login/social/session/google-oauth2/` endpoint)
            url: `/api/login/social/session/google-oauth2/`,  // Django session login (sets session cookie)

            // for DRF tokens rather than session cookie
            // tokenType: 'Token',  // we use Authorization: Token hexb14f00 for DRF tokens
            // url: `/api/login/social/token_user/google-oauth2/`,

            // for JWT tokens rather than session cookie
            // tokenType: 'Bearer',  // we use Authorization: Bearer my.jwt.blob for DRF tokens
            // url: `/api/login/social/jwt_user/google-oauth2/`,
        } as ProviderOptions,
    }
};

// export const vueAuth = VueAuthenticate.default.factory(Vue.prototype.$http, AuthOptions);
export const vueAuth = new VueAuthenticate(WebAPI.fetcher, AuthOptions);
