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
                        <md-table-card>
                            <md-toolbar>
                                <h1 class="md-title">Jobs</h1>
                            </md-toolbar>
                            <md-table>
                                <md-table-header>
                                    <md-table-row>
                                        <md-table-head>Job</md-table-head>
                                        <md-table-head>Pipeline</md-table-head>
                                        <md-table-head>Created</md-table-head>
                                        <md-table-head>Status</md-table-head>
                                        <md-table-head>Action</md-table-head>
                                    </md-table-row>
                                </md-table-header>
                                <md-table-body>
                                    <md-table-row v-for="job in jobs" :key="job.id">
                                        <md-table-cell v-if="job.params.description">
                                            <md-tooltip md-direction="top">Job ID: {{ job.id }}</md-tooltip>
                                            {{ job.params.description }}
                                        </md-table-cell>
                                        <md-table-cell v-else="job.id">{{ job.id }}</md-table-cell>
                                        <md-table-cell>{{ job.params.pipeline }} ({{ job.params.params.genome }})
                                        </md-table-cell>
                                        <md-table-cell>
                                            <md-tooltip md-direction="top">{{ job.created_time }}</md-tooltip>
                                            {{ job.created_time| moment('from') }}
                                        </md-table-cell>
                                        <md-table-cell>
                                        <span :style="{ color: getStatusColor(job.status) }">
                                            {{ job.status }}
                                        </span>
                                        </md-table-cell>
                                        <md-table-cell>
                                            <md-toolbar class="md-dense md-transparent">
                                                <md-button class="md-icon-button"
                                                           @click="cloneJob(job.id)">
                                                    <md-tooltip md-direction="top">Run again</md-tooltip>
                                                    <md-icon>content_copy</md-icon>
                                                </md-button>
                                                <md-button class="md-icon-button"
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
    import {SET_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    import {DummyJobList as _dummyJobList} from "../test-data";

    @Component({
        props: {},
        filters: {},
        beforeRouteLeave(to: any, from: any, next: any) {
            (this as any).beforeRouteLeave(to, from, next);
        }
    })
    export default class JobList extends Vue {
        _DEBUG: boolean = false;

        public jobs: any[] = [];
        public jobToCancel: string = "";
        public pagination: { [k: string]: number } = {page_size: 10, page: 1, count: 0};

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            // this.jobs = _dummyJobList;
            // this.refresh();
            this.refresh();
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
                this.$refs['pagination'].currentPage = leaving_page;
            }
        }

        async refresh() {
            try {
                this.submitting = true;
                let response = await WebAPI.getJobs(
                    this.pagination.page,
                    this.pagination.page_size);
                let jobs: any = response.data.results;
                this.pagination["count"] = response.data.count;
                for (let key of ["created_time", "modified_time", "completed_time"]) {
                    _.update(jobs, key, function (d_str: string) {
                        return new Date(d_str);
                    });
                }
                this.submitting = false;
                this.jobs = jobs;
                // this.flashSnackBarMessage("Updated");
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
                this.submitting = false;
                // this.flashSnackBarMessage("Updated");
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.closeDialog("cancel_job_dialog");
                this.openDialog("error_dialog");
                throw error;
            }

            this.closeDialog("cancel_job_dialog");
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

        routeTo(name: string) {
            this.$router.push(name);
        }
    };

</script>
