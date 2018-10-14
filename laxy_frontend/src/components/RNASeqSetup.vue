<template>
    <div>
        <md-stepper @completed="startJob">
            <md-step md-label="Data source"
                     :md-continue="dataSource_stepComplete"
                     @exitstep="onExitStep('dataSource')"
                     ref="dataSource">
                <input-files-form v-on:stepDone=""
                                  v-on:invalidData=""
                                  v-on:dataSourceChanged="">
                </input-files-form>
            </md-step>
            <!--<md-step md-label="Analysis" md-message="Select one" :md-disabled="true" ref="analysis">-->
            <!--<p>Select your analysis: RNAseq, ChIPSeq</p>-->
            <!--</md-step>-->
            <md-step md-label="Describe samples" md-message="Specify conditions, pair ends"
                     :md-continue="describeSamples_stepComplete"
                     :md-disabled="!dataSource_stepComplete"
                     @exitstep="onExitStep('describeSamples')"
                     ref="describeSamples">
                <sample-cart :fields="['name', 'metadata.condition', 'R1', 'R2']"
                             :editable-fields="['name', 'metadata.condition']"
                             :show-buttons="false"
                             :show-toolbar="true"
                             :show-add-menu="false"
                             ref="describeSamples_sampleCart"></sample-cart>
            </md-step>
            <md-step md-label="Pipeline settings"
                     md-message="Use the defaults Luke !"
                     md-button-continue="Start job"
                     :md-continue="pipelineSettings_stepComplete"
                     :md-disabled="!describeSamples_stepComplete"
                     @exitstep="onExitStep('pipelineSettings')"
                     ref="pipelineSettings">
                <pipeline-params :show-buttons="false" ref="pipelineParams"></pipeline-params>
            </md-step>
        </md-stepper>
    </div>
</template>


<script lang="ts">
    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import Component from 'vue-class-component';
    import {Emit, Inject, Model, Prop, Provide, Watch} from 'vue-property-decorator'

    @Component({props: {}})
    export default class RNASeqSetup extends Vue {
        get dataSource_stepComplete() {
            return this.$store.getters.sample_cart_count > 0;
        }

        describeSamples_stepComplete: boolean = true;
        pipelineSettings_stepComplete: boolean = true;

//        enableStep() {
//            let refName = 'describeSamples';
//            (this.$refs[refName] as mdStep).mdActive = true;
//            console.log("Enabled step " + refName);
//
//            this.dataSource_stepComplete = true;
//        }

        async scrollToTop() {
            const topOfPage = {x: 0, y: 0};
            const duration = 300; // ms
            return new Promise((resolve, reject) => {
                window.scrollTo({
                    top: topOfPage.y,
                    left: topOfPage.x,
                    behavior: 'smooth'
                });
                setTimeout(() => {
                    resolve(topOfPage);
                }, duration);
            });
        }

        onExitStep(stepName: string) {
            if (stepName === 'dataSource') {
                this.scrollToTop();
            }
            else if (stepName === 'describeSamples') {
                 (this.$refs['describeSamples_sampleCart'] as any).save();
                 this.scrollToTop();
            }
            else if (stepName === 'pipelineSettings') {
                this.scrollToTop();
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
