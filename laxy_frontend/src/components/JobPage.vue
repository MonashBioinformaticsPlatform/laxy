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
                           @click="cancelJobConfirmed">Yes, cancel it.
                </md-button>
                <md-button class="md-primary"
                           @click="closeDialog('cancel_job_dialog')">Close
                </md-button>
            </md-dialog-actions>
        </md-dialog>

        <md-layout md-gutter>
            <md-layout md-flex="15" md-hide-medium>
                <md-list>
                    <nav class="vertical-sidebar-nav">
                        <md-list-item>
                            <router-link :to="`/job/${jobId}`" exact>
                                <md-icon>dashboard</md-icon>
                                <span>Summary</span></router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/input`">
                                <md-icon>folder_open</md-icon>
                                <span>Input</span></router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/output`">
                                <md-icon>folder_open</md-icon>
                                <span>Output</span></router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/eventlog`">
                                <md-icon>view_list</md-icon>
                                <span>Event Log</span></router-link>
                        </md-list-item>
                        <md-list-item>
                            <router-link :to="`/job/${jobId}/sharing`">
                                <md-icon>share</md-icon>
                                <span>Sharing</span></router-link>
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
                        <router-link tag="md-button" active-class="md-primary" :to="`/job/${jobId}/sharing`">
                            Sharing
                        </router-link>
                    </nav>
                </md-toolbar>
            </md-layout>
            <md-layout v-if="job">
                <md-layout v-if="bannerSharingLink" md-flex="90">

                    <md-button @click="$router.push(`/job/${jobId}/sharing`)"
                               :style="cssColorVars" class="shadow shared-banner">
                        <md-icon>link</md-icon>
                        Shared via secret link{{ _formatExpiryString(bannerSharingLink.expiry_time, true) }}
                    </md-button>

                </md-layout>

                <md-layout v-show="showTab === 'summary' || showTab == null"
                           id="top-panel" md-flex="90" :md-row="true">
                    <!-- smaller iconish boxes in here. eg simple status -->
                    <!-- -->
                    <md-layout md-flex="25" md-flex-medium="100">
                        <job-status-pip class="fill-width" :job="job" v-on:cancel="onAskCancelJob"></job-status-pip>
                    </md-layout>
                    <!-- -->
                    <md-layout md-flex="25" md-flex-medium="100">
                        <file-link-pip v-if="hasMultiQCReport"
                                       :url="fileUrlByTag('multiqc')"
                                       :style="`background-color: ${cssColorVars['--primary-light']}`">
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
                                             :show-cancel-button="false"
                                             v-on:cancel-job-clicked="onAskCancelJob"
                                             v-on:clone-job-clicked="cloneJob"></job-status-card>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout md-flex-medium="100"
                                   v-show="showTab === 'summary' || showTab == null" md-column>
                            <file-list v-if="job != null && job.status !== 'running'"
                                       ref="report-files"
                                       title="Reports"
                                       :fileset-id="job.output_fileset_id"
                                       :tag-filters="['report', 'html']"
                                       :hide-search="true"
                                       :job-id="jobId"
                                       @refresh-error="showErrorDialog">
                            </file-list>
                            <file-list v-if="job != null && job.status !== 'running'"
                                       ref="count-files"
                                       title="Count files"
                                       :fileset-id="job.output_fileset_id"
                                       :tag-filters="['degust', 'counts']"
                                       :hide-search="true"
                                       :job-id="jobId"
                                       @refresh-error="showErrorDialog">
                            </file-list>
                            <file-list v-if="job != null && job.status !== 'running'"
                                       ref="alignment-files"
                                       title="Alignment files"
                                       :fileset-id="job.output_fileset_id"
                                       :tag-filters="['bam', 'bai']"
                                       :hide-search="false"
                                       :job-id="jobId"
                                       @refresh-error="showErrorDialog">
                            </file-list>

                            <!--
                            <nested-file-list v-if="job && job.status !== 'running'"
                                              id="key-files-card"
                                              class="fill-width"
                                              ref="key-files"
                                              title="Key result files"
                                              :fileTree="fileTree"
                                              :tag-filters="['bam', 'bai', 'counts', 'degust', 'report']"
                                              :job-id="jobId"
                                              :hide-search="false"
                                              @refresh-error="showErrorDialog"></nested-file-list>
                            -->
                            <event-log v-if="job && job.status === 'running'"
                                       ref="eventlogSummary"
                                       :job-id="jobId"
                                       @refresh-error="showErrorDialog"></event-log>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'input'" md-column-medium>
                            <md-layout id="input-files-panel">
                                <nested-file-list id="input-files-card"
                                                  class="fill-width"
                                                  ref="input"
                                                  v-if="job && job.status !== 'running'"
                                                  title="Input files"
                                                  root-path-name="input"
                                                  :fileTree="inputFilesetTree"
                                                  :job-id="jobId"
                                                  :hide-search="false"
                                                  @refresh-error="showErrorDialog"></nested-file-list>
                            </md-layout>
                        </md-layout>
                    </transition>
                    <transition name="fade">
                        <md-layout v-show="showTab === 'output'" md-column-medium>
                            <md-layout id="output-files-panel">
                                <nested-file-list id="output-files-card"
                                                  class="fill-width"
                                                  ref="output"
                                                  v-if="job && job.status !== 'running'"
                                                  title="Output files"
                                                  root-path-name="output"
                                                  :fileTree="outputFilesetTree"
                                                  :job-id="jobId"
                                                  :hide-search="false"
                                                  @refresh-error="showErrorDialog"></nested-file-list>
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
                    <transition name="fade">
                        <md-layout v-show="showTab === 'sharing'" md-column-medium>
                            <md-layout id="sharing-panel" md-column>
                                <md-whiteframe v-if="sharingLinks && sharingLinks.length > 0" class="pad-32">
                                    <h3>Sharing {{ sharingLinks.length | pluralize('Link') }}</h3>
                                    <md-table>
                                        <md-table-header>
                                            <md-table-row>
                                                <md-table-head>
                                                    Link
                                                </md-table-head>
                                                <md-table-head>
                                                    Expires
                                                </md-table-head>
                                                <md-table-head style="text-align: right;">
                                                    Action
                                                </md-table-head>
                                            </md-table-row>
                                        </md-table-header>
                                        <md-table-body>
                                            <md-table-row v-for="link in sharingLinks" :key="link.id">
                                                <md-table-cell>
                                                    <a v-if="!_linkIsExpired(link)"
                                                       @click.prevent.stop="setClipboardFlash(_formatSharingLink(link), 'Copied link to clipboard !')"
                                                       :id="link.id"
                                                       :href="_formatSharingLink(link)">
                                                        <md-icon>link</md-icon>
                                                        {{ _formatSharingLink(link) | truncate }}
                                                    </a>
                                                    <span v-else>
                                                    <md-icon>timer_off</md-icon>
                                                        <span class="expired-link">
                                                        {{ _formatSharingLink(link) | truncate }}
                                                        </span>
                                                    </span>
                                                </md-table-cell>
                                                <md-table-cell>
                                                    <span :class="{ 'expired-link': _linkIsExpired(link) }">{{ _formatExpiryString(link.expiry_time) }}</span>
                                                    <md-menu md-size="4" class="push-left">
                                                        <md-button class="md-icon-button"
                                                                   md-menu-trigger>
                                                            <md-icon>arrow_drop_down</md-icon>
                                                        </md-button>

                                                        <md-menu-content>
                                                                <span class="md-subheading"
                                                                      style="font-weight: bold; padding-left: 16px">Change expiry to</span>
                                                            <!--  -->
                                                            <md-menu-item
                                                                    v-for="expires_in in access_token_lifetime_options"
                                                                    :key="expires_in"
                                                                    @click="updateSharingLink(jobId, expires_in)">
                                                                <span v-if="typeof expires_in == 'number'">
                                                                    {{ expires_in | duration('seconds').humanize() }} from now
                                                                </span>
                                                                <span v-else>{{ expires_in }} expires</span>
                                                            </md-menu-item>
                                                        </md-menu-content>
                                                    </md-menu>
                                                </md-table-cell>
                                                <md-table-cell md-numeric>
                                                    <md-button v-if="!_linkIsExpired(link)"
                                                               class="md-icon-button push-right"
                                                               @click="setClipboardFlash(_formatSharingLink(link), 'Copied link to clipboard !')">
                                                        <md-icon>file_copy</md-icon>
                                                        <md-tooltip md-direction="top">Copy</md-tooltip>
                                                    </md-button>
                                                    <md-button class="md-icon-button"
                                                               :class="{'push-right': _linkIsExpired(link)}"
                                                               @click="deleteSharingLink(link.id)">
                                                        <md-icon>delete</md-icon>
                                                        <md-tooltip md-direction="top">Delete</md-tooltip>
                                                    </md-button>
                                                </md-table-cell>
                                            </md-table-row>
                                        </md-table-body>
                                    </md-table>
                                </md-whiteframe>
                                <md-whiteframe class="pad-32" v-else>
                                    <h3>Create secret public link</h3>
                                    <md-input-container>
                                        <label for="access_token_lifetime">Expires in</label>
                                        <md-select name="access_token_lifetime"
                                                   id="access_token_lifetime"
                                                   v-model="sharing.lifetime">
                                            <md-option v-for="expires_in in access_token_lifetime_options"
                                                       :key="expires_in"
                                                       :value="expires_in">
                                                <span v-if="typeof expires_in == 'number'">
                                                    {{ expires_in | duration('seconds').humanize() }}
                                                </span>
                                                <span v-else>{{ expires_in }}</span></md-option>
                                        </md-select>
                                    </md-input-container>
                                    <md-button class="md-raised md-primary"
                                               @click="updateSharingLink(jobId, sharing.lifetime)">Create
                                    </md-button>
                                </md-whiteframe>
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

    import "es6-promise";

    import filter from "lodash-es/filter";
    import {Memoize} from "lodash-decorators";

    const Clipboard = require('clipboard');

    import * as moment from 'moment';

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

    import {NotImplementedError} from "../exceptions";
    import {ComputeJob, LaxyFile} from "../model";
    import {WebAPI} from "../web-api";
    import {
        palette,
        getStatusColor,
        themeColors,
        getThemeColor,
        getThemedStatusColor,
        cssColorVars
    } from "../palette";

    import {FETCH_FILESET, FETCH_JOB} from "../store";
    import {DummyJobList as _dummyJobList} from "../test-data";
    import JobStatusPip from "./JobStatusPip";
    import FileLinkPip from "./FileLinkPip";
    import NestedFileList from "./NestedFileList";
    import {EMPTY_TREE_ROOT, fileListToTree, TreeNode} from "../file-tree-util";

    @Component({
        components: {FileLinkPip, JobStatusPip, NestedFileList},
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

        public showTab: "summary" | "input" | "output" | "eventlog" | "sharing";

        private _days = 24 * 60 * 60;  // seconds in a day
        public access_token_lifetime_options: any[] = [
            1 * this._days,
            2 * this._days,
            7 * this._days,
            30 * this._days,
            'Never (∞)']
        public sharing: any = {lifetime: this.access_token_lifetime_options[3]};

        public sharingLinks: any[] = [];

        public refreshing: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        private _refreshPollerId: number | null = null;

        getStatusColor = getStatusColor;
        themeColors = themeColors;
        getThemeColor = getThemeColor;
        getThemedStatusColor = getThemedStatusColor;

        get cssColorVars() {
            return cssColorVars();
        }

        get files(): LaxyFile[] {
            return this.$store.getters.currentJobFiles;
        }

        get fileTree(): TreeNode<LaxyFile> {
            if (!this.files) return EMPTY_TREE_ROOT;
            return fileListToTree(this.files || []);
        }

        get inputFiles(): LaxyFile[] | null {
            if (this.job) {
                const fsid = this.job.input_fileset_id;
                if (this.$store.state.filesets[fsid]) {
                    return this.$store.state.filesets[fsid].files;
                }
            }
            return null;
        }

        get inputFilesetTree(): TreeNode<LaxyFile> {
            if (!this.inputFiles) return EMPTY_TREE_ROOT;
            return fileListToTree(this.inputFiles || []);
        }

        get outputFiles(): LaxyFile[] | null {
            if (this.job) {
                const fsid = this.job.output_fileset_id;
                if (this.$store.state.filesets[fsid]) {
                    return this.$store.state.filesets[fsid].files;
                }
            }
            return null;
        }

        get outputFilesetTree(): TreeNode<LaxyFile> {
            if (!this.outputFiles) return EMPTY_TREE_ROOT;
            return fileListToTree(this.outputFiles || []);
        }

        get bannerSharingLink(): string | null {
            if (this.sharingLinks &&
                this.sharingLinks.length > 0 &&
                !this._linkIsExpired(this.sharingLinks[0])) {

                return this.sharingLinks[0];
            } else {
                return null;
            }
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

        async setClipboard(text: string) {
            return new Promise(function (resolve, reject) {
                const tmp_button = document.createElement('button');
                const clipboard = new Clipboard(tmp_button, {
                    text: function () {
                        return text
                    },
                    action: function () {
                        return 'copy'
                    },
                    container: document.body
                });
                clipboard.on('success', function (e: Promise<string>) {
                    clipboard.destroy();
                    resolve(e);
                });
                clipboard.on('error', function (e: Promise<string>) {
                    clipboard.destroy();
                    reject(e);
                });
                tmp_button.click();
            });
        }

        _formatSharingLink(link: any) {
            const rel = `#/job/${link.object_id}/?access_token=${link.token}`;
            return this._relToFullLink(rel);
        }

        _relToFullLink(rel_link: string) {
            const tmp_a = document.createElement('a') as HTMLAnchorElement;
            tmp_a.href = rel_link;
            const abs_link = tmp_a.href;
            return abs_link;
        }

        async setClipboardFlash(text: string, message: string, failMessage: string = "Failed to copy to clipboard :/") {
            try {
                const displayTime = (message.length * 20) + 500;
                await this.setClipboard(text);
                this.flashSnackBarMessage(message, displayTime);
            } catch (error) {
                const displayTime = (failMessage.length * 20) + 1000;
                this.flashSnackBarMessage(failMessage, displayTime);
            }
        }

        async mounted() {
            await this.refresh(null);

            if (this.job && (this.job.status === "running" || this.job.status === "created")) {
                this._refreshPollerId = setInterval(() => {
                    this.refresh(null);
                }, 10000);  // ms
            }
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
            return filter(this.files, (f) => {
                return f.type_tags.includes(tag);
            });
        }

        async refresh(successMessage: string | null = "Updated") {
            try {
                this.refreshing = true;
                // const response = await WebAPI.getJob(this.jobId);
                // this.job = response.data as ComputeJob;

                this.getSharingLinks();

                await this.$store.dispatch(FETCH_JOB, {
                    job_id: this.jobId,
                    access_token: this.$route.query.access_token
                });

                let eventlog = null;
                if (this.showTab == "eventlog") {
                    eventlog = (this.$refs.eventlog as any);
                }
                if (this.showTab == "summary") {
                    eventlog = (this.$refs.eventlogSummary as any);
                }
                if (eventlog) await eventlog.refresh();

                this.job = this.$store.state.currentViewedJob;

                // do web requests if filesets not yet populated
                if (this.job) {
                    const fetches = [];
                    for (let fsid of [this.job.input_fileset_id, this.job.output_fileset_id]) {
                        if (fsid && !this.$store.state.filesets[fsid]) {
                            fetches.push(this.$store.dispatch(FETCH_FILESET, fsid));
                        }
                    }
                    await Promise.all(fetches);
                }

                // These refresh the appropriate file list every time it's
                // displayed
                // if (this.showTab == "summary") {
                //     (this.$refs['key-files'] as any).refresh();
                // }
                // if (this.showTab == "output") {
                //     (this.$refs.output as any).refresh();
                // }
                // if (this.showTab == "input") {
                //     (this.$refs.input as any).refresh();
                // }

                // if (this.showTab == "eventlog") {
                //     (this.$refs.eventlog as any).refresh();
                // }

                this.refreshing = false;
                if (successMessage) this.flashSnackBarMessage(successMessage, 500);
            } catch (error) {
                console.log(error);
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

        async cancelJobConfirmed() {
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

        /*
         NOTE: By using the WebAPI.*JobAccessToken methods, we only allow a single sharing link per-job to be created
         (via the UI). The createAccessToken, getAccessTokens methods could be used instead to allow creation of
         multiple tokens per-job.
         */
        async updateSharingLink(job_id: string, expires_in: number | string) {
            let expiry_time = null;
            if (typeof expires_in == 'string' && expires_in.includes('Never')) {
                expiry_time = null;
            } else {
                let expiry: Date = new Date();
                expiry.setSeconds(expires_in as number);
                expiry_time = expiry.toISOString();
            }
            try {
                const resp = await WebAPI.putJobAccessToken(this.jobId, expiry_time);
                this.getSharingLinks();
            } catch (error) {
                console.log(error);
            }
        }

        async getSharingLinks() {
            try {
                const resp = await WebAPI.getJobAccessToken(this.jobId);
                this.sharingLinks = [];
                const link = resp.data;
                if (link) this.sharingLinks = [link];
            } catch (error) {
                console.log(error);
            }
            return [];
        }

        async deleteSharingLink(link_id: string) {
            try {
                const resp = await WebAPI.deleteAccessToken(link_id);
                this.getSharingLinks();
            } catch (error) {
                console.log(error);
            }
        }

        _formatExpiryString(expiry_time: Date | null, add_sentence_words?: boolean) {
            if (expiry_time == null) {
                if (add_sentence_words) {
                    return ', never expires'
                } else {
                    return 'Never';
                }
            }
            const m = moment(expiry_time);
            let suffix = 'from now';
            if (m.isBefore(Date.now())) {
                suffix = 'ago';
            }
            let formatted = `${m.format("L, h:mm a")} (${m.fromNow(true)} ${suffix})`;
            if (add_sentence_words) {
                formatted = ` until ${formatted}`;
            }
            return formatted;
        }

        @Memoize((link: any) => link.id)
        _linkIsExpired(link: any) {
            return moment(link.expiry_time).isBefore(Date.now());
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
    .shared-banner {
        background-color: var(--accent-light);
        width: 100%;
        text-align: center;
    }

    .expired-link {
        text-decoration: line-through;
    }

    .no-margin {
        margin: 0 !important;
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

    .vertical-sidebar-nav a.router-link-active::after {
        content: " »";
    }
</style>
