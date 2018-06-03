<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-dialog md-open-from="#add_menu_button"
                   md-close-to="#add_menu_button" ref="cancel_job_dialog">
            <md-dialog-title>Cancel job</md-dialog-title>

            <md-dialog-content>Are you sure ?
            </md-dialog-content>

            <md-dialog-actions>
                <md-button class="md-primary"
                           @click="cancelJobConfirmed(jobToCancel)">Yes, cancel it.
                </md-button>
                <md-button class="md-primary"
                           @click="closeDialog('cancel_job_dialog')">Close
                </md-button>
            </md-dialog-actions>
        </md-dialog>

        <md-layout md-gutter>
            <md-layout md-flex="10" md-hide-medium>
                <md-list>
                    <nav class="vertical-sidebar-nav">
                        <md-list-item>
                            <router-link :to="`/job/${jobId}`" exact>Summary</router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/input`">Input</router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/output`">Output</router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/eventlog`">Event Log</router-link>
                        </md-list-item>
                    </nav>
                </md-list>

            </md-layout>
            <md-layout md-hide-large-and-up md-flex-medium="100">
                <md-toolbar class="md-transparent" style="width: 100%">
                    <nav style="width: 100%">
                        <router-link tag="md-button" active-class="md-primary" :to="`/job/${jobId}`" exact>
                            Summary
                        </router-link>
                        <router-link tag="md-button" active-class="md-primary" :to="`/job/${jobId}/input`">
                            Input
                        </router-link>
                        <router-link tag="md-button" active-class="md-primary" :to="`/job/${jobId}/output`">
                            Output
                        </router-link>
                        <router-link tag="md-button" active-class="md-primary" :to="`/job/${jobId}/eventlog`">
                            Event Log
                        </router-link>
                    </nav>
                </md-toolbar>
            </md-layout>
            <md-layout v-if="job">
                <md-layout id="top-panel" md-flex="90" md-flex-small="100">
                    <!-- smaller iconish boxes in here. eg simple status -->
                </md-layout>
                <md-layout id="main-panel" md-flex="90">
                    <transition name="fade">
                        <md-layout v-show="showTab === 'summary' || showTab == null" :md-column-medium="true" :md-row-large="true">
                            <md-layout id="left-panel" md-flex="40">
                                <job-status-card :job="job" v-on:cancel-job-clicked="onAskCancelJob"></job-status-card>
                            </md-layout>
                            <md-layout id="right-panel" md-flex="40">
                                <file-list v-if="job != null && job.status !== 'running'"
                                           title="Key result files"
                                           :fileset-id="job.output_fileset_id"
                                           :regex-filters="['\\.html$', '\\.count$', '\\.bam$', '\\.bai$', '\\.log$', '\\.out$']"
                                           :hide-search="false"
                                           @refresh-error="showErrorDialog">
                                </file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'input'" md-column-medium>
                            <md-layout id="left-panel">
                                <file-list id="input-files-card"
                                           v-if="job != null && job.status !== 'running'"
                                           title="Input files"
                                           :fileset-id="job.input_fileset_id"
                                           @refresh-error="showErrorDialog"></file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'output'" md-column-medium>
                            <md-layout id="left-panel">
                                <file-list id="output-files-card"
                                           v-if="job != null && job.status !== 'running'"
                                           title="Output files"
                                           :fileset-id="job.output_fileset_id"
                                           @refresh-error="showErrorDialog"></file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'eventlog'" md-column-medium>
                            <md-layout id="left-panel">
                                <event-log :job-id="jobId"
                                           @refresh-error="showErrorDialog"></event-log>
                            </md-layout>
                        </md-layout>
                    </transition>
                </md-layout>
            </md-layout>
        </md-layout>
        <md-snackbar md-position="bottom center" ref="snackbar"
                     :md-duration="snackbar_duration">
            <span>{{ snackbar_message }}</span>
            <md-button class="md-accent" @click="$refs.snackbar.close()">
                Dismiss
            </md-button>
        </md-snackbar>
    </div>
</template>


<script lang="ts">
    import "vue-material/dist/vue-material.css";

    import * as _ from "lodash";
    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
    import VueMaterial from "vue-material";
    import {palette} from "../palette";

    import Component from "vue-class-component";
    import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";

    import {
        State,
        Getter,
        Action,
        Mutation,
        namespace
    } from "vuex-class";

    import {ComputeJob} from "../model";
    import {WebAPI} from "../web-api";

    import {DummyJobList as _dummyJobList} from "../test-data";

    @Component({
        props: {
            jobId: {type: String, default: ""},
            showTab: {type: String, default: "summary"}
        },
        filters: {},
    })
    export default class JobPage extends Vue {
        _DEBUG: boolean = false;

        public job: ComputeJob | null = null;
        public jobId: string;

        public showTab: "summary" | "input" | "output" | "eventlog";

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            // this.jobId = _dummyJobList[0].id || '';
            // this.job = _dummyJobList[0];
            // this.jobId = '5ozQUwFCJDoV0vWgmo4q6E';
            this.refresh(null);
        }

        async refresh(successMessage: string | null = "Updated") {
            try {
                this.submitting = true;
                const response = await WebAPI.getJob(this.jobId);
                this.job = response.data as ComputeJob;
                this.submitting = false;
                if (successMessage) this.flashSnackBarMessage(successMessage, 500);
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                throw error;
            }
        }

        askCancelJob(id: string) {
            this.openDialog("cancel_job_dialog");
        }

        onAskCancelJob(event: Event) {
            this.openDialog("cancel_job_dialog");
        }

        async cancelJobConfirmed(id: string) {
            try {
                this.submitting = true;
                await WebAPI.cancelJob(this.jobId);
                this.submitting = false;
                this.flashSnackBarMessage("Job cancelled.");
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.closeDialog("cancel_job_dialog");
                this.openDialog("error_dialog");
                throw error;
            }

            this.closeDialog("cancel_job_dialog");
            this.refresh(null);
        }

        showErrorDialog(message: string) {
            this.error_alert_message = message;
            this.openDialog("error_dialog");
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }

        flashSnackBarMessage(msg: string, duration: number = 2000) {
            this.snackbar_message = msg;
            this.snackbar_duration = duration;
            (this.$refs.snackbar as any).open();
        }
    };

</script>

<style scoped>
    .spin {
        animation: rotate 1s infinite linear;
    }

    @keyframes rotate {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(359deg);
        }
    }

    .vertical-sidebar-nav a.router-link-active::after {
        content: " »";
    }
</style>
