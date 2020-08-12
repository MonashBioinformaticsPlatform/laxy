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
      <form novalidate>
        <md-whiteframe style="padding: 32px;">
          <h2>RNAsik</h2>
          <h3>Pipeline parameters</h3>
          <md-input-container>
            <label>Description</label>
            <md-input v-model="description" placeholder="Description of pipeline run ..."></md-input>
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
      </form>

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

import { Get, Sync, Call } from "vuex-pathify";

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
import RemoteFilesSelect from "./RemoteSelect/RemoteFilesSelect.vue";
import { FileListItem } from "../file-tree-util";
import { filenameFromUrl } from "../util";
import { ReferenceGenome, ILaxyFile, PairedEndFiles } from "../types";

@Component({
  components: {
    BannerNotice,
    RemoteFilesSelect,
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

  public reference_genome_valid: boolean = true;
  public available_genomes: Array<ReferenceGenome> = AVAILABLE_GENOMES;

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

  @Sync("pipelineParams@description")
  public description: string;

  @Sync("pipelineParams@pipeline_version")
  public pipeline_version: string;

  get pipeline_aligner() {
    return this.$store.getters.pipelineParams.pipeline_aligner;
  }

  set pipeline_aligner(aligner: string) {
    let state = Object.assign({}, this.$store.state.pipelineParams);
    state.pipeline_aligner = aligner;
    this.$store.set("pipelineParams", state);
  }

  created() {
    this._samples = cloneDeep(this.$store.state.samples);
  }

  /*
   *  Populates the pipelineParams.fetch_files list with files
   *  that should be retrieved by the backend as initial input files.
   *  For RNAsik runs, this is the reference genome files and input
   *  FASTQ files.
   *
   *  TODO: Deprecate sample_cart on the backend and just use this.
   *        Keep using the state.samples data structure here on the
   *        frontend for convenience, but convert it's content into
   *        fetch_files for use by pipeline_config.json / laxydl.
   */
  updateFetchFiles() {
    if (!this.$store.state.use_custom_genome) {
      this.$store.set("pipelineParams@user_genome.fasta_url", "");
      this.$store.set("pipelineParams@user_genome.annotation_url", "");
    }

    const fastaUrl = this.$store.get("pipelineParams@user_genome.fasta_url");
    const annotUrl = this.$store.get(
      "pipelineParams@user_genome.annotation_url"
    );

    let annotType = "annotation";
    if (annotUrl.includes(".gff")) {
      annotType = "gff";
    } else if (annotUrl.includes(".gtf")) {
      annotType = "gtf";
    }

    let params = this.$store.copy("pipelineParams");

    const fetch_files: ILaxyFile[] = [];

    if (this.$store.state.use_custom_genome && fastaUrl && annotUrl) {
      params.genome = null;

      fetch_files.push(
        ...[
          {
            name: filenameFromUrl(fastaUrl) || "", //"genome.fa.gz",
            location: fastaUrl.trim(),
            type_tags: ["reference_genome", "genome_sequence", "fasta"],
          } as ILaxyFile,
          {
            name: filenameFromUrl(annotUrl) || "", //"genes.gff.gz",
            location: annotUrl.trim(),
            type_tags: ["reference_genome", "genome_annotation", annotType],
          } as ILaxyFile,
        ]
      );
    }

    const samples = this.$store.state.samples;
    for (let i of samples.items) {
      for (let f of i.files) {
        for (let pair of Object.keys(f)) {
          const sampleFile: ILaxyFile = cloneDeep(f[pair]);

          if (sampleFile == null) continue;
          if (sampleFile.location == null) continue;

          sampleFile.metadata = sampleFile.metadata || {};
          sampleFile.type_tags = sampleFile.type_tags || [];
          sampleFile.metadata["read_pair"] = pair;

          let doppelganger = pair == "R1" ? "R2" : "R1";
          if (f[doppelganger] != null) {
            sampleFile.metadata["paired_file"] = f[doppelganger].name;
          }

          sampleFile.type_tags.push("ngs_reads");

          fetch_files.push(sampleFile);
        }
      }
    }

    params.fetch_files = fetch_files;
    this.$store.set("pipelineParams", params);
  }

  prepareData() {
    this.updateFetchFiles();

    let data = {
      sample_cart: this.$store.state.samples.id,
      params: this.$store.getters.pipelineParams,
      pipeline: "rnasik",
      description: this.description,
    };
    return data;
  }

  get isValid_reference_genome() {
    const reference_genome = this.$store.get("pipelineParams@genome");
    const fastaUrl = this.$store.get("pipelineParams@user_genome.fasta_url");
    const annotUrl = this.$store.get(
      "pipelineParams@user_genome.annotation_url"
    );

    const isSet: boolean =
      map(this.available_genomes, "id").includes(reference_genome) ||
      (reference_genome == null && fastaUrl && annotUrl);
    return isSet;
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
    this.$store.set("pipelineParams_valid", is_valid);

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
    this.$store.set("samples", this._samples);
    next();
  }
}
</script>