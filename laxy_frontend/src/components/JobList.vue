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

        <md-layout md-column>
            <md-layout md-gutter>
                <md-layout>
                    <md-layout v-if="jobs != null">
                        <md-table-card style="width: 100%;">
                            <md-toolbar>
                                <h1 class="md-title">Jobs</h1>
                                <md-button class="md-icon-button" @click="refresh()">
                                    <md-icon :class="{spin: submitting}">refresh</md-icon>
                                </md-button>
                            </md-toolbar>
                            <md-table :class="{ colored: submitting }">
                                <md-table-header>
                                    <md-table-row>
                                        <md-table-head>Job</md-table-head>
                                        <md-table-head>Pipeline</md-table-head>
                                        <md-table-head>Created</md-table-head>
                                        <md-table-head>Status</md-table-head>
                                        <md-table-head style="text-align: center">Action</md-table-head>
                                    </md-table-row>
                                </md-table-header>
                                <md-table-body>
                                    <md-table-row v-for="job in jobs" :key="job.id">
                                        <md-table-cell v-if="job.params.description"
                                                       @click.native="routeTo('job', {jobId: job.id})">
                                            <md-tooltip md-direction="top">Job ID: {{ job.id }}</md-tooltip>
                                            {{ job.params.description }}
                                        </md-table-cell>
                                        <md-table-cell v-else="job.id">{{ job.id }}</md-table-cell>

                                        <md-table-cell @click.native="routeTo('job', {jobId: job.id})">
                                            {{ job.params.pipeline }}
                                            <template v-if="job && job.params && job.params.params">({{ job.params.params.genome }})</template>
                                        </md-table-cell>
                                        <md-table-cell @click.native="routeTo('job', {jobId: job.id})">
                                            <md-tooltip md-direction="top">{{ job.created_time }}</md-tooltip>
                                            {{ job.created_time| moment('from') }}
                                        </md-table-cell>
                                        <md-table-cell @click.native="routeTo('job', {jobId: job.id})">
                                            <span :style="{ color: getStatusColor(job.status) }">
                                                {{ job.status }}
                                            </span>
                                            <br>
                                        </md-table-cell>
                                        <md-table-cell md-numeric>
                                            <md-toolbar class="md-dense md-transparent">
                                                <md-button v-if="job.owner == userId"
                                                           class="md-icon-button"
                                                           @click="cloneJob(job.id)">
                                                    <md-tooltip md-direction="top">Run again</md-tooltip>
                                                    <md-icon>content_copy</md-icon>
                                                </md-button>
                                                <md-button class="md-icon-button"
                                                           @click="routeTo('job', {jobId: job.id})">
                                                    <md-tooltip md-direction="top">View job</md-tooltip>
                                                    <md-icon>remove_red_eye</md-icon>
                                                </md-button>
                                                <md-button v-if="job.owner == userId && job.status === 'running'"
                                                           class="md-icon-button"
                                                           @click="askCancelJob(job.id)">
                                                    <md-tooltip md-direction="top">Cancel</md-tooltip>
                                                    <md-icon>cancel</md-icon>
                                                </md-button>
                                            </md-toolbar>
                                        </md-table-cell>
                                    </md-table-row>
                                </md-table-body>
                            </md-table>
                            <md-table-pagination
                                    ref="pagination"
                                    :md-size="pagination.page_size"
                                    :md-total="pagination.count"
                                    :md-page="1"
                                    md-label="Jobs"
                                    md-separator="of"
                                    :md-page-options="false"
                                    @pagination="onPagination">
                            </md-table-pagination>
                        </md-table-card>
                    </md-layout>
                    <md-layout v-else>
                        .. no jobs ..
                    </md-layout>
                </md-layout>
            </md-layout>
        </md-layout>
    </div>
</template>


<script lang="ts">
    import * as _ from "lodash";
    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
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

    import {ComputeJob, SampleCartItems} from "../model";
    import {FETCH_JOBS, SET_PIPELINE_DESCRIPTION, SET_PIPELINE_PARAMS, SET_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    //import {AuthMixin} from "../index";

    import {DummyJobList as _dummyJobList} from "../test-data";
    import {Snackbar} from "../snackbar";
    import PipelineParams from "./PipelineParams.vue";

    @Component({})
    export default class JobList extends Vue {// Mixins<AuthMixin>(AuthMixin) {
        _DEBUG: boolean = false;

        // public jobs: any[] = [];
        public jobToCancel: string = "";
        public pagination: { [k: string]: number } = {page_size: 10, page: 1, count: 0};

        private _refreshPollerId: number | null = null;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        get jobs(): ComputeJob[] {
            return this.$store.state.jobs.jobs;
        }

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            //(new AuthMixin()).authenticate('google');
            //this.authenticate('google');

            // this.jobs = _dummyJobList;
            this.refresh();
        }

        mounted() {
            this._refreshPollerId = setInterval(() => {
                this.refresh(null);
            }, 10000);  // ms
        }

        beforeDestroy() {
            if (this._refreshPollerId != null) clearInterval(this._refreshPollerId);
        }

        routeTo(name: string, params: any = {}) {
            this.$router.push({name: name, params: params});
        }

        get userId(): string | null {
            return this.$store.getters.userId;
        }

        getStatusColor(status: string) {
            const status_colors: any = {
                complete: "grey",
                running: "green",
                failed: "red",
                cancelled: "black",
            };

            let color: any = status_colors[status];
            if (color == null) {
                color = "black";
            }
            return color;
        }

        async onPagination(event: any) {
            const leaving_page = this.pagination.page;
            this.pagination.page = event.page;
            this.pagination.page_size = event.size;
            try {
                await this.refresh();
            } catch (error) {
                this.pagination.page = leaving_page;
                (this.$refs["pagination"] as any).currentPage = leaving_page;
            }
        }

        async refresh(successMessage: string | null = "Refreshed !") {
            try {
                this.submitting = true;
                await this.$store.dispatch(FETCH_JOBS, this.pagination);
                this.pagination.count = this.$store.state.jobs.total;
                this.submitting = false;
                if (successMessage) Snackbar.flashMessage(successMessage, 500);
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                throw error;
            }
        }

        askCancelJob(id: string) {
            this.jobToCancel = id;
            this.openDialog("cancel_job_dialog");
        }

        async cancelJobConfirmed(id: string) {
            try {
                this.submitting = true;
                await WebAPI.cancelJob(id);
                await this.refresh(null);
                this.submitting = false;
                Snackbar.flashMessage(`Job ${id} cancelled.`);
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.closeDialog("cancel_job_dialog");
                this.openDialog("error_dialog");
                throw error;
            }

            this.closeDialog("cancel_job_dialog");
            this.refresh();
        }

        async cloneJob(id: string) {
            try {
                const response = await WebAPI.cloneJob(id);
                const pipelinerun_id = response.data.pipelinerun_id;
                const samplecart_id = response.data.samplecart_id;

                const p_response = await WebAPI.getPipelineRun(pipelinerun_id);
                const s_response = await WebAPI.getSampleCart(samplecart_id);

                const pipelinerun = p_response.data;
                const samplecart = s_response.data as ILaxySampleCart;

                let samples = new SampleCartItems();
                samples.id = samplecart.id;
                samples.items = samplecart.samples;

                for (let ss of samplecart.samples) {
                    for (let ff of ss.files) {
                        for (let field of ['R1', 'R2']) {
                            const url = ff[field];
                            // Replace and simple URL strings in the R1/R2 field with an ILaxyFile shaped object
                            if (url != undefined &&
                                typeof url === 'string' &&
                                url.includes('://')) {
                                    ff[field] = {
                                        location: url,
                                        name: url,
                                        type: 'file'} as ILaxyFile;
                            }
                        }
                    }
                }

                samples.name = samplecart.name;
                this.$store.commit(SET_SAMPLES, samples as SampleCartItems);

                this.$store.commit(SET_PIPELINE_PARAMS, pipelinerun.params);
                this.$store.commit(SET_PIPELINE_DESCRIPTION, pipelinerun.description);

                // TODO: make a prop on RNASeqSetup to allow a jump to second or last step immediately
                this.$router.push({name: 'rnaseq', params: {allowSkipping: 'true'}});

            } catch (error) {
                console.log(error)
            }
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }
    };

</script>

<style scoped>

    .colored {
        background-color: #EEEEEE;
    }

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

</style>
