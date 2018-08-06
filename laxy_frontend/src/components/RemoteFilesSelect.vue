<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-layout>
                <md-whiteframe md-elevation="5" style="padding: 16px; min-height: 100%; width: 100%;">
                    <div>Provide a URL to a page where your data can be downloaded
                    </div>
                </md-whiteframe>
            </md-layout>
            <md-layout md-column>
                <form @submit.stop.prevent="listLinks(url)">
                    <md-input-container>
                        <label>URL
                            <span>
                                <md-icon style="font-size: 16px;">info</md-icon>
                                <md-tooltip md-direction="right">The page must contain links to your files
                                </md-tooltip>
                            </span>
                        </label>
                        <md-input v-model="url"
                                  placeholder="https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/">
                        </md-input>
                        <md-button class="md-icon-button"
                                   @click="listLinks(url)">
                            <md-icon type="submit">search</md-icon>
                        </md-button>
                    </md-input-container>
                </form>
            </md-layout>
            <md-layout v-if="submitting">
                <md-progress md-indeterminate></md-progress>
            </md-layout>
            <md-layout md-gutter>
                <md-layout v-if="!hasResults"
                           md-flex-large="75" md-flex-small="100">
                    <!-- no results -->
                </md-layout>
                <md-layout v-else
                           md-flex-large="75" md-flex-small="100">
                    <nested-file-list
                            v-if="files && files.length > 0"
                            id="remote-files-list"
                            class="fill-width"
                            ref="remote-files-list"
                            title="Links"
                            root-path-name=""
                            :fileList="files"
                            :hide-search="false"
                            @refresh-error="showErrorDialog">
                    </nested-file-list>
                </md-layout>
            </md-layout>
        </md-layout>
        <md-layout v-if="showButtons" md-gutter>
            <md-button @click="addToCart"
                       :disabled="submitting || samples.length === 0"
                       class="md-raised">Add to cart
            </md-button>
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

    import * as pluralize from "pluralize";
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

    import FileList from "./FileList";
    import NestedFileList from "./NestedFileList";
    import {LaxyFile, Sample} from "../model";
    import {ADD_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    import {ENADummySampleList as _dummysampleList} from "../test-data";

    interface DbAccession {
        accession: string;
    }

    @Component({
        components: {FileList, NestedFileList},
        props: {showButtons: Boolean},
        filters: {}
    })
    export default class RemoteFileSelect extends Vue {
        public showButtons: boolean | undefined;

        public url: string = "";
        public files: Array<LaxyFile> = [];
        public selectedFiles: Array<LaxyFile> = [];

        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine.";

        // for lodash in templates
        get _() {
            return _;
        }

        created() {

        }

        get hasResults() {
            return !(this.files == null || this.files.length === 0);
        }

        onSelect(rows: any) {
            this.selectedFiles = rows as Array<LaxyFile>;
            // console.log(this.selectedSamples);
        }

        remove(rows: LaxyFile[]) {
            for (const row of rows) {
                const i = this.files.indexOf(row);
                this.files.splice(i, 1);
            }
        }

        addToCart() {
            // TODO: this.selectedSamples needs to be transformed from an array
            // of ENASample[] to an array of Sample[], mapping 'fastq_ftp' to 'files',
            // 'sample_accession' to 'name'.
            // Might be also a good time to refactor 'condition' to 'metadata'
            // and shove some of the ENA metadata in there (eg the
            // run/experiment/study/sample_accession)

            console.log(this.selectedFiles);
            const cart_samples: Sample[] = [];
            for (let f of this.selectedFiles) {
                cart_samples.push({
                    name: f.name,
                    files: [f],
                    metadata: {condition: ""},
                } as Sample);
            }
            this.$store.commit(ADD_SAMPLES, cart_samples);
            let count = this.selectedFiles.length;
            this.flashSnackBarMessage(`Added ${count} ${pluralize("sample", count)} to cart.`);

            this.remove(this.selectedFiles);
            this.selectedFiles = [];
        }

        // rowHover(row: any) {
        //     this.hoveredSampleDetails = row;
        //     // console.log(row);
        // }

        async listLinks(url: string) {
            this.files = [];
            this.selectedFiles = [];

            try {
                this.submitting = true;
                const response = await WebAPI.remoteFilesList(url);
                this.submitting = false;
                // if (response.data.status === "error") {
                //     this.error_alert_message = `${response.status} ${response.statusText}`;
                //     this.openDialog("error_dialog");
                // } else {
                this.populateSelectionList(response.data);
                //}
                // console.log(response);
            } catch (error) {
                console.log(error);
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                this.submitting = false;
            }
        }

        populateSelectionList(data: any) {
            // console.log(data);
            this.files = [];
            // for (let d of data['directories']) {
            //     this.files.push(d as LaxyFile);
            // }
            for (let f of data['files']) {
                this.files.push(f as LaxyFile);
            }
        }

        showErrorDialog(message: string) {
            this.error_alert_message = message;
            this.openDialog("error_dialog");
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        flashSnackBarMessage(msg: string, duration: number = 2000) {
            this.snackbar_message = msg;
            this.snackbar_duration = duration;
            (this.$refs.snackbar as any).open();
        }
    };

</script>

<style lang="css" scoped>

</style>
