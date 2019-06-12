<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-dialog md-open-from="#add_menu_button"
                   md-close-to="#add_menu_button" ref="csv_file_select_dialog">
            <md-dialog-title>Select a file</md-dialog-title>

            <md-dialog-content>Choose a CSV file to upload.
                <md-input-container>
                    <label>From CSV</label>
                    <md-file v-model="csv_file" :disabled="submitting"
                             @selected="submitCSV"></md-file>
                </md-input-container>

                Example format (Sample name, R1, R2):
                <pre>
                        SampleA,ftp://bla_lane1_R1.fastq.gz,ftp://bla_lane1_R2.fastq.gz
                        SampleA,ftp://bla_lane2_R1.fastq.gz,ftp://bla_lane2_R2.fastq.gz
                        SampleB,ftp://bla2_R1_001.fastq.gz,ftp://bla2_R2_001.fastq.gz
                               ,ftp://bla2_R1_002.fastq.gz,ftp://bla2_R2_002.fastq.gz
                        SampleC,ftp://foo2_lane4_1.fastq.gz,ftp://foo2_lane4_2.fastq.gz
                        SampleC,ftp://foo2_lane5_1.fastq.gz,ftp://foo2_lane5_2.fastq.gz
                </pre>
                Each row represents a biological replicate (sample + condition +
                biological replicate).
                Rows with identical sample names are considered technical
                replicates and may be merged for
                analysis.
                For single-end data, omit the R2 column.
            </md-dialog-content>

            <md-dialog-actions>
                <md-button class="md-primary"
                           @click="closeDialog('csv_file_select_dialog')">Close
                </md-button>
            </md-dialog-actions>
        </md-dialog>

        <md-layout md-column>
            <md-layout md-gutter>
                <md-layout>
                    <md-layout v-if="samples != null">
                        <md-input-container v-if="editableSetName">
                            <label>Sample list name</label>
                            <md-input v-model="_samples.name"
                                      placeholder="My sample list"></md-input>
                        </md-input-container>
                        <div v-else>
                            <h4>{{ samples.name }}</h4>
                        </div>

                        <sample-table :samples="samples"
                                      :fields="fields"
                                      :editable-fields="editableFields"
                                      :selectable="selectable"
                                      @selected="onSelect"></sample-table>

                        <md-toolbar v-if="showToolbar"
                                    class="md-dense" :disabled="submitting"
                                    style="width: 100%;">
                            <md-menu v-if="showAddMenu" md-size="5">
                                <md-button id="add_menu_button"
                                           class="md-icon-button"
                                           md-menu-trigger>
                                    <md-icon>add</md-icon>
                                    <md-tooltip md-direction="top">Add samples
                                    </md-tooltip>
                                </md-button>

                                <md-menu-content>
                                    <md-menu-item @click="routeTo('enaselect', {showButtons: true})">
                                        From public ENA data
                                    </md-menu-item>
                                    <md-menu-item>From my uploaded files
                                    </md-menu-item>
                                    <md-menu-item>By URL</md-menu-item>
                                    <md-menu-item
                                            @click="openDialog('csv_file_select_dialog')">
                                        From CSV / Excel
                                    </md-menu-item>
                                </md-menu-content>
                            </md-menu>
                            <md-button class="md-icon-button"
                                       @click="removeSelected">
                                <md-icon>delete</md-icon>
                                <md-tooltip md-direction="top">Remove selected
                                </md-tooltip>
                            </md-button>
                            <span style="flex: 1;"></span>
                            <md-button class="md-icon-button"
                                       @click="save"
                                       :disabled="submitting">
                                <md-icon>save</md-icon>
                                <md-tooltip md-direction="top">Save</md-tooltip>
                            </md-button>
                        </md-toolbar>
                        <md-layout v-if="submitting">
                            <md-progress md-indeterminate></md-progress>
                        </md-layout>
                        <hr>
                    </md-layout>
                    <md-layout v-else>
                        .. no samples ..
                    </md-layout>
                </md-layout>
            </md-layout>
            <md-layout v-if="showButtons" md-gutter>
                <md-button @click="saveAndContinue"
                           :disabled="submitting"
                           class="md-raised">Save & continue
                </md-button>
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

    import {Sample, SampleCartItems} from "../model";
    import {SET_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    import {DummySampleList as _dummySampleList} from "../test-data";
    import {Snackbar} from "../snackbar";
    import CSVSampleListUpload from "./CSVSampleListUpload/CSVSampleListUpload.vue";

    @Component({
        props: {},
        filters: {},
        beforeRouteLeave(to: any, from: any, next: any) {
            (this as any).beforeRouteLeave(to, from, next);
        }
    })
    export default class SampleCart extends Vue {
        _DEBUG: boolean = false;

        @Prop({default: true, type: Boolean})
        public showButtons: boolean;

        @Prop({default: true, type: Boolean})
        public showToolbar: boolean;

        @Prop({default: true, type: Boolean})
        public showAddMenu: boolean;

        @Prop({default: true, type: Boolean})
        public editableSetName: boolean;

        @Prop({default: true, type: Boolean})
        public selectable: boolean;

        // = ["name", "metadata.condition", "R1", "R2"];
        @Prop({default: () => ['name', 'R1', 'R2'], type: Array})
        public fields: Array<string>;

        // = ["name", "metadata.condition"];
        @Prop({default: () => [], type: Array})
        public editableFields: Array<string>;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;
        public csv_file: string = "";

        // public sampleset_uuid: string | null = null;

        //public sample_list_name: string = "";

        // For Vuex, we make 'samples' a readonly computed attribute that deep clones
        // the object held by the vuex store. 'samples' in the vuex store is
        // only modified by wholesale replacement upon 'Save' or navigation
        // away from the SampleCart route.
        // public samples: Sample[];

        public selectedSamples: Sample[] = [];

        // for lodash in templates
        get _() {
            return _;
        }

        async beforeCreate() {
            // Example data for debug only
            if (this._DEBUG) {
                if (this.$store.getters.sample_cart_count === null ||
                    this.$store.getters.sample_cart_count === 0) {
                    const s: SampleCartItems = _.cloneDeep(_dummySampleList);
                    this.$store.commit(SET_SAMPLES, s);
                }
            }
        }

        created() {
            this._samples = _.cloneDeep(this.$store.state.samples);
        }

        public _samples: SampleCartItems;
        get samples(): SampleCartItems {
            this._samples = _.cloneDeep(this.$store.state.samples);
            return this._samples;
        }

        set samples(sampleset: SampleCartItems) {
            this._samples = sampleset;
            this.$store.commit(SET_SAMPLES, sampleset as SampleCartItems);
        }

        async submit() {
            try {
                this.submitting = true;
                await this.$store.dispatch(SET_SAMPLES, this._samples);
                this.submitting = false;
                Snackbar.flashMessage("Saved !");
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                throw error;
            }
        }

        async submitCSV(filelist: FileList) {
            console.log(filelist);
            const file: File = filelist[0];
            const data = new FormData(); // automatically uses 'content-type': 'multipart/form-data' in axios ?
            data.set("name", this.samples.name);
            data.set("file", file);
            //const headers = {headers: {'content-type': 'multipart/form-data'}};
            try {
                this.closeDialog("csv_file_select_dialog");
                this.submitting = true;
                const response = await WebAPI.fetcher.post("/api/v1/sampleset/", data) as AxiosResponse;
                // TODO: CSV upload doesn't append/merge, it aways creates a new SampleSet.
                //       Implement backend PATCH method so we can append/merge an uploaded CSV
                //       (or parse and merge CSV clientside - probably a bad idea since we really
                //        want to be able to validate CSV serverside before allowing it to be accepted)
                // let response = null;
                // if (this.samples.id == null) {
                //     const response = await WebAPI.fetcher.post("/api/v1/sampleset/", data) as AxiosResponse;
                //     this._samples.id = response.data.id;
                // } else {
                //     const response = await WebAPI.fetcher.patch(`/api/v1/sampleset/{this.samples.id}`, data) as AxiosResponse;
                // }
                this.submitting = false;
                Snackbar.flashMessage("Saved !");
                // coerce JSON into a list of proper Sample objects, ensuring all properties are present
                const _samples: Sample[] = _.map(response.data.samples, (s) => {
                    return new Sample(s)
                });
                this.populateSelectionList(_samples);

                // TODO: Save and highlight validation issues (eg identical sample names)
                //       Route to next step

            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.closeDialog("csv_file_select_dialog");
                this.openDialog("error_dialog");
                throw error;
            }
        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
        }

        removeSelected() {
            // const cartTable: any = this.$refs['cartTable'];
            for (const row of this.selectedSamples) {
                const i = this.samples.items.indexOf(row);
                this.samples.items.splice(i, 1);
            }
            this.$store.commit(SET_SAMPLES, this.samples);
        }

        save() {
            this.submit();
        }

        async saveAndContinue() {
            try {
                await this.submit();
                // TODO: We should fire an event here to let the parent component do something
                //  (eg catch event in index.ts, do toggleSidenav('rightSidenav') )
                // this.routeTo("rnaseq");
            } catch (error) {
                throw error;
            }
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }

        populateSelectionList(sample_list: Array<Sample>) {
            console.log(sample_list);
            this._samples.items = sample_list;
            this.$store.commit(SET_SAMPLES, this._samples);
        }

        routeTo(name: string, params: any = {}) {
            this.$router.push({name: name, params: params});
        }

        // This ensures changes to sample table are committed to the vuex store
        // prior to navigating away. Defined here and wrapped on the Component
        // decorator so `this` works correctly.
        // https://router.vuejs.org/en/advanced/navigation-guards.html
        beforeRouteLeave(to: any, from: any, next: any) {
            // console.log([to, from, next]);
            this.$store.commit(SET_SAMPLES, this._samples);
            next();
        }
    };

</script>
