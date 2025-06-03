<template>
  <div>
    <md-dialog-alert :md-content-html="error_alert_message" :md-content="error_alert_message"
      ref="error_dialog"></md-dialog-alert>
    <md-layout md-column>
      <form novalidate>
        <md-whiteframe class="pad-32">
          <h2>BRB-seq demux + nf-core/rnaseq</h2>
          <md-whiteframe class="pad-32" md-elevation="8">
            BRB-seq demultiplexing + <a href="https://nf-co.re/rnaseq">nf-core/rnaseq</a>
            <br />This pipeline runs demultiplexing for BRB-seq samples, then 
            runs the standard nf-core/rnaseq pipeline for transcript quantification
          </md-whiteframe>
          <h3>Pipeline parameters</h3>
          <md-input-container>
            <label>Description</label>
            <md-input v-model="description" placeholder="Description of pipeline run ..."></md-input>
          </md-input-container>
          <md-input-container>
            <label for="strandedness">Strandedness</label>
            <md-select name="strandedness" id="strandedness" v-model="strandedness">
              <md-option v-for="strand_option in standedness_options" :key="strand_option.value"
                :value="strand_option.value">{{ strand_option.text }}</md-option>
            </md-select>
          </md-input-container>

          <md-switch v-model="show_advanced" id="advanced-toggle" name="advanced-toggle" class="md-primary">Show
            advanced options</md-switch>
          <transition name="fade">
            <md-layout v-if="show_advanced">
              <md-input-container>
                <label for="pipeline_version">Pipeline version</label>
                <md-select name="pipeline_version" id="pipeline_version" v-model="pipeline_version">
                  <md-option v-for="version in pipeline_versions" :key="version" :value="version">{{
                    version
                  }}</md-option>
                </md-select>
              </md-input-container>

              <md-layout md-column>
                <md-switch v-model="debug_mode" id="debug-toggle" name="debug-toggle" class="md-primary">Enable DEBUG
                  mode</md-switch>

                <md-switch v-if="umi_option_supported" v-model="has_umi" id="umi-toggle" name="umi-toggle"
                  class="md-primary">
                  Use UMIs <em>(UMIs must be in the FASTQ header from bcl2fastq demultiplexing, not in the
                    sequence)</em></md-switch>

                <md-layout>
                  <md-layout>
                    <md-input-container>
                      <label>Exclude samples with less this percentage of mapped reads
                        (<code>--min_mapped_reads</code>)</label>
                      <md-input type="number" min="0" max="100" v-model="min_mapped_reads"></md-input>
                    </md-input-container>
                  </md-layout>
                  <md-layout md-flex="5" md-vertical-align="center">
                    <md-button id="minMappedReadshelpButton" @click="openDialog('minMappedReadsHelpPopup')"
                      class="push-right md-icon-button md-raised md-dense">
                      <md-icon style="color: #bdbdbd;">help</md-icon>
                    </md-button>
                  </md-layout>
                </md-layout>

                <md-switch v-model="save_reference_genome" id="save-reference-genome-toggle"
                  name="save-reference-genome-toggle" class="md-primary">Save reference genome</md-switch>

                <md-switch v-model="save_genome_index" id="save-genome-index-toggle" name="save-genome-index-toggle"
                  class="md-primary">Save reference genome index</md-switch>

                <md-switch v-model="skip_trimming" id="skip-trimming-toggle" name="skip-trimming-toggle"
                  class="md-primary">Skip trimming reads</md-switch>

                <md-layout v-if="trimmer_option_supported && !skip_trimming">
                  <md-layout>
                    <md-input-container>
                      <label for="trimmer">Trimmer</label>
                      <md-select name="trimmer" id="trimmer" v-model="trimmer">
                        <md-option v-for="trimmer_option in trimmer_options" :key="trimmer_option.value"
                          :value="trimmer_option.value">{{ trimmer_option.text }}</md-option>
                      </md-select>
                    </md-input-container>
                  </md-layout>
                  <md-layout md-flex="5" md-vertical-align="center">
                    <md-button id="fastpHelpButton" @click="openDialog('fastpHelpPopup')"
                      class="push-right md-icon-button md-raised md-dense">
                      <md-icon style="color: #bdbdbd;">help</md-icon>
                    </md-button>
                  </md-layout>
                </md-layout>

              <md-layout md-column>
                <h3>Read structure for demultiplexing</h3>
                <md-input-container>
                  <label>R1 read structure</label>
                  <md-input v-model="readstructure_R1" placeholder="14B14M122T"></md-input>
                </md-input-container>

                <md-input-container>
                  <label>R2 read structure</label>
                  <md-input v-model="readstructure_R2" placeholder="150T"></md-input>
                </md-input-container>
              </md-layout>

            </md-layout>
            </md-layout>
          </transition>
        </md-whiteframe>
      </form>

      <md-whiteframe class="pad-16" md-elevation="2">
        <select-genome :genomes="available_genomes"></select-genome>
      </md-whiteframe>

      <md-whiteframe class="pad-16" md-elevation="2">
        <input-files-form title-text="FASTQ files"></input-files-form>
      </md-whiteframe>

      <md-whiteframe class="pad-16" md-elevation="2">
        <csv-text-form 
          title-text="Paste your barcode samplesheet here (CSV or TSV)" 
          label-text="Barcode samplesheet" 
          :show-columns="['*title', 'barcode']"
          :placeholder-text="'*title,barcode\nsample1,TACGAGTACAGACA\n\n(other columns are ignored)'" 
          @data-modified="handleCsvDataModified"></csv-text-form>
      </md-whiteframe>

      <md-whiteframe v-if="barcodeSamplesheetData && barcodeSamplesheetData.length > 0" class="pad-16" md-elevation="2">
        <h4>Barcode sample sheet preview</h4>
        <md-table v-if="barcodeSamplesheetHeaders.length > 0" style="width: fit-content;">
          <md-table-row>
            <md-table-head v-for="header in barcodeSamplesheetHeaders" :key="header">{{ header }}</md-table-head>
          </md-table-row>

          <md-table-row v-for="(row, rowIndex) in barcodeSamplesheetData" :key="rowIndex">
            <md-table-cell v-for="header in barcodeSamplesheetHeaders" :key="header">{{ row[header] }}</md-table-cell>
          </md-table-row>
        </md-table>
      </md-whiteframe>

      <md-whiteframe class="pad-32" md-elevation="8">
        <h3>Sample summary</h3>
        <sample-cart v-if="samples.items.length > 0" :samples="samples"
          :fields="['name', 'metadata.condition', 'R1', 'R2']" :show-toolbar="false" :show-add-menu="false"
          :show-buttons="false" :editable-set-name="false" :selectable="false" @selected="onSelect"></sample-cart>
        <div v-if="samples.items.length === 0">No samples in cart.</div>
      </md-whiteframe>
      <md-layout v-if="showButtons">
        <!-- <md-button class="md-primary md-raised" @click="save">Save</md-button> -->
        <md-button :disabled="!isValid_params || submitting" class="md-primary md-raised" @click="run">Run the
          pipeline</md-button>
      </md-layout>

      <banner-notice v-if="!isValid_samples_added" type="error" :show-close-button="false">Please add some samples
        before submitting your job.</banner-notice>
      <banner-notice v-if="!isValid_duplicate_samples" type="error" :show-close-button="false">
        Input sample files contain duplicates (based on URL/location).
        <br />Please remove duplicates before continuing.
      </banner-notice>
      <banner-notice v-if="!isValid_reference_genome" type="error" :show-close-button="false">Selected reference genome
        is invalid.</banner-notice>
      <banner-notice v-if="!isValid_strandedness_option" type="error" :show-close-button="false">The selected version of
        nf-core/rnaseq does not support 'auto' strandedness. Please select another strandedness option, or another
        pipeline version.
      </banner-notice>
      <banner-notice v-if="!isValid_min_mapped_reads" type="error" :show-close-button="false">Invalid value for minimum
        mapped reads - should be an integer between 0 and 100.
      </banner-notice>
      <banner-notice v-if="!isValid_barcode_samplesheet" type="error" :show-close-button="false">
        Barcode samplesheet must contain at least one row with required headers: 'barcode' and one of '*title', 'title', or 'sample_id'.
      </banner-notice>


      <md-dialog md-open-from="#minMappedReadshelpButton" md-close-to="#minMappedReadshelpButton"
        id="minMappedReadsHelpPopup" ref="minMappedReadsHelpPopup">
        <md-dialog-title>Minimum mapped reads</md-dialog-title>

        <md-dialog-content>
          The nf-core/rnaseq <code>--min_mapped_reads</code> option.<br />
          Samples with mapping rates less than this are excluded from the final counts matrix and most QC steps.<br />
          Setting this to below 5% risks some downstream steps failing, since not all tools handle samples with very
          low mapping rates gracefully.<br />
        </md-dialog-content>

        <md-dialog-actions>
          <md-button class="md-primary" @click="closeDialog('minMappedReadsHelpPopup')">Close</md-button>
        </md-dialog-actions>
      </md-dialog>

      <md-dialog md-open-from="#fastpHelpButton" md-close-to="#fastpHelpButton" id="fastpHelpPopup"
        ref="fastpHelpPopup">
        <md-dialog-title>Fastp Trimmer</md-dialog-title>

        <md-dialog-content>
          When using the 'fastp' trimmer, the flags <code>--trim_poly_g --trim_poly_x</code> are enabled by default to
          remove polyG/polyX tails.
        </md-dialog-content>

        <md-dialog-actions>
          <md-button class="md-primary" @click="closeDialog('fastpHelpPopup')">Close</md-button>
        </md-dialog-actions>
      </md-dialog>

    </md-layout>

    <md-snackbar md-position="bottom center" ref="snackbar" :md-duration="snackbar_duration">
      <span>{{ snackbar_message }}</span>
      <md-button class="md-accent" @click="closeSnackbar">Dismiss</md-button>
    </md-snackbar>
  </div>
</template>


<script lang="ts">
import cloneDeep from "lodash-es/cloneDeep";
import get from "lodash-es/get";
//import find from "lodash-es/find";
//import map from "lodash-es/map";
//import every from "lodash-es/every";
import sortBy from "lodash-es/sortBy";
import last from "lodash-es/last";
//import { Memoize } from "lodash-decorators";

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
  Watch
} from "vue-property-decorator";

import { compareVersions } from 'compare-versions';

import { Get, Sync, Call } from "vuex-pathify";

import { SET_SAMPLES, CLEAR_SAMPLE_CART } from "../../../../store";

import storeModule from "../store/module";

import { Sample, SampleCartItems } from "../../../../model";
import { WebAPI } from "../../../../web-api";

import { Snackbar } from "../../../../snackbar";
import BannerNotice from "../../../BannerNotice.vue";
import InputFilesForm from "../../../InputFilesForm.vue";
import CsvTextForm from "../../../CsvTextForm.vue";
import SelectGenome from "../../../SelectGenome.vue";
import { ReferenceGenome } from "../../../../types";
import AVAILABLE_GENOMES from "../config/genomes";

@Component({
  components: {
    BannerNotice,
    InputFilesForm,
    CsvTextForm,
    SelectGenome
  },
  props: {},
  filters: {},
  beforeRouteLeave(to: any, from: any, next: any) {
    (this as any).beforeRouteLeave(to, from, next);
  }
})
export default class PipelineParams extends Vue {
  public pipeline_name: string = "nf-core-rnaseq-brbseq";
  public available_genomes: Array<ReferenceGenome> = AVAILABLE_GENOMES;

  @Prop({ default: true, type: Boolean })
  public showButtons: boolean;
  public show_advanced = false;

  public submitting: boolean = false;
  public error_alert_message: string = "Everything is fine. 🏩";
  public snackbar_message: string = "Everything is fine. ௐ";
  public snackbar_duration: number = 2000;

  public pipelinerun_uuid: string | null = null;
  public selectedSamples: Array<Sample> = [];

  // Removed local properties for barcode samplesheet, will use store + computed for headers
  // public barcodeSamplesheetData: Record<string, string>[] = [];
  // public barcodeSamplesheetHeaders: string[] = [];

  get pipeline_versions() {
    // const versions = = ["3.1", "3.2", "3.10.1"];
    return get(
      this.$store.state.availablePipelines[this.pipeline_name],
      "metadata.versions",
      []
    );
  }

  get default_pipeline_version() {
    const version = get(
      this.$store.state.availablePipelines[this.pipeline_name],
      "metadata.default_version",
      last(
        sortBy(this.pipeline_versions, v => {
          return v;
        })
      )
    );
    // For older versions, ensure the strandedness dropdown is populated
    // with a default that is not 'auto'.
    if (compareVersions(version, "3.7") < 0) {
      this.strandedness = 'unstranded';
    }
    return version;
  }

  get standedness_options() {
    if (this.auto_strandedness_option_supported) {
      return [
        { value: 'auto', text: 'auto' },
        { value: 'unstranded', text: 'unstranded' },
        { value: 'forward', text: 'forward' },
        { value: 'reverse', text: 'reverse' }
      ]
    };

    return [
      { value: 'unstranded', text: 'unstranded' },
      { value: 'forward', text: 'forward' },
      { value: 'reverse', text: 'reverse' }
    ]
  }

  get trimmer_options() {
    return [
      { value: 'fastp', text: 'fastp' },
      { value: 'trimgalore', text: 'trimgalore' }
    ]
  }

  public _samples: SampleCartItems;
  get samples(): SampleCartItems {
    this._samples = cloneDeep(this.$store.state.samples);
    // We trigger the computed property so that if samples change validation runs
    const _ = this.isValid_params;
    return this._samples;
  }

  @Sync("pipelineParams@description")
  public description: string;

  @Sync("pipelineParams@pipeline_version")
  public pipeline_version: string;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.strandedness")
  public strandedness: string;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.trimmer")
  public trimmer: string;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.debug_mode")
  public debug_mode: boolean;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.has_umi")
  public has_umi: boolean;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.min_mapped_reads")
  public min_mapped_reads: number;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.save_reference_genome")
  public save_reference_genome: boolean;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.save_genome_index")
  public save_genome_index: boolean;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.skip_trimming")
  public skip_trimming: boolean;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.barcode_samplesheet") // Sync with the new store property
  public barcodeSamplesheetData: Record<string, string>[];

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.readstructure.R1") // Sync for R1 read structure
  public readstructure_R1: string;

  @Sync("pipelineParams@nf-core-rnaseq-brbseq.readstructure.R2") // Sync for R2 read structure
  public readstructure_R2: string;

  created() {
    this.$store.registerModule(
      ["pipelineParams", this.pipeline_name],
      storeModule
    );

    this._samples = cloneDeep(this.$store.state.samples);
    this.pipeline_version = this.default_pipeline_version;
  }

  /*
   *  Populates the pipelineParams.fetch_files list with files
   *  from the sample cart (and external genome reference files)
   *  that should be retrieved by the backend as initial input files.
   */

  updateFetchFiles() {
    if (!this.$store.state.use_custom_genome) {
      this.$store.set("pipelineParams@user_genome.fasta_url", "");
      this.$store.set("pipelineParams@user_genome.annotation_url", "");
    }

    const fetch_files = this.$store.get(
      "pipelineParams/generateFetchFilesList"
    );
    let params = this.$store.copy("pipelineParams");
    params.fetch_files = fetch_files;
    this.$store.set("pipelineParams", params);
  }

  prepareData() {
    this.updateFetchFiles();

    let data = {
      sample_cart: this.$store.state.samples.id,
      params: this.$store.getters.pipelineParams,
      pipeline: this.pipeline_name,
      description: this.description
    };

    data = cloneDeep(data);

    if (this.$store.state.use_custom_genome) {
      data.params.genome = null;
    }

    // If skipping trimming, set the trimmer param to blank
    if (this.skip_trimming) {
      data.params['nf-core-rnaseq'].trimmer = '';
    }

    return data;
  }

  get isValid_samples_added() {
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

  get isValid_reference_genome() {
    return this.$store.get("pipelineParams/isValidReferenceGenome");
  }

  get trimmer_option_supported() {
    let supported_versions = ['3.18.0'];
    return supported_versions.includes(this.pipeline_version);
  }

  get auto_strandedness_option_supported() {
    return compareVersions(this.pipeline_version, "3.7") >= 0;
  }

  get umi_option_supported() {
    // nf-core/rnaseq had some UMI support in earlier versions (at least since 3.2),
    // however options were limited - we only support more recent versions here
    const supported = compareVersions(this.pipeline_version, "3.10") >= 0;
    if (!supported) {
      this.has_umi = false;
    }
    return supported;
  }

  get isValid_strandedness_option() {
    if (this.strandedness == 'auto') {
      // version 3.7+ required to support the 'auto' option
      return this.auto_strandedness_option_supported;
    }
    return true;
  }

  get isValid_min_mapped_reads() {
    if (this.min_mapped_reads >= 0 &&
      this.min_mapped_reads <= 100) {
      return true;
    }
    return false;
  }

  get isValid_barcode_samplesheet() {
    // Check if we have at least one row
    if (!this.barcodeSamplesheetData || this.barcodeSamplesheetData.length === 0) {
      return false;
    }

    // Check if required headers are present
    const headers = this.barcodeSamplesheetHeaders;
    const hasBarcode = headers.includes('barcode');
    const hasTitleHeader = headers.includes('*title') || headers.includes('title') || headers.includes('sample_id');
    
    return hasBarcode && hasTitleHeader;
  }

  get isValid_params() {
    let is_valid = false;
    if (
      this.isValid_reference_genome &&
      this.isValid_samples_added &&
      this.isValid_duplicate_samples &&
      this.isValid_strandedness_option &&
      this.isValid_min_mapped_reads &&
      this.isValid_barcode_samplesheet
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
      this.submitting = true;
      await this.save();
      this.submitting = true;

      if (!this.isValid_params) {
        Snackbar.flashMessage("Please correct errors before submitting.");
        this.submitting = false;
        return null;
      }

      try {
        let response = null;
        response = (await WebAPI.fetcher.post(
          `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`,
          {}
        )) as AxiosResponse;
        this.submitting = false;
        Snackbar.flashMessage("Saved !");
        await this.clearCart();

        if (response == null) {
          throw Error("Request to start job failed");
        }
        if (response && response.data && response.data.id) {
          this.$router.push({
            name: "job",
            params: { jobId: response.data.id }
          });
        }
        // } else {
        //   this.$router.push("jobs");
        // }

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

    this.submitting = false;
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

  closeSnackbar() {
    const snackbar = this.$refs.snackbar as any;
    if (snackbar && typeof snackbar.close === "function") {
      snackbar.close();
    }
  }

  onSelect(rows: any) {
    this.selectedSamples = rows as Array<Sample>;
  }

  routeTo(name: string, params: any = {}) {
    this.$router.push({ name: name, params: params });
  }

  @Watch("pipeline_version", { immediate: true })
  onPipelineVersionChange(newVersion: string, oldVersion: string) {
    if (!this.trimmer_option_supported) {
      this.trimmer = "";
    } else if (this.trimmer === "") {
      this.trimmer = "fastp";
    }

    if (newVersion && compareVersions(newVersion, "3.7") < 0 && this.strandedness === 'auto') {
      this.strandedness = 'unstranded';
    }
  }

  get barcodeSamplesheetHeaders(): string[] {
    if (this.barcodeSamplesheetData && this.barcodeSamplesheetData.length > 0) {
      return Object.keys(this.barcodeSamplesheetData[0]);
    }
    return [];
  }

  public handleCsvDataModified(data: Record<string, string>[]) {
    this.$store.set(`pipelineParams/${this.pipeline_name}/barcode_samplesheet`, data);
  }

  beforeRouteLeave(to: any, from: any, next: any) {
    // console.log([to, from, next]);
    this.$store.set("samples", this._samples);
    next();
  }
}
</script>