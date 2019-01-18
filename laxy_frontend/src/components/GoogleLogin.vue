<template>
    <!--<md-layout md-align="center" md-gutter="16">-->

        <div class="g-signin2" data-onsuccess="onSignIn" data-theme="dark"></div>

    <!--</md-layout>-->
</template>

<script lang="ts">
    import '../../assets/favicon-grey-24.png';
    import '../../assets/btn_google_signin_dark_normal_web.png';

    import Vue from 'vue';
    import Component from "vue-class-component";

    import {
        Prop,
    } from "vue-property-decorator";

    @Component({})
    export default class LoginPage extends Vue {
        @Prop({default: '/', type: String})
        public redirectPath: string;

        public get is_authenticated(): boolean {
            return this.$store.getters.is_authenticated;
        }
    }
</script>

<style lang="scss" scoped>

</style>
