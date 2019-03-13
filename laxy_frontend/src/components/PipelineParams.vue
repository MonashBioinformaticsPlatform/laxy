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
                    <label for="genome_organism">Species</label>
                    <md-select name="genome_organism"
                               id="genome_organism"
                               :required="true"
                               v-model="selected_genome_organism"
                               @change="onOrganismChange">
                        <md-option v-for="organism in genome_organism_list"
                                   :key="organism"
                                   :value="organism">
                            {{ organism }}
                        </md-option>
                    </md-select>
                </md-input-container>
                <md-input-container>
                    <label for="genome">Reference genome</label>
                    <md-select name="genome"
                               id="genome"
                               :required="true"
                               v-model="reference_genome">
                        <md-option v-for="genome in genomes_for_organism(selected_genome_organism)"
                                   :key="genome.id"
                                   :value="genome.id">
                            {{ get_genome_description(genome) }}
                        </md-option>
                    </md-select>
                </md-input-container>
                <md-switch v-model="show_advanced" id="advanced-toggle" name="advanced-toggle" class="md-primary">
                    Show advanced options
                </md-switch>
                <transition name="fade">
                    <md-layout v-if="show_advanced">
                        <md-input-container v-if="show_advanced">
                            <label for="genome">Pipeline version</label>
                            <md-select name="pipeline_version"
                                       id="pipeline_version"
                                       v-model="pipeline_version">
                                <md-option v-for="version in pipeline_versions"
                                           :key="version"
                                           :value="version">
                                    {{ version }}
                                </md-option>
                            </md-select>
                        </md-input-container>
                    </md-layout>
                </transition>
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
    import get from "lodash-es/get";
    import find from "lodash-es/find";
    import map from "lodash-es/map";
    import {Memoize} from "lodash-decorators";

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
        SET_PIPELINE_DESCRIPTION, SET_PIPELINE_PARAMS_VALID, CLEAR_SAMPLE_CART, SET_PIPELINE_GENOME
    } from "../store";

    import {Sample, SampleCartItems} from "../model";
    import {WebAPI} from "../web-api";

    import AVAILABLE_GENOMES from "../config/genomics/genomes";

    import {DummySampleList as _dummySampleList} from "../test-data";
    import {DummyPipelineConfig as _dummyPipelineConfig} from "../test-data";
    import {Snackbar} from "../snackbar";

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
        public show_advanced = false;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🏩";
        public snackbar_message: string = "Everything is fine. ௐ";
        public snackbar_duration: number = 2000;

        public pipelinerun_uuid: string | null = null;
        // public samples: SampleSet = _dummySampleList;
        // public sampleset_id: string = "3NNIIOt8skAuS1w2ZfgOq";
        public selectedSamples: Array<Sample> = [];

        public available_genomes: Array<ReferenceGenome> = AVAILABLE_GENOMES;

        public reference_genome_valid: boolean = true;

        /* we keep a component local _selected_genome_organism when *setting*, but always
           pull the value from the Vuex store (since the org/centre/release genome identifier
           determines the current _selected_genome_organism, and pipelineParams.genome in the
           store may be set from other places [eg automatically via the ENA search form]).
         */
        _selected_genome_organism: string = 'Homo sapiens';
        get selected_genome_organism(): string {
            return get(find(AVAILABLE_GENOMES,
                {'id': this.$store.state.pipelineParams.genome}), 'organism', 'Homo sapiens');
        }

        set selected_genome_organism(organism: string) {
            this._selected_genome_organism = organism;
        }

        public pipeline_versions = ['1.5.3', '1.5.2'];

        public _samples: SampleCartItems;
        get samples(): SampleCartItems {
            this._samples = cloneDeep(this.$store.state.samples);
            return this._samples;
        }

        get description() {
            return this.$store.getters.pipelineParams.description;
        }

        set description(txt: string) {
            let state = Object.assign({}, this.$store.state.pipelineParams);
            state.description = txt;
            this.$store.commit(SET_PIPELINE_PARAMS, state);
        }

        get reference_genome() {
            return this.$store.getters.pipelineParams.genome;
        }

        set reference_genome(id: string) {
            // let state = Object.assign({}, this.$store.state.pipelineParams);
            // state.genome = id;
            this.$store.commit(SET_PIPELINE_GENOME, id);
            this.validatePipelineParams();
        }

        get pipeline_version() {
            return this.$store.getters.pipelineParams.pipeline_version;
        }

        set pipeline_version(version: string) {
            let state = Object.assign({}, this.$store.state.pipelineParams);
            state.pipeline_version = version;
            this.$store.commit(SET_PIPELINE_PARAMS, state);
        }

        get genome_organism_list(): string[] {
            let organisms = new Set();
            for (let g of this.available_genomes) {
                organisms.add(g.organism);
            }
            return Array.from(organisms.values());
        }

        @Memoize
        genomes_for_organism(organism: string): ReferenceGenome[] {
            const genomes: ReferenceGenome[] = [];
            for (let g of this.available_genomes) {
                if (g.organism === organism) {
                    genomes.push(g);
                }
            }
            return genomes;
        }

        get_genome_description(reference: ReferenceGenome): string {
            const [org, centre, build] = reference.id.split('/');
            // return `${build} [${centre}] (${reference.organism})`;
            let desc = `${build} [${centre}]`;
            if (reference.recommended) {
                desc = `${desc} (recommended)`
            }
            return desc;
        }

        onOrganismChange(e: any) {
            this.reference_genome = this.genomes_for_organism(this.selected_genome_organism)[0].id;
        }

        created() {
            this._samples = cloneDeep(this.$store.state.samples);
        }

        prepareData() {
            let data = {
                "sample_set": this.$store.state.samples.id,
                "params": this.$store.getters.pipelineParams,
                "pipeline": "rnasik",
                "description": this.description,
            };
            return data;
        }

        validatePipelineParams() {
            let is_valid = false;
            if (map(this.available_genomes, 'id').includes(this.reference_genome)) {
                is_valid = true;
            }
            this.$store.commit(SET_PIPELINE_PARAMS_VALID, is_valid);

            return is_valid;
        }

        async save() {
            try {
                this.submitting = true;
                await this.$store.dispatch(SET_SAMPLES, this._samples);

                const data = this.prepareData();
                // console.log(data);

                if (this.pipelinerun_uuid == null) {
                    const response = await WebAPI.fetcher.post("/api/v1/pipelinerun/", data) as AxiosResponse;
                    this.pipelinerun_uuid = response.data.id;
                } else {
                    await WebAPI.fetcher.put(`/api/v1/pipelinerun/${this.pipelinerun_uuid}/`, data) as AxiosResponse;
                }
                this.submitting = false;
                Snackbar.flashMessage("Saved !");
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

                if (!this.validatePipelineParams()) {
                    Snackbar.flashMessage("Please select a reference genome.");
                    return;
                }

                try {
                    this.submitting = true;
                    let response = null;
                    response = await WebAPI.fetcher.post(
                        `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`, {}) as AxiosResponse;
                    this.submitting = false;
                    Snackbar.flashMessage("Saved !");
                    await this.clearCart();
                    return response;
                } catch (error) {
                    console.log(error);
                    this.submitting = false;
                    this.error_alert_message = error.toString();
                    this.openDialog("error_dialog");
                }

            } catch (error) {
                console.error(error);
            }
            return null;
        }

        async clearCart() {
            await this.$store.dispatch(CLEAR_SAMPLE_CART);
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
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
