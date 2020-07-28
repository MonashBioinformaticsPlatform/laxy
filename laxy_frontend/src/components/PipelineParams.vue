<template>
  <div>
    <md-dialog-alert
      :md-content-html="error_alert_message"
      :md-content="error_alert_message"
      ref="error_dialog"
    ></md-dialog-alert>
    <banner-notice
      v-if="!isValid_samples_added"
      type="error"
      :show-close-button="false"
    >Please add some samples before submitting your job.</banner-notice>
    <banner-notice v-if="!isValid_duplicate_samples" type="error" :show-close-button="false">
      Input sample files contain duplicates (based on URL/location).
      <br />Please remove duplicates before continuing.
    </banner-notice>
    <banner-notice
      v-if="!isValid_mixed_single_paired_check"
      type="error"
      :show-close-button="false"
    >
      Mixing single-end and paired-end samples is not currently supported.
      <br />Please remove either the single-end or the paired-end samples to continue.
    </banner-notice>
    <banner-notice
      v-if="!isValid_reference_genome"
      type="error"
      :show-close-button="false"
    >Selected reference genome is invalid.</banner-notice>
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
          <md-select
            name="genome_organism"
            id="genome_organism"
            :required="true"
            v-model="selected_genome_organism"
            @change="onOrganismChange"
          >
            <md-option
              v-for="organism in genome_organism_list"
              :key="organism"
              :value="organism"
            >{{ organism }}</md-option>
          </md-select>
        </md-input-container>
        <md-input-container>
          <label for="genome">Reference genome</label>
          <md-select name="genome" id="genome" :required="true" v-model="reference_genome">
            <md-option
              v-for="genome in genomes_for_organism(selected_genome_organism)"
              :key="genome.id"
              :value="genome.id"
            >{{ get_genome_description(genome) }}</md-option>
          </md-select>
        </md-input-container>
        <md-switch
          v-model="show_advanced"
          id="advanced-toggle"
          name="advanced-toggle"
          class="md-primary"
        >Show advanced options</md-switch>
        <transition name="fade">
          <md-layout v-if="show_advanced">
            <md-input-container>
              <label for="pipeline_version">Pipeline version</label>
              <md-select name="pipeline_version" id="pipeline_version" v-model="pipeline_version">
                <md-option
                  v-for="version in pipeline_versions"
                  :key="version"
                  :value="version"
                >{{ version }}</md-option>
              </md-select>
            </md-input-container>
            <md-input-container>
              <label for="pipeline_aligner">Aligner</label>
              <md-select name="pipeline_aligner" id="pipeline_aligner" v-model="pipeline_aligner">
                <md-option
                  v-for="aligner in pipeline_aligners"
                  :key="aligner.text"
                  :value="aligner.value"
                >{{ aligner.text }}</md-option>
              </md-select>
            </md-input-container>
          </md-layout>
        </transition>
      </md-whiteframe>

      <md-whiteframe style="padding: 32px;">
        <h3>Sample summary</h3>
        <sample-cart
          v-if="samples.items.length > 0"
          :samples="samples"
          :fields="['name', 'metadata.condition', 'R1', 'R2']"
          :show-toolbar="false"
          :show-add-menu="false"
          :show-buttons="false"
          :editable-set-name="false"
          :selectable="false"
          @selected="onSelect"
        ></sample-cart>
        <div v-if="samples.items.length === 0">No samples in cart.</div>
      </md-whiteframe>
      <md-layout v-if="showButtons">
        <md-button class="md-primary md-raised" @click="save">Save</md-button>
        <md-button
          :disabled="isValid_params"
          class="md-primary md-raised"
          @click="run"
        >Run the pipeline</md-button>
      </md-layout>
    </md-layout>

    <md-snackbar md-position="bottom center" ref="snackbar" :md-duration="snackbar_duration">
      <span>{{ snackbar_message }}</span>
      <md-button class="md-accent" @click="$refs.snackbar.close()">Dismiss</md-button>
    </md-snackbar>
  </div>
</template>


<script lang="ts">
import cloneDeep from "lodash-es/cloneDeep";
import get from "lodash-es/get";
import find from "lodash-es/find";
import map from "lodash-es/map";
import every from "lodash-es/every";
import { Memoize } from "lodash-decorators";

import "es6-promise";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch,
} from "vue-property-decorator";

import {
  SET_SAMPLES,
  SET_PIPELINE_PARAMS,
  SET_PIPELINE_DESCRIPTION,
  SET_PIPELINE_PARAMS_VALID,
  CLEAR_SAMPLE_CART,
  SET_PIPELINE_GENOME,
} from "../store";

import { Sample, SampleCartItems } from "../model";
import { WebAPI } from "../web-api";

import AVAILABLE_GENOMES from "../config/genomics/genomes";

import { DummySampleList as _dummySampleList } from "../test-data";
import { DummyPipelineConfig as _dummyPipelineConfig } from "../test-data";
import { Snackbar } from "../snackbar";
import BannerNotice from "./BannerNotice.vue";

@Component({
  components: {
    BannerNotice,
  },
  props: {},
  filters: {},
  beforeRouteLeave(to: any, from: any, next: any) {
    (this as any).beforeRouteLeave(to, from, next);
  },
})
export default class PipelineParams extends Vue {
  @Prop({ default: true, type: Boolean })
  public showButtons: boolean;
  public show_advanced = false;

  public submitting: boolean = false;
  public error_alert_message: string = "Everything is fine. 🏩";
  public snackbar_message: string = "Everything is fine. ௐ";
  public snackbar_duration: number = 2000;

  public pipelinerun_uuid: string | null = null;
  public selectedSamples: Array<Sample> = [];

  public available_genomes: Array<ReferenceGenome> = AVAILABLE_GENOMES;

  public reference_genome_valid: boolean = true;

  get selected_genome_organism(): string {
    return (
      this.get_organism_from_genome_id(
        this.$store.state.pipelineParams.genome
      ) || "Homo sapiens"
    );
  }

  set selected_genome_organism(organism: string) {
    const id =
      this.get_first_genome_id_for_organism(organism) ||
      AVAILABLE_GENOMES[0].id;
    this.$store.commit(SET_PIPELINE_GENOME, id);
  }

  public pipeline_versions = ["1.5.3", "1.5.2", "1.5.3-laxydev", "1.5.4"];
  public pipeline_aligners = [
    { text: "STAR", value: "star" },
    { text: "BWA-MEM", value: "bwa" },
  ];

  public _samples: SampleCartItems;
  get samples(): SampleCartItems {
    this._samples = cloneDeep(this.$store.state.samples);
    // We do this so that if samples change validation runs
    const _ = this.isValid_params;
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

    //this.validatePipelineParams();
  }

  get pipeline_version() {
    return this.$store.getters.pipelineParams.pipeline_version;
  }

  set pipeline_version(version: string) {
    let state = Object.assign({}, this.$store.state.pipelineParams);
    state.pipeline_version = version;
    this.$store.commit(SET_PIPELINE_PARAMS, state);
  }

  get pipeline_aligner() {
    return this.$store.getters.pipelineParams.pipeline_aligner;
  }

  set pipeline_aligner(aligner: string) {
    let state = Object.assign({}, this.$store.state.pipelineParams);
    state.pipeline_aligner = aligner;
    this.$store.commit(SET_PIPELINE_PARAMS, state);
  }

  get genome_organism_list(): string[] {
    let organisms = new Set<string>();
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

  @Memoize
  get_organism_from_genome_id(genome_id: string): string | undefined {
    return get(find(AVAILABLE_GENOMES, { id: genome_id }), "organism");
  }

  @Memoize
  get_first_genome_id_for_organism(organism: string): string | undefined {
    return get(find(AVAILABLE_GENOMES, { organism: organism }), "id");
  }

  @Memoize
  get_genome_description(reference: ReferenceGenome): string {
    const [org, centre, build] = reference.id.split("/");
    // return `${build} [${centre}] (${reference.organism})`;
    let desc = `${build} [${centre}]`;
    if (reference.recommended) {
      desc = `${desc} (recommended)`;
    }
    return desc;
  }

  onOrganismChange(e: any) {
    this.reference_genome = this.genomes_for_organism(
      this.selected_genome_organism
    )[0].id;
  }

  created() {
    this._samples = cloneDeep(this.$store.state.samples);
  }

  prepareData() {
    let data = {
      sample_cart: this.$store.state.samples.id,
      params: this.$store.getters.pipelineParams,
      pipeline: "rnasik",
      description: this.description,
    };
    return data;
  }

  get isValid_reference_genome() {
    return map(this.available_genomes, "id").includes(this.reference_genome);
  }

  get isValid_samples_added() {
    // return (this.samples.items.length != 0);
    return this.$store.getters.sample_cart_count > 0;
  }

  get isValid_duplicate_samples() {
    const samples = this.$store.state.samples;
    const seen: string[] = [];
    for (let i of samples.items) {
      for (let f of i.files) {
        for (let pair of ["R1", "R2"]) {
          if (f[pair] == null) continue;
          if (f[pair].location == null) continue;
          if (seen.includes(f[pair].location)) return false;
          seen.push(f[pair].location);
        }
      }
    }

    return true;
  }

  get isValid_mixed_single_paired_check() {
    function isPairedEnd(f: PairedEndFiles) {
      return f.R1 != null && f.R2 != null;
    }
    const samples = this.$store.state.samples;
    let is_paired: boolean[] = [];
    for (let i of samples.items) {
      for (let f of i.files) {
        is_paired.push(isPairedEnd(f));
      }
    }

    // true for all paired or all single, not a mixture
    return every(is_paired) || every(map(is_paired, (b) => !b));
  }

  get isValid_params() {
    let is_valid = false;
    if (
      this.isValid_reference_genome &&
      this.isValid_samples_added &&
      this.isValid_duplicate_samples &&
      this.isValid_mixed_single_paired_check
    ) {
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
        const response = (await WebAPI.fetcher.post(
          "/api/v1/pipelinerun/",
          data
        )) as AxiosResponse;
        this.pipelinerun_uuid = response.data.id;
      } else {
        (await WebAPI.fetcher.put(
          `/api/v1/pipelinerun/${this.pipelinerun_uuid}/`,
          data
        )) as AxiosResponse;
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

      if (!this.isValid_params) {
        Snackbar.flashMessage("Please correct errors before submitting.");
        return null;
      }

      // if (this.samples.items.length == 0) {
      //     console.log("NO samples !!");
      //     // Snackbar.flashMessage("Please add some samples to the sample cart first !");
      //     this.error_alert_message = "Please add some samples to the sample cart first !";
      //     this.openDialog("error_dialog");
      //     // throw Error( "Please add some samples to the sample cart first !");
      //     return null;
      // }

      try {
        this.submitting = true;
        let response = null;
        response = (await WebAPI.fetcher.post(
          `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`,
          {}
        )) as AxiosResponse;
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
}
</script>
