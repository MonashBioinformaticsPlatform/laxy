<template>
  <div>
    <md-stepper @completed="startJob">
      <md-step
        md-label="Data source"
        :md-continue="stepsComplete.dataSource"
        @exitstep="onExitStep('dataSource')"
      >
        <ena-file-select :show-buttons="true" ref="dataSource"></ena-file-select>
      </md-step>
      <md-step
        md-label="Name Samples"
        md-message
        :md-continue="stepsComplete.sampleCart"
        :md-disabled="!stepsComplete.dataSource"
        @exitstep="onExitStep('sampleCart')"
      >
        <sample-cart :show-buttons="false" ref="sampleCart"></sample-cart>
      </md-step>
      <md-step
        md-label="Pipeline settings"
        md-message="Choose a reference genome"
        md-button-continue="Start job"
        :md-continue="stepsComplete.pipelineParams"
        :md-disabled="!stepsComplete.sampleCart"
        @exitstep="onExitStep('pipelineParams')"
      >
        <pipeline-params :show-buttons="false" ref="pipelineParams"></pipeline-params>
      </md-step>
    </md-stepper>
  </div>
</template>


<script lang="ts">
// import 'vue-material/dist/vue-material.css';

import * as _ from 'lodash';
import 'es6-promise';

import axios, { AxiosResponse } from 'axios';
import Vue, { ComponentOptions } from 'vue';
import Component from 'vue-class-component';
import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator'
// import VueMaterial from 'vue-material';

import ENAFileSelect from "./ENAFileSelect";

@Component({
  components: { 'ena-file-select': ENAFileSelect },
  props: {}
})
export default class ENAFlow extends Vue {
  public stepsComplete = {
    dataSource: true,
    sampleCart: true,
    pipelineParams: true,
  };

  onExitStep(stepName: string) {
    if (stepName === 'dataSource') {
      //
    }
    else if (stepName === 'sampleCart') {
      (this.$refs[stepName] as any).save();
    }
    else if (stepName === 'pipelineParams') {
      (this.$refs[stepName] as any).save();
    }
  }

  async startJob() {
    try {
      await (this.$refs['pipelineParams'] as any).run();
      this.$router.push('jobs');
    }
    catch (error) {
      throw error;
    }
  }
}

</script>
