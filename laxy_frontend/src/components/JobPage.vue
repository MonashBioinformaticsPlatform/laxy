<template>
  <div>
    <md-dialog-alert :md-content-html="error_alert_message" :md-content="error_alert_message"
      ref="error_dialog"></md-dialog-alert>

    <md-dialog md-open-from="#add_menu_button" md-close-to="#add_menu_button" ref="cancel_job_dialog">
      <md-dialog-title>Cancel job</md-dialog-title>

      <md-dialog-content>Are you sure ?</md-dialog-content>

      <md-dialog-actions>
        <md-button class="md-primary" @click="cancelJobConfirmed">Yes, cancel it.</md-button>
        <md-button class="md-primary" @click="closeDialog('cancel_job_dialog')">Close</md-button>
      </md-dialog-actions>
    </md-dialog>

    <ExpiryDialog ref="expiryInfoDialog" :job="job"></ExpiryDialog>
    <DownloadHelpDialog ref="downloadHelpDialog" :tarballUrl="tarballUrl"></DownloadHelpDialog>

    <banner-notice v-if="job && jobExpiresSoon && showTopBanner" @click="openDialog('expiryInfoDialog')" :type="jobExpiresSoon && !job.expired
      ? 'warning'
      : job.expired
        ? 'error'
        : 'clear'
      ">
      <span v-if="!job.expired">
        Job expires {{ jobExpiresSoon ? "in less than 7 days" : "" }} on
        &nbsp;{{ job.expiry_time }}
      </span>
      <span v-if="job.expired">Job has expired - large files are no longer available</span>
    </banner-notice>

    <!-- <PopupBlockerBanner :do-test-on-create="false"></PopupBlockerBanner> -->

    <md-layout md-gutter>
      <md-layout md-flex="15" md-hide-medium>
        <md-list>
          <nav class="vertical-sidebar-nav">
            <md-list-item v-for="tab in tabs" :key="tab.name">
              <router-link v-if="tab.showWithoutAuth || isAuthenticated" :to="{
                path: `/job/${jobId}${tab.path}`,
                query: persistQueryParams
              }" replace :exact="tab.exact">
                <md-icon>{{ tab.icon }}</md-icon>
                <span>{{ tab.text }}</span>
              </router-link>
            </md-list-item>
          </nav>
        </md-list>
      </md-layout>
      <md-layout md-hide-large-and-up md-flex-medium="100">
        <md-toolbar class="md-transparent" style="width: 100%">
          <nav style="width: 100%">
            <template v-for="tab in tabs">
              <router-link :key="tab.name" v-if="tab.showWithoutAuth || isAuthenticated" tag="md-button"
                active-class="md-primary" :to="{
                  path: `/job/${jobId}${tab.path}`,
                  query: persistQueryParams
                }" replace :exact="tab.exact">{{ tab.text }}</router-link>
            </template>
          </nav>
        </md-toolbar>
      </md-layout>
      <md-layout v-if="job" md-gutter="16">
        <md-layout id="top-panel-banner" v-show="showTab === 'summary' || showTab == null"
          v-if="job && jobIsDone && badInputFile" md-flex="100" md-gutter="16" md-column style="padding-right: 24px;">
          <generic-pip class="fill-width" cardClass stripeColor="warn" icon="broken_image" buttonIcon buttonText>
            <template>
              <span slot="title">Bad input file(s)</span>
              <span slot="subtitle">
                It appears your job failed due to a problem with the input file:
                <strong>{{ badInputFile }}</strong>
                <br />The file may be corrupt or not a valid FASTQ file - please
                verify before trying again. <br />If you believe your input file
                is okay and the problem persists, please don't hestiate to
                contact us for further assistance.
              </span>
            </template>
          </generic-pip>
        </md-layout>

        <md-layout v-show="showTab === 'summary' || showTab == null" id="top-panel" md-flex="100" :md-row="true"
          md-gutter="16">
          <!-- smaller iconish boxes in here. eg simple status -->
          <!-- -->
          <md-layout md-flex="25" md-flex-medium="100">
            <job-status-pip class="fill-width" :job="job" v-on:cancel="onAskCancelJob"></job-status-pip>
          </md-layout>
          <!-- -->
          <md-layout v-if="hasMultiQCReport" md-flex="25" md-flex-medium="100">
            <generic-pip @click="openLinkInTab(fileUrlByTag('multiqc'))"
              :style="`background-color: ${cssColorVars['--primary-light']}`" class="fill-width" stripeColor="primary"
              icon="list" buttonIcon buttonText>
              <span slot="title">MultiQC report</span>
              <span slot="subtitle">Open in new tab</span>
            </generic-pip>
          </md-layout>

          <md-layout v-if="hasDegustCounts" md-flex="25" md-flex-medium="100">
            <generic-pip @click.stop.native :hover="false" :style="`background-color: ${cssColorVars['--primary-light']}`"
              class="fill-width" stripeColor="primary" icon="dashboard" buttonIcon buttonText>
              <span slot="title">Send to Degust</span>
              <span slot="subtitle">
                <template v-if="strandednessGuess">
                  This library appears to be
                  <strong>
                    <em>{{ strandednessGuess }}</em>
                  </strong>
                  <template v-if="strandBias">
                    with an overall strand bias of
                    {{ strandBias | numeral_format("0.00") }}
                  </template>
                  .
                </template>
                See the "Count files" section below for other options.
              </span>
              <template slot="content" style="list-style-type: none;">
                <span v-for="countsFile in primaryCountsFiles" :key="countsFile.id">
                  <md-button @click="openDegustLink(countsFile.id)" target="_blank">
                    <md-icon>send</md-icon>&nbsp;{{
                      _countsFileInfo(countsFile).featureSet
                    }}&nbsp;

                    <md-tooltip>{{ countsFile.path }}/{{ countsFile.name }}</md-tooltip>
                  </md-button>
                </span>
              </template>
            </generic-pip>
          </md-layout>

          <md-layout v-if="bannerSharingLink" md-flex="25" md-flex-medium="100">
            <generic-pip class="fill-width" @click="
              $router.push({
                path: `/job/${jobId}/sharing`,
                query: persistQueryParams
              })
              " stripeColor="warn" icon="share" buttonIcon buttonText>
              <span slot="title">Shared via secret link</span>
              <span slot="subtitle">
                This job is accessible by anyone with the secret link
                <strong>{{
                  _formatExpiryString(bannerSharingLink.expiry_time, true)
                }}</strong>.
              </span>
            </generic-pip>
          </md-layout>

          <md-layout v-if="job && job.expiry_time && jobIsDone" md-flex="25" md-flex-medium="100">
            <generic-pip class="fill-width" @click="openDialog('expiryInfoDialog')" :cardClass="jobExpiresSoon ? (job.expired ? 'accent' : 'warn') : ''
              " :stripeColor="jobExpiresSoon ? '' : 'warn'" :icon="jobExpiresSoon ? 'warning' : ''" buttonIcon
              buttonText>
              <template v-if="!job.expired">
                <span slot="title">Job expiry
                  {{ jobExpiresSoon ? "in less than 7 days" : "" }}</span>
                <span slot="subtitle">
                  Large files associated with this job will be deleted on
                  <br />
                  <strong>{{
                    job.expiry_time | moment("DD-MMM-YYYY (HH:mm UTCZ)")
                  }}</strong>
                </span>
              </template>
              <template v-else>
                <span slot="title">Job has expired.</span>
                <span slot="subtitle">Large files associated with this job are no longer
                  available</span>
              </template>
            </generic-pip>
          </md-layout>

          <!--
                    <md-layout md-flex="100">
                        <md-toolbar @click.stop.native=""
                                    class="shadow fill-width"
                                    :class="{'md-primary': false, 'md-transparent': true, 'md-accent': false}">
                            <span style="flex: 1"></span>
                            <h4><a :href="tarballUrl" @click.prevent="">Download job files (.tar.gz)</a></h4>
                            <span style="flex: 1"></span>
                            <md-button class="md-icon-button" @click.prevent="openLinkInTab(tarballUrl)">
                                <md-icon>save_alt</md-icon>
                            </md-button>
                        </md-toolbar>
                    </md-layout>
          !-->

          <!-- input and output file total sizes in pip card -->
          <!-- pipeline reference genome (icon on organism or DNA double-helix for non-model) -->
          <!-- pipeline type and version -->
        </md-layout>
        <md-layout id="main-panel" md-flex="100" md-gutter="16">
          <transition name="fade">
            <md-layout md-flex="40" md-flex-medium="100" v-show="showTab === 'summary' || showTab == null"
              :md-column-medium="true" :md-row-large="true">
              <job-status-card v-if="job && job.params" :job="job" :show-cancel-button="false"
                :show-run-again-button="isJobOwner" :extra-table-rows="jobParamRows"
                v-on:cancel-job-clicked="onAskCancelJob" v-on:clone-job-clicked="cloneJob"></job-status-card>
            </md-layout>
          </transition>
          <transition name="fade">
            <md-layout id="right-column" md-flex-medium="100" v-show="showTab === 'summary' || showTab == null" md-column>
              <md-progress v-if="refreshing" md-indeterminate></md-progress>
              <file-list v-if="job && jobIsDone && hasFilesWithTags(['report', 'html'])" class="shadow" ref="report-files"
                title="Reports" :fileset-id="job.output_fileset_id" :tag-filters="['report', 'html']"
                :exclude-tags="['fastqc']" :hide-search="true" :job-id="jobId"
                @refresh-error="showErrorDialog"></file-list>
              <file-list v-if="job && jobIsDone && hasFilesWithTags(['counts', 'strand-info'])"
                ref="count-files" title="Recommended count files" :fileset-id="job.output_fileset_id"
                :tag-filters="['counts', 'strand-info']" :hide-search="true" :job-id="jobId"
                @action-error="showErrorDialog" @refresh-error="showErrorDialog"></file-list>
              <file-list v-if="job && jobIsDone && hasFilesWithTags(['fastqc'])" ref="report-files" title="FastQC Reports"
                :fileset-id="job.output_fileset_id" :tag-filters="['fastqc']" :hide-search="true" :job-id="jobId"
                @refresh-error="showErrorDialog"></file-list>
              <file-list v-if="job && jobIsDone && hasFilesWithTags(['bam', 'bai'])" ref="alignment-files"
                title="Alignment files" :fileset-id="job.output_fileset_id" :tag-filters="['bam', 'bai']"
                :hide-search="false" :job-id="jobId" @refresh-error="showErrorDialog"></file-list>

              <!-- TODO: This Openfold/Alphafold specifc box should be split out into a specific 
                         JobPage summary tab component used just for these pipelines -->
              <laxy-ngl-viewer :job-id="job.id"
                :file-id="filesByRegex(outputFiles, [new RegExp('.*_relaxed\.pdb$')])[0].id"
                v-if="job && jobIsDone && (filesByRegex(outputFiles, [new RegExp('.*_relaxed\.pdb$')]).length > 0)">
              </laxy-ngl-viewer>

              <!--
                            <nested-file-list v-if="jobIsRunning"
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
              <event-log v-if="jobIsRunning" ref="eventlogSummary" :job-id="jobId"
                @refresh-error="showErrorDialog"></event-log>
            </md-layout>
          </transition>
          <transition name="fade">
            <md-layout v-show="showTab === 'input'" md-column-medium>
              <md-progress v-if="refreshing" md-indeterminate></md-progress>
              <md-layout id="input-files-panel">
                <nested-file-list v-if="job && inputFilesetTree.children.length" id="input-files-card" class="fill-width"
                  ref="input" title="Input files" root-path-name="input" :fileTree="inputFilesetTree" :job-id="jobId"
                  :hide-search="false" @refresh-error="showErrorDialog"></nested-file-list>
                <md-layout v-else-if="!refreshing" md-align="center">No files.</md-layout>
              </md-layout>
            </md-layout>
          </transition>
          <transition name="fade">
            <md-layout v-show="showTab === 'output'">
              <md-progress v-if="refreshing" md-indeterminate></md-progress>
              <md-layout v-if="jobIsDone" md-flex="100">
                <md-whiteframe class="pad-32 fill-width">
                  <div>
                    <h3 style="display: inline; float: left; margin-top:-8px;">
                      Download all job files
                      <span v-if="job && job.params && job.params.tarball_size">(~
                        {{ job.params.tarball_size | humanize_bytes }})</span>
                    </h3>
                    <md-button id="helpButton" @click="openDialog('downloadHelpDialog')"
                      class="push-right md-icon-button md-raised md-dense" style="display: inline;">
                      <md-icon style="color: #bdbdbd;">help</md-icon>
                    </md-button>
                  </div>
                  <DownloadJobFilesTable :url="tarballUrl" :filename="jobId + '.tar.gz'"
                    @flash-message="flashSnackBarEvent"></DownloadJobFilesTable>
                </md-whiteframe>
              </md-layout>
              <md-layout id="output-files-panel" md-flex="100">
                <nested-file-list v-if="job && outputFilesetTree.children.length" id="output-files-card"
                  class="fill-width" ref="output" title="Output files" root-path-name="output"
                  :fileTree="outputFilesetTree" :job-id="jobId" :hide-search="false"
                  @refresh-error="showErrorDialog"></nested-file-list>
                <md-layout v-else-if="!refreshing" md-align="center">No files.</md-layout>
              </md-layout>
            </md-layout>
          </transition>
          <transition name="fade">
            <md-layout v-show="showTab === 'eventlog'" md-column-medium>
              <md-progress v-if="refreshing" md-indeterminate></md-progress>
              <md-layout id="eventlog-panel">
                <event-log ref="eventlog" :job-id="jobId" @refresh-error="showErrorDialog"></event-log>
              </md-layout>
            </md-layout>
          </transition>
          <transition name="fade">
            <md-layout v-show="showTab === 'sharing'" md-column-medium>
              <md-layout v-if="isAuthenticated" id="sharing-panel" md-column>
                <md-progress v-if="refreshing" md-indeterminate></md-progress>
                <md-whiteframe v-if="sharingLinks && sharingLinks.length > 0" class="pad-32">
                  <h3>Sharing {{ sharingLinks.length | pluralize("Link") }}</h3>
                  <sharing-link-list @flash-message="flashSnackBarEvent" @change-link="onChangeLinkEvent"
                    @delete-link="onDeleteSharingLinkEvent" :show-delete-button="isJobOwner"
                    :allow-expiry-edit="isJobOwner" :job-id="jobId" :sharing-links="sharingLinks"></sharing-link-list>
                </md-whiteframe>
                <md-whiteframe class="pad-32" v-else>
                  <h3>Create secret public link</h3>
                  <md-input-container>
                    <label for="access_token_lifetime">Expires in</label>
                    <md-select name="access_token_lifetime" id="access_token_lifetime" v-model="sharing.lifetime">
                      <md-option v-for="expires_in in access_token_lifetime_options" :key="expires_in"
                        :value="expires_in">
                        <span v-if="typeof expires_in == 'number'">{{
                          expires_in | duration("seconds").humanize()
                        }}</span>
                        <span v-else>{{ expires_in }}</span>
                      </md-option>
                    </md-select>
                  </md-input-container>
                  <md-button class="md-raised md-primary"
                    @click="updateSharingLink(jobId, sharing.lifetime)">Create</md-button>
                </md-whiteframe>
              </md-layout>
            </md-layout>
          </transition>
        </md-layout>
      </md-layout>
    </md-layout>
    <md-snackbar md-position="bottom center" ref="snackbar" :md-duration="snackbar_duration">
      <span>{{ snackbar_message }}</span>
      <md-button class="md-accent" @click="$refs.snackbar.close()">Dismiss</md-button>
    </md-snackbar>
  </div>
</template>

<script lang="ts">
import "es6-promise";

import filter from "lodash-es/filter";
import find from "lodash-es/find";
import get from "lodash-es/get";
import head from "lodash-es/head";
import { Memoize } from "lodash-decorators";

const Clipboard = require("clipboard");

import * as moment from "moment";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";

import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch
} from "vue-property-decorator";

import { State, Getter, Action, Mutation, namespace } from "vuex-class";

import { NotImplementedError } from "../exceptions";
import { ComputeJob, LaxyFile, SampleCartItems } from "../model";
import { WebAPI } from "../web-api";
import {
  palette,
  getStatusColor,
  themeColors,
  getThemeColor,
  getThemedStatusColor,
  cssColorVars
} from "../palette";

import {
  FETCH_FILESET,
  FETCH_JOB,
  SET_PIPELINE_DESCRIPTION,
  SET_PIPELINE_PARAMS,
  SET_SAMPLES
} from "../store";

import {
  filterByTag,
  filterByRegex,
  filterByFullPath,
  filterByFilename
} from "../file-tree-util";

import { DummyJobList as _dummyJobList } from "../test-data";
import JobStatusPip from "./JobStatusPip.vue";
import FileLinkPip from "./FileLinkPip.vue";
import NestedFileList from "./NestedFileList.vue";
import { EMPTY_TREE_ROOT, fileListToTree, TreeNode } from "../file-tree-util";
import SharingLinkList from "./SharingLinkList.vue";
import { Snackbar } from "../snackbar";
import ExpiryDialog from "./Dialogs/ExpiryDialog.vue";
import AVAILABLE_GENOMES from "../config/genomics/genomes";
import GenericPip from "./GenericPip.vue";
import DownloadJobFilesTable from "./DownloadJobFilesTable.vue";
import DownloadHelpDialog from "./Dialogs/DownloadHelpDialog.vue";
import PopupBlockerBanner from "./PopupBlockerBanner.vue";
import BannerNotice from "./BannerNotice.vue";
import { LaxySharingLink } from "../types";

import LaxyNglViewer from "./pipelines/openfold/ui/LaxyNglViewer.vue";

@Component({
  components: {
    BannerNotice,
    PopupBlockerBanner,
    DownloadHelpDialog,
    GenericPip,
    SharingLinkList,
    FileLinkPip,
    JobStatusPip,
    NestedFileList,
    ExpiryDialog,
    DownloadJobFilesTable,
    LaxyNglViewer
  },
  props: {
    jobId: { type: String, default: "" },
    showTab: { type: String, default: "summary" }
  },
  filters: {}
})
export default class JobPage extends Vue {
  $store: any;
  $refs: any;
  WebAPI: any = WebAPI;
  filterByTag: Function = filterByTag;

  _DEBUG: boolean = false;

  // public job: ComputeJob | null = null;
  get job(): ComputeJob | null {
    return this.$store.state.currentViewedJob;
  }
  // TODO: Put file list / job record in Vuex, make this a read only
  //       computed property derived from the store
  public jobId: string;
  public output_fileset_id: string = "";
  public input_fileset_id: string = "";

  public showTab: "summary" | "input" | "output" | "eventlog" | "sharing";
  public tabs: any = [
    {
      name: "summary",
      path: "",
      text: "Summary",
      icon: "dashboard",
      exact: true,
      showWithoutAuth: true
    },
    {
      name: "input",
      path: "/input",
      text: "Input",
      icon: "folder_open",
      exact: false,
      showWithoutAuth: true
    },
    {
      name: "output",
      path: "/output",
      text: "Output",
      icon: "folder_open",
      exact: false,
      showWithoutAuth: true
    },
    {
      name: "eventlog",
      path: "/eventlog",
      text: "Event Log",
      icon: "view_list",
      exact: false,
      showWithoutAuth: true
    },
    {
      name: "sharing",
      path: "/sharing",
      text: "Sharing",
      icon: "share",
      exact: false,
      showWithoutAuth: false
    }
  ];

  private _days = 24 * 60 * 60; // seconds in a day
  public access_token_lifetime_options: any[] = [
    1 * this._days,
    2 * this._days,
    7 * this._days,
    30 * this._days,
    "Never (∞)"
  ];
  public sharing: any = { lifetime: this.access_token_lifetime_options[3] };

  public sharingLinks: LaxySharingLink[] = [];

  public showTopBanner: boolean = true;

  public refreshing: boolean = false;
  public error_alert_message: string = "Everything is fine. 🐺";
  public snackbar_message: string = "Everything is fine. ☃";
  public snackbar_duration: number = 2000;

  private refreshPollerId: number | null = null;

  getStatusColor = getStatusColor;
  themeColors = themeColors;
  getThemeColor = getThemeColor;
  getThemedStatusColor = getThemedStatusColor;

  get persistQueryParams(): any {
    if (this.$route.query.access_token) {
      return this.$route.query;
    }
    return {};
  }

  get cssColorVars() {
    return cssColorVars();
  }

  // Use like:
  // :style="`background-color: ${paletteColor('yellow', '50')};`"
  get paletteColor(): any {
    return (color: string, shade: string | number) => {
      return palette[color][shade];
    };
  }

  get userId(): string | null {
    return this.$store.getters.userId;
  }

  get isJobOwner(): boolean {
    if (this.job) {
      return this.userId === this.job.owner;
    }
    return false;
  }

  get files(): LaxyFile[] {
    return this.$store.getters.currentJobFiles;
  }

  get fileTree(): TreeNode<LaxyFile> {
    if (!this.files) return EMPTY_TREE_ROOT;
    return fileListToTree(this.files || []);
  }

  get inputFiles(): LaxyFile[] | null {
    if (this.input_fileset_id) {
      const fsid = this.input_fileset_id;
      if (fsid && this.$store.state.filesets[fsid]) {
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
    if (this.output_fileset_id) {
      const fsid = this.output_fileset_id;
      if (fsid && this.$store.state.filesets[fsid]) {
        return this.$store.state.filesets[fsid].files;
      }
    }
    return null;
  }

  get outputFilesetTree(): TreeNode<LaxyFile> {
    if (!this.outputFiles) return EMPTY_TREE_ROOT;
    return fileListToTree(this.outputFiles || []);
  }

  get isAuthenticated() {
    return this.$store.getters.is_authenticated;
  }

  get bannerSharingLink(): LaxySharingLink | null {
    if (
      this.sharingLinks &&
      this.sharingLinks.length > 0 &&
      !this._linkIsExpired(this.sharingLinks[0])
    ) {
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

  async mounted() {
    await this.refresh(null);

    //if (this.job && !this.jobIsDone) {
    this.refreshPollerId = window.setInterval(() => {
      this.refresh(null);
    }, 10000); // ms
    //}
  }

  beforeDestroy() {
    if (this.refreshPollerId != null) clearInterval(this.refreshPollerId);
  }

  get jobIsDone() {
    return (
      this.job != null &&
      this.job.status !== "running" &&
      this.job.status !== "created"
    );
  }

  get jobIsRunning() {
    return this.job != null && this.job.status === "running";
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
        `${file.path}/${file.name}`
      );
    }
    return null;
  }

  hasFileTagged(tag: string): boolean {
    return this.filesByTag(tag).length > 0;
  }

  // Returns true if there are any files with 
  // at least one of the `tags`
  hasFilesWithTags(tags: Array<string>): boolean {
    for (let tag of tags) {
      if (this.filesByTag(tag).length > 0) {
        return true;
      }
    }
    return false;
  }

  filesByRegex(files: Array<LaxyFile> | null, patterns: Array<RegExp>): Array<LaxyFile> {
    if (files == null) {
      return [];
    }
    return filterByRegex(files, patterns);
  }

  get hasMultiQCReport(): boolean {
    return this.hasFileTagged("multiqc");
  }

  get hasDegustCounts(): boolean {
    return this.hasFileTagged("degust");
  }

  openDegustLink(fileId: string) {
    window.open(
      WebAPI.getExternalAppRedirectUrl("degust", fileId, this.access_token),
      "_blank"
    );
  }

  get genomeID(): string | null {
    return get(this.job, "params.params.genome", null);
  }

  // TODO: This may be better shifted to a dedicated JobParamsCard rather than including it as a row in
  // the generic JobStatusCard
  get genomeDescription(): string | null {
    const genome_id = this.genomeID;
    find(AVAILABLE_GENOMES, { id: genome_id });
    const genome = find(AVAILABLE_GENOMES, { id: genome_id });
    if (genome_id && genome) {
      let [organism, centre, build] = genome_id.split("/");
      organism = organism.replace("_", " ");
      return `${build} (${organism})`;
    }
    return null;
  }

  get externalGenomeDescription(): any | null {
    const fetch_files = get(this.job, "params.params.fetch_files", null);
    let fasta = head(
      filter(fetch_files, {
        type_tags: ["reference_genome", "genome_sequence"]
      })
    );
    let annotation = head(
      filter(fetch_files, {
        type_tags: ["reference_genome", "genome_annotation"]
      })
    );
    //console.dir(fasta);
    //console.dir(annotation);
    return {
      genome_sequence: fasta,
      genome_annotation: annotation
    };
  }

  _countsFileInfo(
    file: LaxyFile
  ): { strandedness: string; featureSet: string } {
    let data: { strandedness: string; featureSet: string } = {
      strandedness: "",
      featureSet: "Counts"
    };
    if (file.name.includes("NonStranded")) data.strandedness = "non-stranded";
    if (file.name.includes("Forward")) data.strandedness = "forward-stranded";
    if (file.name.includes("Reverse")) data.strandedness = "reverse-stranded";
    
    if (file.name.includes("proteinCoding")) data.featureSet = "Protein coding";
    if (file.name.includes("featureCounts")) {
      data.featureSet = "featureCounts file";
    } else if (file.name.includes("salmon")) {
      let salmon_run_type = file.path.endsWith('/star_salmon') ? "STAR → Salmon" : "Salmon";
      data.featureSet = `${salmon_run_type} counts`
    } else {
      data.featureSet = "Counts"
    }
    return data;
  }

  get strandBias(): number | null {
    return get(this.job, "metadata.results.strandedness.bias", null);
  }

  get rnasik_strandPredictionPrefix(): string | null {
    if (this.strandednessGuess == null) return null;
    if (this.strandednessGuess == "non-stranded") return "NonStranded";
    if (this.strandednessGuess == "forward-stranded") return "Forward";
    if (this.strandednessGuess == "reverse-stranded") return "Reverse";

    return null;
  }

  get strandednessGuess(): string | null {
    let strandedness = null;
    switch (true) {
      case (this.strandBias == null):
        return null;
      case (this.strandBias != null && this.strandBias >= 0.8):
        strandedness = "forward-stranded";
        break;
      case (this.strandBias != null && this.strandBias <= -0.8):
        strandedness = "reverse-stranded";
        break;
      default:
        strandedness = "non-stranded";
        break;
    }
    return strandedness;
  }

  get primaryCountsFiles(): LaxyFile[] {
    const outputFiles: LaxyFile[] = this.outputFiles || [];
    const degustFiles = this.filterByTag(outputFiles, ['degust']);

    // Helper function to check if a file is a specific type
    const isFileType = (file: LaxyFile, pathEnd: string, nameIncludes: string): boolean => {
        return file.path.endsWith(pathEnd) && file.name.includes(nameIncludes);
    };

    const checkers = [
        // Priority 1: RNAsik files
        (file: LaxyFile): boolean => {
            return !!this.rnasik_strandPredictionPrefix &&
                file.name.startsWith(this.rnasik_strandPredictionPrefix as string) &&
                file.name.includes('withNames');
        },
        // Priority 2: featureCounts counts file
        (file: LaxyFile): boolean => {
            return isFileType(file, '/featureCounts', 'counts.star_featureCounts.tsv');
        },
        // Priority 3: star_salmon counts file
        (file: LaxyFile): boolean => {
            return isFileType(file, '/star_salmon', 'salmon.merged.gene_counts.biotypes.tsv');
        },
        // Priority 4: salmon pseudo-mapping counts file
        (file: LaxyFile): boolean => {
            return isFileType(file, '/salmon', 'salmon.merged.gene_counts.biotypes.tsv');
        }
    ];

    // Check each rule in order, returning the first file that matches
    for (const checker of checkers) {
        const foundFile = degustFiles.find(checker);
        if (foundFile) {
            return [foundFile];
        }
    }

    return [];
  }

  get badInputFile(): number | null {
    return get(this.job, "metadata.error.bad_input_file", null);
  }

  get jobParamRows() {
    let rows = [];
    if (this.job) {
      const pipeline_version = get(
        this.job,
        "params.params.pipeline_version",
        null
      );
      if (pipeline_version != null) {
        rows.push([
          "Pipeline",
          `${this.job.params.pipeline} ${this.job.params.params.pipeline_version
          }`
        ]);
      }

      if (this.genomeID != null) {
        rows.push(["Reference genome ID", this.genomeID]);
      } else if (this.externalGenomeDescription != null) {
        rows.push([
          "Reference genome sequence",
          this.externalGenomeDescription?.genome_sequence?.location
        ]);
        rows.push([
          "Reference genome annotation",
          this.externalGenomeDescription?.genome_annotation?.location
        ]);
      }
    }
    return rows;
  }

  get access_token(): string | undefined {
    let token = this.$route.query.access_token;
    if (token != null) {
      return token.toString();
    }
    return undefined;
  }

  get tarballUrl(): string {
    let access_token = this.access_token;
    if (this.bannerSharingLink) {
      access_token = this.bannerSharingLink.token;
    }
    return WebAPI.downloadJobTarballUrl(this.jobId, access_token);
  }

  filesByTag(tag: string): LaxyFile[] {
    return filter(this.files, f => {
      if (f.type_tags == null) return false;
      return f.type_tags.includes(tag);
    });
  }

  async refresh(successMessage: string | null = "Updated") {
    try {
      this.refreshing = true;
      // const response = await WebAPI.getJob(this.jobId);
      // this.job = response.data as ComputeJob;

      this.getSharingLinks();

      let original_status = null;
      if (this.job != null) {
        original_status = `${this.job.status}`;
      }

      await this.$store.dispatch(FETCH_JOB, {
        job_id: this.jobId,
        access_token: this.access_token
      });
      // this.job = this.$store.state.currentViewedJob;
      const status_changed = this.job && this.job.status != original_status;

      let eventlog = null;
      if (this.showTab == "eventlog") {
        eventlog = this.$refs.eventlog as any;
      }
      if (this.showTab == "summary") {
        eventlog = this.$refs.eventlogSummary as any;
      }
      if (eventlog) await eventlog.refresh();

      // do web requests if filesets not yet populated
      if (status_changed && this.job) {
        this.input_fileset_id = this.job.input_fileset_id;
        this.output_fileset_id = this.job.output_fileset_id;
        const fetches = [];
        for (let fsid of [this.input_fileset_id, this.output_fileset_id]) {
          if (fsid) {
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
      if (successMessage) Snackbar.flashMessage(successMessage, 500);
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
      await this.refresh();
      this.refreshing = false;
      Snackbar.flashMessage("Job cancelled.");
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

  async cloneJob(id: string) {
    try {
      const response = await WebAPI.cloneJob(id);
      const pipelinerun_id = response.data.pipelinerun_id;
      const pipeline_name = response.data.pipeline;
      const samplecart_id = response.data.samplecart_id;

      if (samplecart_id != null) {
        const s_response = await WebAPI.getSampleCart(samplecart_id);
        const samplecart = s_response.data;
        let samples = new SampleCartItems();
        samples.id = samplecart.id;
        samples.items = samplecart.samples;
        samples.name = samplecart.name;
        this.$store.commit(SET_SAMPLES, samples as SampleCartItems);
      }

      const p_response = await WebAPI.getPipelineRun(pipelinerun_id);
      const pipelinerun = p_response.data;
      this.$store.commit(SET_PIPELINE_PARAMS, pipelinerun.params);
      this.$store.commit(SET_PIPELINE_DESCRIPTION, pipelinerun.description);

      if (
        this.$store.get("pipelineParams@user_genome.fasta_url") ||
        this.$store.get("pipelineParams@user_genome.annotation_url")
      ) {
        this.$store.set("use_custom_genome", true);
      }

      // TODO: make a prop on RNASeqSetup to allow a jump to second or last step immediately
      this.$router.push({ name: pipeline_name });
    } catch (error) {
      console.log(error);
    }
  }

  async updateSharingLink(job_id: string, expires_in: number | string) {
    try {
      await WebAPI.updateSharingLink(job_id, expires_in);
      this.getSharingLinks();
    } catch (error) {
      throw error;
    }
  }

  async onChangeLinkEvent(params: any) {
    await this.updateSharingLink(params.job_id, params.expires_in);
  }

  async getSharingLinks() {
    try {
      const resp = await WebAPI.getJobAccessToken(this.jobId);
      this.sharingLinks = [];
      const link = resp.data as LaxySharingLink;
      if (link) this.sharingLinks = [link];
    } catch (error) {
      console.log(error);
    }
  }

  async onDeleteSharingLinkEvent(link_id: string) {
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
        return ", never expires";
      } else {
        return "Never";
      }
    }
    const m = moment(expiry_time);
    let suffix = "from now";
    if (m.isBefore(Date.now())) {
      suffix = "ago";
    }
    let formatted = `${m.format("DD-MMM-YYYY (HH:mm UTCZ)")} (${m.fromNow(
      true
    )} ${suffix})`;
    if (add_sentence_words) {
      formatted = ` until ${formatted}`;
    }
    return formatted;
  }

  @Memoize((link: any) => link.id)
  _linkIsExpired(link: any) {
    return moment(link.expiry_time).isBefore(Date.now());
  }

  get jobExpiresDaysFromNow(): number {
    // const expiry_time = new Date(this.job.expiry_time);
    if (this.job && this.job.expiry_time) {
      const expiry_time = moment(this.job.expiry_time || undefined);
      const now = moment();
      return expiry_time.diff(now, "days") as number;
    }
    return Infinity;
  }

  get jobExpiresSoon(): boolean {
    return this.jobExpiresDaysFromNow <= 7;
  }

  openLinkInTab(url: string) {
    const access_token = this.access_token;
    if (access_token) {
      const urlObj = new URL(url, window.location.origin);
      urlObj.searchParams.set('access_token', access_token);
      url = urlObj.toString();
    }
    window.open(url);
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

  flashSnackBarEvent(params: any) {
    Snackbar.flashMessage(params.message, params.duration);
  }
}
</script>

<style scoped>
/* Fix alignment of boxes in right column */
#right-column {
  padding-top: 16px;
}

.shared-banner {
  background-color: var(--accent-light);
  width: 100%;
  height: 36px;
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
