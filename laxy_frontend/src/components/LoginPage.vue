<template>
    <md-layout md-align="center" md-gutter="16">
        <md-layout md-flex="25" md-flex-small="100" md-column>
            <md-card v-if="!is_authenticated" style="margin-top: 32px;">

                <callout-box></callout-box>

                <md-card-content>
                    <md-layout md-column>
                        <transition name="slide-fade">
                            <md-layout v-if="showExternalButtons" md-column>
                                <div class="md-title pad-16">Login</div>
                                <md-button @click="login('google')"
                                           class="md-raised login-button"
                                           style="background-color: #4385F4;"
                                           type="submit"><img src="assets/btn_google_signin_dark_normal_web.png">
                                </md-button>
                                <md-button @click="login('google_monash')"
                                           class="md-raised md-primary login-button"
                                           style="background-color: #4385F4;"
                                           type="submit">Monash Login via Google
                                </md-button>
                            </md-layout>
                        </transition>
                        <hr>
                        <md-list>
                            <md-list-item @click="() => { showExternalButtons = !showExternalButtons }">
                                <md-icon md-src="assets/favicon-grey-24.png"></md-icon>
                                <span>Other options</span>
                                <md-list-expand>
                                    <form novalidate @submit.stop.prevent="">
                                        <md-list>
                                            <li>
                                                <br>
                                                <div class="md-subtitle">Login with a local Laxy account</div>
                                            </li>
                                            <li>
                                                <md-input-container>
                                                    <label>Username</label>
                                                    <md-input v-model="login_form_username"></md-input>
                                                </md-input-container>
                                            </li>
                                            <li>
                                                <md-input-container md-has-password>
                                                    <label>Password</label>
                                                    <md-input v-model="login_form_password"
                                                              type="password"></md-input>
                                                </md-input-container>
                                            </li>
                                            <li>
                                                <md-button @click="login('laxy')"
                                                           class="md-raised md-primary fill-width login-button"
                                                           type="submit">Login
                                                </md-button>
                                            </li>
                                        </md-list>
                                    </form>
                                </md-list-expand>
                            </md-list-item>
                        </md-list>
                    </md-layout>
                </md-card-content>
            </md-card>
            <md-card v-if="is_authenticated" style="margin-top: 32px;">

                <callout-box></callout-box>

                <md-card-content>
                    <md-layout md-column>
                        <br>
                        <span class="md-title">You are logged in as {{ full_name }} (<em>{{ username }}</em>).</span>
                        <br>
                        <md-button @click="logout" class="md-primary md-raised fill-width">Logout</md-button>
                    </md-layout>
                </md-card-content>
            </md-card>
        </md-layout>
    </md-layout>
</template>

<script lang="ts">
    import '../../assets/favicon-grey-24.png';
    import '../../assets/btn_google_signin_dark_normal_web.png';

    import get from 'lodash-es/get';

    import Vue from 'vue';
    import Component from "vue-class-component";

    import {AUTHENTICATE_USER, SET_GLOBAL_SNACKBAR, SET_USER_PROFILE} from "../store";
    import {WebAPI} from "../web-api";

    import CalloutBox from './CalloutBox';
    import {Snackbar} from "../snackbar";

    @Component({
        components: {
            'callout-box': CalloutBox
        }
    })
    export default class LoginPage extends Vue {
        public login_form_username: string = '';
        public login_form_password: string = '';

        public showExternalButtons: boolean = true;

        public get is_authenticated(): boolean {
            return this.$store.getters.is_authenticated;
        }

        public get full_name(): string {
            return get(this.$store.state.user_profile, 'full_name', 'Anonymous')
        }

        public get username(): string {
            return get(this.$store.state.user_profile, 'username', 'anonymous')
        }

        public async created() {

        }

        public async login(provider: string) {
            let providerData = {provider: provider};
            if (provider === 'laxy') {
                providerData = Object.assign(providerData, {
                    username: this.login_form_username,
                    password: this.login_form_password
                });
            }
            try {
                await this.$store.dispatch(AUTHENTICATE_USER, providerData);
                this.clearLoginForm();
                this.routeTo('home');
            } catch (error) {
                if (error.message === 'Auth popup window closed') {
                    Snackbar.flashMessage('Authentication cancelled');
                } else {
                    throw error;
                }
            }
        }

        public async logout(event: Event) {
            await WebAPI.logout();
            this.$store.commit(SET_USER_PROFILE, null);
            this.routeTo('home');
        }

        public clearLoginForm() {
            this.login_form_username = '';
            this.login_form_password = '';
        }

        public routeTo(name: string, params: any = {}) {
            (this as any).$router.push({name: name, params: params});
        }
    }
</script>

<style lang="scss" scoped>
    $login-button-height: 64px;
    $slide-fade-transition-duration: 200ms;
    $slide-fade-transition-move-by: 512px;

    .login-button {
        height: $login-button-height;
        padding: 8px;
        margin-top: 16px;
        margin-bottom: 16px;
    }

    .slide-fade-enter-active {
        transition: all $slide-fade-transition-duration ease;
    }

    .slide-fade-leave-active {
        transition: all $slide-fade-transition-duration cubic-bezier(1.0, 0.5, 0.8, 1.0);
    }

    .slide-fade-enter, .slide-fade-leave-to {
        transform: translateX($slide-fade-transition-move-by);
        opacity: 0;
    }
</style>
