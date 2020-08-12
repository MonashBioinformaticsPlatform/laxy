<template>
  <div>
    <md-stepper @completed="startJob">
      <md-step
        md-label="Data source"
        :md-continue="dataSource_stepComplete"
        @exitstep="onExitStep('dataSource')"
        ref="dataSource"
      >
        <input-files-form v-on:stepDone v-on:invalidData v-on:dataSourceChanged></input-files-form>
      </md-step>
      <!--<md-step md-label="Analysis" md-message="Select one" :md-disabled="true" ref="analysis">-->
      <!--<p>Select your analysis: RNAseq, ChIPSeq</p>-->
      <!--</md-step>-->
      <md-step
        md-label="Describe samples"
        md-message="Specify sample names, conditions"
        :md-continue="dataSource_stepComplete"
        :md-disabled="!dataSource_stepComplete"
        @exitstep="onExitStep('describeSamples')"
        ref="describeSamples"
      >
        <sample-cart
          :fields="['name', 'metadata.condition', 'R1', 'R2']"
          :editable-fields="['name', 'metadata.condition']"
          :show-buttons="false"
          :show-toolbar="true"
          :show-add-menu="false"
          ref="describeSamples_sampleCart"
        ></sample-cart>
      </md-step>
      <md-step
        md-label="Reference genome"
        md-message="Select a reference genome"
        md-button-continue="Continue"
        :md-continue="selectGenome_stepComplete"
        :md-disabled="!selectGenome_stepComplete || !dataSource_stepComplete"
        @exitstep="onExitStep('selectGenome')"
        ref="selectGenome"
      >
        <select-genome></select-genome>
      </md-step>
      <md-step
        md-label="Pipeline settings"
        md-message="Finalise settings"
        md-button-continue="Start job"
        :md-continue="pipelineSettings_stepComplete && start_job_button_enabled"
        :md-disabled="!selectGenome_stepComplete || !dataSource_stepComplete"
        @exitstep="onExitStep('pipelineSettings')"
        ref="pipelineSettings"
      >
        <pipeline-params :show-buttons="false" ref="pipelineParams"></pipeline-params>
      </md-step>
    </md-stepper>
  </div>
</template>


<script lang="ts">
import * as _ from "lodash";
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

import SelectGenome from "./SelectGenome";

@Component({ components: { SelectGenome } })
export default class RNASeqSetup extends Vue {
  // This is a string since vue-router only allows strings to be passed as params
  @Prop({ type: String, default: "false" })
  public allowSkipping: string;

  get dataSource_stepComplete(): boolean {
    return (
      this.$store.getters.sample_cart_count > 0 || this.allowSkipping === "true"
    );
  }

  _describeSamples_stepComplete: boolean = false;
  get describeSamples_stepComplete(): boolean {
    return this._describeSamples_stepComplete || this.allowSkipping === "true";
  }

  set describeSamples_stepComplete(state: boolean) {
    this._describeSamples_stepComplete = state;
  }

  get selectGenome_stepComplete(): boolean {
    return (
      this.allowSkipping === "true" || this.$store.get("genome_values_valid")
    );
  }

  public start_job_button_enabled = true;
  get pipelineSettings_stepComplete(): boolean {
    return this.$store.state.pipelineParams_valid;
  }

  //        enableStep() {
  //            let refName = 'describeSamples';
  //            (this.$refs[refName] as mdStep).mdActive = true;
  //            console.log("Enabled step " + refName);
  //
  //            this.dataSource_stepComplete = true;
  //        }

  async scrollToTop() {
    const topOfPage = { x: 0, y: 0 };
    const duration = 300; // ms
    return new Promise((resolve, reject) => {
      window.scrollTo({
        top: topOfPage.y,
        left: topOfPage.x,
        behavior: "smooth",
      });
      setTimeout(() => {
        resolve(topOfPage);
      }, duration);
    });
  }

  onExitStep(stepName: string) {
    if (stepName === "dataSource") {
      this.scrollToTop();
    } else if (stepName === "describeSamples") {
      (this.$refs["describeSamples_sampleCart"] as any).save();
      this.describeSamples_stepComplete = true;
      this.scrollToTop();
    } else if (stepName === "selectGenome") {
      this.scrollToTop();
    } else if (stepName === "pipelineSettings") {
      this.scrollToTop();
    }
  }

  async startJob() {
    try {
      this.start_job_button_enabled = false;
      const response = await (this.$refs["pipelineParams"] as any).run();
      if (response == null) {
        throw Error("Request to start job failed");
      }
      if (response && response.data && response.data.id) {
        this.$router.push({ name: "job", params: { jobId: response.data.id } });
      } else {
        this.$router.push("jobs");
      }
    } catch (error) {
      this.start_job_button_enabled = true;
      throw error;
    }
  }
}
</script>
