<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-whiteframe style="padding: 32px;">
                <h2>RNAsik</h2>
                <h3>Pipeline parameters</h3>
                <md-input-container>
                    <label>Description</label>
                    <md-input v-model="description" placeholder="Description of pipeline run ..."></md-input>
                </md-input-container>
                <md-input-container>
                    <label for="genome">Reference genome</label>
                    <md-select name="genome" id="genome"
                               v-model="reference_genome">
                        <md-option v-for="genome in available_genomes"
                                   :key="genome.id"
                                   :value="genome.id">
                            {{ get_genome_description(genome) }}
                        </md-option>
                    </md-select>
                </md-input-container>
            </md-whiteframe>

            <md-whiteframe style="padding: 32px;">
                <h3>Sample summary</h3>
                <sample-cart :samples="samples"
                             :fields="['name', 'metadata.condition', 'R1', 'R2']"
                             :show-toolbar="false"
                             :show-add-menu="false"
                             :show-buttons="false"
                             :editable-set-name="false"
                             :selectable="false"
                             @selected="onSelect"></sample-cart>
            </md-whiteframe>
            <md-layout v-if="showButtons">
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
    import cloneDeep from "lodash-es/cloneDeep";

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
        SET_SAMPLES,
        SET_PIPELINE_PARAMS,
        SET_PIPELINE_DESCRIPTION
    } from "../store";

    import {Sample, SampleSet} from "../model";
    import {WebAPI} from "../web-api";

    import {DummySampleList as _dummySampleList} from "../test-data";
    import {DummyPipelineConfig as _dummyPipelineConfig} from "../test-data";

    @Component({
        components: {},
        props: {},
        filters: {},
        beforeRouteLeave(to: any, from: any, next: any) {
            (this as any).beforeRouteLeave(to, from, next);
        }
    })
    export default class PipelineParams extends Vue {

        @Prop({default: true, type: Boolean})
        public showButtons: boolean;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🏩";
        public snackbar_message: string = "Everything is fine. ௐ";
        public snackbar_duration: number = 2000;

        public pipelinerun_uuid: string | null = null;
        // public samples: SampleSet = _dummySampleList;
        // public sampleset_id: string = "3NNIIOt8skAuS1w2ZfgOq";
        public selectedSamples: Array<Sample> = [];

        public available_genomes: Array<ReferenceGenome> = [
            {id: "Homo_sapiens/Ensembl/GRCh37", organism: "Human"},
            {id: "Homo_sapiens/UCSC/hg19", organism: "Human"},
            {id: "Homo_sapiens/NCBI/build37.2", organism: "Human"},
            {id: "Mus_musculus/Ensembl/GRCm38", organism: "Mouse"},
            {id: "Mus_musculus/UCSC/mm10", organism: "Mouse"},
            {id: "Mus_musculus/NCBI/GRCm38", organism: "Mouse"},
            {id: "Saccharomyces_cerevisiae/Ensembl/R64-1-1", organism: "Saccharomyces cerevisiae"},
            // {id: "Saccharomyces_cerevisiae/UCSC/sacCer3", organism: "Saccharomyces cerevisiae"},
            // {id: "Saccharomyces_cerevisiae/NCBI/build3.1", organism: "Saccharomyces cerevisiae"},
            {id: "Caenorhabditis_elegans/Ensembl/WBcel235", organism: "Caenorhabditis elegans"},
            {id: "Caenorhabditis_elegans/UCSC/ce10", organism: "Caenorhabditis elegans"},
            {id: "Caenorhabditis_elegans/NCBI/WS195", organism: "Caenorhabditis elegans"},
        ];
        // public reference_genome: string = this.available_genomes[0].id;
        // public description: string = '';

        public _samples: SampleSet;
        get samples(): SampleSet {
            this._samples = cloneDeep(this.$store.state.samples);
            return this._samples;
        }

        get description() {
            return this.$store.getters.pipelineParams.description;
        }

        set description(txt: string) {
            this.$store.commit(SET_PIPELINE_PARAMS, {
                description: txt,
                reference_genome: this.reference_genome,
            });
        }

        get reference_genome() {
            return this.$store.getters.pipelineParams.reference_genome;
        }

        set reference_genome(id: string) {
            this.$store.commit(SET_PIPELINE_PARAMS, {
                description: this.description,
                reference_genome: id,
            });
        }

        get_genome_description(reference: ReferenceGenome): string {
            const [org, centre, build] = reference.id.split('/');
            return `${build} [${centre}] (${reference.organism})`;
        }

        created() {
            this._samples = cloneDeep(this.$store.state.samples);
        }

        prepareData() {
            let data = {
                "sample_set": this.$store.state.samples.id,
                "params": {
                    "genome": this.reference_genome,
                },
                "pipeline": "rnasik",
                "description": this.description,
            };
            return data;
        }

        async save() {
            try {
                this.submitting = true;
                await this.$store.dispatch(SET_SAMPLES, this._samples);

                const data = this.prepareData();
                console.log(data);

                if (this.pipelinerun_uuid == null) {
                    const response = await WebAPI.fetcher.post("/api/v1/pipelinerun/", data) as AxiosResponse;
                    this.pipelinerun_uuid = response.data.id;
                } else {
                    await WebAPI.fetcher.put(`/api/v1/pipelinerun/${this.pipelinerun_uuid}/`, data) as AxiosResponse;
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
                console.error(error);
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

        beforeRouteLeave(to: any, from: any, next: any) {
            // console.log([to, from, next]);
            this.$store.commit(SET_SAMPLES, this._samples);
            next();
        }
    };

</script>
