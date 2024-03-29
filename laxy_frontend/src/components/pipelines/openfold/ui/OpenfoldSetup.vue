<template>
  <div>
    <md-dialog-alert :md-content-html="error_alert_message" :md-content="error_alert_message"
      ref="error_dialog"></md-dialog-alert>
    <md-layout md-column>
      <form novalidate>
        <md-whiteframe class="pad-32">
          <h2>Openfold</h2>
          <md-whiteframe class="pad-32" md-elevation="8">
            <a href="https://github.com/aqlaboratory/openfold">Openfold</a>
            A memory-efficient, and GPU-friendly PyTorch reproduction of AlphaFold 2.
            Predicts proteins structures based on primary sequence.
            <br />
          </md-whiteframe>
          <h3>Pipeline parameters</h3>
          <md-input-container>
            <label>Description</label>
            <md-input v-model="description" placeholder="Description of pipeline run ..."></md-input>
          </md-input-container>
          <md-input-container>
            <label>FASTA format sequence(s)</label>
            <md-textarea v-model="fasta" maxlength="10000" placeholder=""></md-textarea>
          </md-input-container>
        </md-whiteframe>
      </form>

      <md-layout v-if="showButtons">
        <!-- <md-button class="md-primary md-raised" @click="save">Save</md-button> -->
        <md-button :disabled="!isValid_params || submitting" class="md-primary md-raised" @click="run">Run the
          pipeline</md-button>
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
import sortBy from "lodash-es/sortBy";
import last from "lodash-es/last";
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
  Watch
} from "vue-property-decorator";

import { Get, Sync, Call } from "vuex-pathify";

import {
  Store,
  SET_SAMPLES,
  SET_PIPELINE_PARAMS,
  SET_PIPELINE_DESCRIPTION,
  SET_PIPELINE_PARAMS_VALID,
  CLEAR_SAMPLE_CART
} from "../../../../store";

import storeModule from "../store/module";

import { Sample, SampleCartItems } from "../../../../model";
import { WebAPI } from "../../../../web-api";

import { Snackbar } from "../../../../snackbar";
import BannerNotice from "../../../BannerNotice.vue";
import InputFilesForm from "../../../InputFilesForm.vue";
import RemoteFilesSelect from "../../../RemoteSelect/RemoteFilesSelect.vue";
import { FileListItem } from "../../../../file-tree-util";
import { filenameFromUrl } from "../../../../util";
import { ILaxyFile, PairedEndFiles } from "../../../../types";

@Component({
  components: {
    InputFilesForm
  },
  props: {},
  filters: {},
  beforeRouteLeave(to: any, from: any, next: any) {
    (this as any).beforeRouteLeave(to, from, next);
  }
})
export default class PipelineParams extends Vue {
  public pipeline_name: string = "openfold";

  @Prop({ default: true, type: Boolean })
  public showButtons: boolean;
  public show_advanced = false;

  public submitting: boolean = false;
  public error_alert_message: string = "Everything is fine. 🏩";
  public snackbar_message: string = "Everything is fine. ௐ";
  public snackbar_duration: number = 2000;

  public pipelinerun_uuid: string | null = null;
  public selectedSamples: Array<Sample> = [];

  get pipeline_versions() {
    // const versions = = ["1.5.3", "1.5.2", "1.5.3-laxydev", "1.5.4"];
    return get(
      this.$store.state.availablePipelines[this.pipeline_name],
      "metadata.versions",
      []
    );
  }

  get default_pipeline_version() {
    return get(
      this.$store.state.availablePipelines[this.pipeline_name],
      "metadata.default_version",
      last(
        sortBy(this.pipeline_versions, v => {
          return v;
        })
      )
    );
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

  @Sync("pipelineParams@openfold.input.fasta")
  public fasta: boolean;

  created() {
    this.$store.registerModule(
      ["pipelineParams", this.pipeline_name],
      storeModule
    );

    this._samples = cloneDeep(this.$store.state.samples);
  }

  mounted() {
    this.pipeline_version = this.default_pipeline_version;
  }

  /*
   *  Populates the pipelineParams.fetch_files list with (FASTQ) files
   *  from the sample cart that should be retrieved by the backend as
   *  initial input files.
   */
  updateFetchFiles() {
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
      params: this.$store.getters.pipelineParams,
      pipeline: this.pipeline_name,
      description: this.description
    };
    return data;
  }

  // get isValid_samples_added() {
  //   return this.$store.getters.sample_cart_count > 0;
  // }

  get isValid_params() {
    let is_valid = true;
    //let is_valid = false;
    // if (this.isValid_samples_added) {
    //   is_valid = true;
    // }
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

      // if (!this.isValid_params) {
      //   Snackbar.flashMessage("Please correct errors before submitting.");
      //   this.submitting = false;
      //   return null;
      // }

      try {
        let response: AxiosResponse<any> | null = null;
        response = (await WebAPI.fetcher.post(
          `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`,
          {}
        )) as AxiosResponse<any>;
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

  onSelect(rows: any) {
    this.selectedSamples = rows as Array<Sample>;
  }

  routeTo(name: string, params: any = {}) {
    this.$router.push({ name: name, params: params });
  }

  beforeRouteLeave(to: any, from: any, next: any) {
    // console.log([to, from, next]);
    this.$store.set("samples", this._samples);
    next();
  }
}
</script>