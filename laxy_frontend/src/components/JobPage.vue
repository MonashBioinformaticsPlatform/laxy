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
            <md-layout v-if="job" md-column>
                <md-layout md-gutter>
                    <md-layout md-flex="20">
                        <md-card md-with-hover>
                            <md-card-header>
                                <div class="md-title">{{ job.params.pipeline }} job</div>
                                <div class="md-subhead">{{ job.params.description }}</div>
                            </md-card-header>

                            <md-card-content>
                                <md-layout md-align="center" class="pad-32">
                                    <spinner-cube-grid v-if="job.status === 'running'"
                                                       :colors="['#3f51b5','#e91e63','#ff5722','black']"
                                                       :time="1.5"
                                                       :columns="4" :rows="4"
                                                       :width="96" :height="96"
                                                       :random-seed="hashCode(job.id)">

                                    </spinner-cube-grid>
                                    <md-icon v-if="job.status === 'failed'" class="md-size-4x md-accent">error_outline
                                    </md-icon>
                                    <md-icon v-if="job.status === 'cancelled'" class="md-size-4x md-warn">
                                        cancel_presentation
                                    </md-icon>
                                    <md-icon v-if="job.status === 'complete'" class="md-size-4x md-primary">
                                        check_circle_outline
                                    </md-icon>
                                </md-layout>
                                <md-table>
                                    <md-table-body>
                                        <md-table-row>
                                            <md-table-cell>Status</md-table-cell>
                                            <md-table-cell>
                                                <span :style="{ color: getStatusColor(job.status) }">{{ job.status }}</span>
                                            </md-table-cell>
                                        </md-table-row>
                                        <md-table-row>
                                            <md-table-cell>Created</md-table-cell>
                                            <md-table-cell>
                                                <md-tooltip md-direction="top">{{ job.created_time }}</md-tooltip>
                                                {{ job.created_time| moment('from') }}
                                            </md-table-cell>
                                        </md-table-row>
                                        <md-table-row v-if="job.completed_time">
                                            <md-table-cell>Completed</md-table-cell>
                                            <md-table-cell>
                                                <md-tooltip md-direction="top">{{ job.completed_time }}</md-tooltip>
                                                {{ job.completed_time| moment('from') }}
                                            </md-table-cell>
                                        </md-table-row>
                                        <md-table-row>
                                            <md-table-cell>Job ID</md-table-cell>
                                            <md-table-cell>{{ job.id }}</md-table-cell>
                                        </md-table-row>
                                    </md-table-body>
                                </md-table>
                            </md-card-content>

                            <md-card-actions>
                                <md-button v-if="job.status !== 'running'"
                                           @click="cloneJob(job.id)">
                                    <md-icon>content_copy</md-icon>
                                    Run again
                                </md-button>
                                <md-button v-if="job.status === 'running'"
                                           @click="askCancelJob(job.id)">
                                    <md-icon>cancel</md-icon>
                                    Cancel
                                </md-button>
                            </md-card-actions>
                        </md-card>
                    </md-layout>
                    <md-layout>
                        <file-list v-if="job != null && job.status !== 'running'"
                                   title="Key result files"
                                   :fileset-id="job.output_fileset_id"
                                   :regex-filters="['\\.html$', '\\.count$', '\\.bam$', '\\.bai$', '\\.log$', '\\.out$']"
                                   :hide-search="false">
                        </file-list>
                    </md-layout>
                </md-layout>
                <file-list v-if="job != null && job.status !== 'running'" title="Input files"
                           :fileset-id="job.input_fileset_id"></file-list>
                <file-list v-if="job != null && job.status !== 'running'" title="Output files"
                           :fileset-id="job.output_fileset_id"></file-list>
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
    import {WebAPI} from "../web-api";

    import {DummyJobList as _dummyJobList} from "../test-data";

    @Component({
        props: {jobId: String},
        filters: {},
    })
    export default class JobPage extends Vue {
        _DEBUG: boolean = false;

        public job: ComputeJob | null = null;
        public jobId: string;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            //this.jobId = _dummyJobList[0].id || '';
            //this.job = _dummyJobList[0];
            // this.jobId = '5ozQUwFCJDoV0vWgmo4q6E';
            this.refresh();
        }

        // TODO: Refactor me somewhere to combine with the method in JobList
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

        // http://werxltd.com/wp/2010/05/13/javascript-implementation-of-javas-string-hashcode-method/
        hashCode(s: string){
                        console.log((Vue as any).material.currentTheme);
            var hash = 0;
            if (s.length == 0) return hash;
            for (let i = 0; i < s.length; i++) {
                let char = s.charCodeAt(i);
                hash = ((hash<<5)-hash)+char;
                hash = hash & hash; // Convert to 32bit integer
            }
            return hash;
        }

        async refresh() {
            try {
                this.submitting = true;
                const response = await WebAPI.getJob(this.jobId);
                this.job = response.data as ComputeJob;
                this.submitting = false;
                this.flashSnackBarMessage("Updated", 500);
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
            this.refresh();
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

</style>
