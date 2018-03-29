<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-whiteframe style="padding: 32px;">
                <h3>Pipeline parameters</h3>
                <md-input-container>
                    <label for="genome">Reference genome</label>
                    <md-select name="genome" id="genome"
                               v-model="reference_genome">
                        <md-option v-for="genome in available_genomes"
                                   :key="genome.id"
                                   :value="genome.id">{{ genome.id }} ({{
                            genome.organism }})
                        </md-option>
                    </md-select>
                </md-input-container>
            </md-whiteframe>
            <md-whiteframe style="padding: 32px;">
                <h3>Sample conditions</h3>
                <sample-table :samples="samples"
                              :fields="['name', 'condition']"
                              :editable_fields="['condition']"
                              @selected="onSelect"></sample-table>
            </md-whiteframe>
            <md-layout>
                <md-button class="md-primary md-raised" @click="save">
                    Save
                </md-button>
                <md-button class="md-primary md-raised" @click="run">
                    Run the pipeline
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

    import {WebAPI} from "../web-api";

    import {DummySampleList as _dummySampleList} from "../test-data";
    import {DummyPipelineConfig as _dummyPipelineConfig} from "../test-data";

    @Component({props: {}, filters: {}})
    export default class PipelineParams extends Vue {
        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🏩";
        public snackbar_message: string = "Everything is fine. ௐ";
        public snackbar_duration: number = 2000;

        public pipelinerun_uuid: string | null = null;
        public sample_list_name: string = "";
        public samples: Array<Sample> = _dummySampleList;
        public sampleset_id: string = "3NNIIOt8skAuS1w2ZfgOq";
        public selectedSamples: Array<Sample> = [];

        public available_genomes: Array<ReferenceGenome> = [
            {id: "hg19", organism: "Human"},
            {id: "mm10", organism: "Mouse"},
        ];
        public reference_genome: string = this.available_genomes[0].id;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {

        }

        prepareData() {
            let data = {
                "sample_set": this.sampleset_id,
                "sample_metadata": {},
                "params": {
                    "genome": this.reference_genome,
                },
                "pipeline": "rnasik",
                "comment": "Just a test."
            };

            data.sample_metadata =
                _.keyBy(_.map(this.samples, s => _.pick(s, ["id", "condition"])),
                    "id");

            // data.sample_metadata = _.keyBy(this.samples, "id");

            return data;
        }

        async save() {
            // const data = _dummyPipelineConfig;

            const data = this.prepareData();
            console.log(data);
            try {
                this.submitting = true;
                let response = null;
                if (this.pipelinerun_uuid == null) {
                    response = await WebAPI.fetcher.post("/api/v1/pipelinerun/", data) as AxiosResponse;
                    this.pipelinerun_uuid = response.data.id;
                } else {
                    response = await WebAPI.fetcher.put(`/api/v1/pipelinerun/${this.pipelinerun_uuid}/`, data) as AxiosResponse;
                }
                this.submitting = false;
                this.flashSnackBarMessage("Saved !");
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
            }
        }

        async run() {
            try {
                await this.save();

                try {
                    this.submitting = true;
                    let response = null;
                    response = await WebAPI.fetcher.post(
                        `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`, {}) as AxiosResponse;
                    this.submitting = false;
                    this.flashSnackBarMessage("Saved !");
                } catch (error) {
                    console.log(error);
                    this.submitting = false;
                    this.error_alert_message = error.toString();
                    this.openDialog("error_dialog");
                }

            } catch (error) {

            }


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

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
        }

        populateSelectionList(sample_list: Array<Sample>) {
            console.log(sample_list);
            this.samples = sample_list;
        }
    };

</script>
