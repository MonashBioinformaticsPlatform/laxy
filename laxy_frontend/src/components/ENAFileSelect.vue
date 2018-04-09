<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-layout md-column>
                <form @submit.stop.prevent="search(accession_input)">
                    <md-input-container>
                        <label>Accession(s)
                            <span>
                                <md-icon style="font-size: 16px;">info</md-icon>
                                <md-tooltip md-direction="right">Multpile accessions should be comma or space separated
                                </md-tooltip>
                            </span>
                        </label>
                        <md-input v-model="accession_input"
                                  placeholder="PRJNA276493, SRR950078"></md-input>
                        <md-button class="md-icon-button"
                                   @click="search(accession_input)">
                            <md-icon type="submit">search</md-icon>
                        </md-button>
                    </md-input-container>
                </form>
            </md-layout>
            <md-layout md-gutter>
                <md-layout>
                    <md-layout v-if="samples != null">
                        <md-table @select="onSelect">
                            <md-table-header>
                                <md-table-row>
                                    <md-table-head
                                            v-for="field in show_sample_fields"
                                            :key="field">{{ field | deunderscore }}
                                    </md-table-head>
                                </md-table-row>
                            </md-table-header>
                            <md-table-body>
                                <md-table-row v-for="sample in samples"
                                              :key="sample.fastq_md5.join('-')"
                                              :md-item="sample"
                                              md-auto-select md-selection>
                                    <md-table-cell
                                            v-for="field in show_sample_fields"
                                            :key="field">
                                        <span v-if="field.includes('_accession')">
                                            <a :href="'https://www.ebi.ac.uk/ena/data/view/'+sample[field]"
                                               target="_blank">
                                              {{ sample[field] }}
                                            </a>
                                        </span>
                                        <span v-else-if="field === 'read_count'">
                                              {{ sample[field] | numeral_format('0 a') }}
                                        </span>
                                        <span v-else>
                                              {{ sample[field] }}
                                        </span>
                                    </md-table-cell>
                                    <!-- FASTQ links
                                    <md-table-cell v-for="url in sample.fastq_ftp" :key="url">
                                        <a :href="url"><md-icon>link</md-icon>&nbsp;FASTQ</a>
                                    </md-table-cell>
                                    -->
                                </md-table-row>
                            </md-table-body>
                        </md-table>
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
            <md-layout md-gutter>
                <md-button @click="addToCart"
                           :disabled="submitting || samples.length === 0"
                           class="md-raised">Add to cart
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

    import {ADD_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    import {ENADummySampleList as _dummysampleList} from "../test-data";

    interface DbAccession {
        accession: string;
    }

    @Component({props: {}, filters: {}})
    export default class ENAFileSelect extends Vue {
        public samples: Array<ENASample> = [];  // = _dummysampleList;
        public selectedSamples: Array<ENASample> = [];

        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        // TODO: Show only run_accession and sample_accession, maybe run_alias
        //       in table, show all other details in a hover card to the right.
        public show_sample_fields = [
            "run_alias",
            "run_accession",
            "experiment_accession",
            //"study_accession",
            "sample_accession",
            //"instrument_platform",
            //"instrument_model",
            "library_strategy",
            "library_source",
            //"library_layout",
            "library_selection",
            //"library_name",
            //"study_alias",
            //"experiment_alias",
            //"sample_alias",
            //"run_alias",
            //"read_count",
            //"base_count",
            //"center_name",
            //"broker_name",
            //"fastq_ftp",
            //"fastq_md5",
            //"fastq_bytes"]
        ];

        public ena_ids: DbAccession[] = [{accession: ""} as DbAccession];

        // public accession_input: string = "PRJNA319904"; // ~6000 files !
        // public accession_input: string = "PRJEB3366"; // many !
        public accession_input: string = "PRJNA276493, SRR950078";

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine.";

        // for lodash in templates
        get _() {
            return _;
        }

        created() {

        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<ENASample>;
            // console.log(this.selectedSamples);
        }

        remove(rows: ENASample[]) {
            for (const row of rows) {
                const i = this.samples.indexOf(row);
                this.samples.splice(i, 1);
            }
        }

        addToCart() {
            // TODO: this.selectedSamples needs to be transformed from an array
            // of ENASample[] to an array of Sample[], mapping 'fastq_ftp' to 'files',
            // 'sample_accession' to 'name'.
            // Might be also a good time to refactor 'condition' to 'metadata'
            // and shove some of the ENA metadata in there (eg the
            // run/experiment/study/sample_accession)

            console.log(this.selectedSamples);
            const cart_samples = [];
            for (let ena of this.selectedSamples) {
                cart_samples.push({
                    name: ena.sample_accession,
                    files: ena.fastq_ftp,
                    metadata: {condition: '', ena: ena},
                });
            }
            this.$store.commit(ADD_SAMPLES, cart_samples);
            let count = this.selectedSamples.length;
            this.flashSnackBarMessage(`Added ${count} ${pluralize("sample", count)} to cart.`);

            this.remove(this.selectedSamples);
            this.selectedSamples = [];
        }

        async search(accessions: string) {
            this.samples = [];
            this.selectedSamples = [];

            // split on commas and spaces, make items unique, rejoin as comma separated list
            let accession_list = _.uniq(_.compact(accessions.trim().split(/[\s,]+/))).join(",");
            const url = `/api/v1/ena/fastqs?accessions=${accession_list}`;
            // console.log(url);
            const fetcher = WebAPI.fetcher;

            try {
                this.submitting = true;
                const response = await fetcher.get(url) as AxiosResponse;
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
            this.samples = [];
            for (let key in data) {
                this.samples.push(data[key] as ENASample);
            }
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
