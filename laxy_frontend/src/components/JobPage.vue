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
                <md-layout id="top-panel" md-flex="90" :md-row="true">
                    <!-- smaller iconish boxes in here. eg simple status -->
                    <!-- -->
                    <md-layout md-flex="25" md-flex-medium="100">
                        <job-status-pip class="fill-width" :job="job"></job-status-pip>
                    </md-layout>
                    <!-- -->
                    <md-layout md-flex="25" md-flex-medium="100">
                        <file-link-pip v-if="hasMultiQCReport"
                                       :url="fileUrlByTag('multiqc')"
                                       style="background-color: #9fa8da">
                            <span slot="title">MultiQC report</span>
                            <span slot="subtitle">Open in new tab</span>
                        </file-link-pip>
                    </md-layout>

                    <!-- input and output file total sizes in pip card -->
                    <!-- pipeline reference genome (icon on organism or DNA double-helix for non-model) -->
                    <!-- pipeline type and version -->

                </md-layout>
                <md-layout id="main-panel" md-flex="90">
                    <transition name="fade">
                        <md-layout md-flex="40" md-flex-medium="100"
                                   v-show="showTab === 'summary' || showTab == null" :md-column-medium="true"
                                   :md-row-large="true">
                            <job-status-card :job="job"
                                             v-on:cancel-job-clicked="onAskCancelJob"
                                             v-on:clone-job-clicked="cloneJob"></job-status-card>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout md-flex="40" md-flex-medium="100"
                                   v-show="showTab === 'summary' || showTab == null" :md-column-medium="true"
                                   :md-row-large="true">
                            <file-list v-if="job != null && job.status !== 'running'"
                                       ref="keyFiles"
                                       class="fill-width"
                                       title="Key result files"
                                       :fileset-id="job.output_fileset_id"
                                       :regex-filters="['\\.html$', '\\.counts$', 'StrandedCounts.*\\.txt$', '^strandInfo\\.txt$', '\\.bam$', '\\.bai$', '\\.log$', '\\.out$']"
                                       :hide-search="false"
                                       :job-id="jobId"
                                       @refresh-error="showErrorDialog">
                            </file-list>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'input'" md-column-medium>
                            <md-layout id="input-files-panel">
                                <file-list id="input-files-card"
                                           ref="input"
                                           v-if="job != null && job.status !== 'running'"
                                           title="Input files"
                                           :fileset-id="job.input_fileset_id"
                                           :job-id="jobId"
                                           :hide-search="false"
                                           @refresh-error="showErrorDialog"></file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'output'" md-column-medium>
                            <md-layout id="output-files-panel">
                                <file-list ref="output"
                                           id="output-files-card"
                                           v-if="job != null && job.status !== 'running'"
                                           title="Output files"
                                           :fileset-id="job.output_fileset_id"
                                           :hide-search="false"
                                           @refresh-error="showErrorDialog"></file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'eventlog'" md-column-medium>
                            <md-layout id="eventlog-panel">
                                <event-log ref="eventlog"
                                           :job-id="jobId"
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

    import {NotImplementedError} from "../exceptions";
    import {ComputeJob} from "../model";
    import {WebAPI} from "../web-api";
    import {
        palette,
        getStatusColor,
        themeColors,
        getThemeColor,
        getThemedStatusColor
    } from "../palette";

    import {FETCH_FILESET, FETCH_JOB} from "../store";
    import {DummyJobList as _dummyJobList} from "../test-data";
    import JobStatusPip from "./JobStatusPip";
    import FileLinkPip from "./FileLinkPip";

    @Component({
        components: {FileLinkPip, JobStatusPip},
        props: {
            jobId: {type: String, default: ""},
            showTab: {type: String, default: "summary"}
        },
        filters: {},
    })
    export default class JobPage extends Vue {
        _DEBUG: boolean = false;

        public job: ComputeJob | null = null;
        // TODO: Put file list / job record in Vuex, make this a read only
        //       computed property derived from the store
        public jobId: string;

        public showTab: "summary" | "input" | "output" | "eventlog";

        public refreshing: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        private _refreshPollerId: number | null = null;

        getStatusColor = getStatusColor;
        themeColors = themeColors;
        getThemeColor = getThemeColor;
        getThemedStatusColor = getThemedStatusColor;
        // for lodash in templates
        _ = _;

        get files(): LaxyFile[] {
            return this.$store.getters.currentJobFiles;
        }

        // @Getter("currentInputFileset")
        // inputFileset: LaxyFileSet;
        //
        // @Getter("currentOutputFileset")
        // outputFileset: LaxyFileSet;

        created() {
            // this.jobId = _dummyJobList[0].id || '';
            // this.job = _dummyJobList[0];
            // this.jobId = '5ozQUwFCJDoV0vWgmo4q6E';
            // this.refresh(null);
        }

        mounted() {
            this.refresh(null);

            this._refreshPollerId = setInterval(() => {
                this.refresh(null);
            }, 10000);  // ms
        }

        beforeDestroy() {
            if (this._refreshPollerId != null) clearInterval(this._refreshPollerId);
        }

        openFileByPath(filepath: string) {
            window.open(WebAPI.viewJobFileByPathUrl(this.jobId, filepath));
        }

        openFileByTag(tag: string) {
            const file = this.filesByTag(tag).shift();
            if (file && file.id) {
                window.open(WebAPI.viewFileByIdUrl(file.id));
            }
        }

        fileUrlByTag(tag: string): string | null {
            const file = this.filesByTag(tag).shift();
            if (file && file.id) {
                // return WebAPI.viewFileByIdUrl(file.id);
                return WebAPI.viewJobFileByPathUrl(
                    this.jobId,
                    `${file.path}/${file.name}`);
            }
            return null;
        }

        hasFileTagged(tag: string): boolean {
            return this.filesByTag(tag).length > 0;
        }

        get hasMultiQCReport(): boolean {
            return this.hasFileTagged("multiqc");
        }

        filesByTag(tag: string): LaxyFile[] {
            return _.filter(this.files, (f) => {
                return f.type_tags.includes(tag);
            });
        }

        async refresh(successMessage: string | null = "Updated") {
            try {
                this.refreshing = true;
                // const response = await WebAPI.getJob(this.jobId);
                // this.job = response.data as ComputeJob;
                await this.$store.dispatch(FETCH_JOB, this.jobId);
                this.job = this.$store.state.currentViewedJob;
                // if (this.job &&
                //     this.job.input_fileset_id &&
                //     this.job.output_fileset_id) {
                //     await Promise.all([
                //         this.$store.dispatch(FETCH_FILESET, this.job.input_fileset_id),
                //         this.$store.dispatch(FETCH_FILESET, this.job.output_fileset_id)
                //     ]);
                // }

                if (this.showTab == "summary") {
                    (this.$refs.keyFiles as any).refresh();
                }
                if (this.showTab == "output") {
                    (this.$refs.output as any).refresh();
                }
                if (this.showTab == "input") {
                    (this.$refs.input as any).refresh();
                }

                if (this.showTab == "eventlog") {
                    (this.$refs.eventlog as any).refresh();
                }

                this.refreshing = false;
                if (successMessage) this.flashSnackBarMessage(successMessage, 500);
            } catch (error) {
                console.log(JSON.parse(JSON.stringify(error)));
                this.refreshing = false;
                this.error_alert_message = error.toString();
                if (error.response && error.response.status != 401) {
                    this.openDialog("error_dialog");
                    throw error;
                }
            }
        }

        onAskCancelJob(job_id: string) {
            this.openDialog("cancel_job_dialog");
        }

        async cancelJobConfirmed(id: string) {
            try {
                this.refreshing = true;
                await WebAPI.cancelJob(this.jobId);
                this.refreshing = false;
                this.flashSnackBarMessage("Job cancelled.");
            } catch (error) {
                console.log(error);
                this.refreshing = false;
                this.error_alert_message = error.toString();
                this.closeDialog("cancel_job_dialog");
                this.openDialog("error_dialog");
                throw error;
            }

            this.closeDialog("cancel_job_dialog");
            this.refresh(null);
        }

        cloneJob(job_id: string) {
            throw new NotImplementedError("Job cloning isn't yet implemented.");
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
