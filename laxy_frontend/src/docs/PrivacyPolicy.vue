<template>
    <md-layout md-flex-offset="25" md-column>
        <vue-markdown>

Privacy Policy
--------------

Laxy is an experimental service and comes with no expectation or guarantee of user privacy.
This includes, but is not limited to, data relating to user activity, uploaded data and derived data.
All data may be shared with third parties or publicly disclosed.
The developers, their employers and affiliates take no responsibility for the preservation of data
stored by or made accessible to the service. By using the service you agree to the terms of this policy.
This policy may be modified in the future without notice.

        </vue-markdown>
    </md-layout>
</template>

<script lang="ts">
    import Vue from "vue";
    import Component from "vue-class-component";
    import VueMarkdown from 'vue-markdown';

    @Component({
        components: {'vue-markdown': VueMarkdown},
        filters: {}
    })
    export default class PrivacyPolicy extends Vue {
    }
</script>
