<template>
    <div>
        <md-stepper @completed="startJob">
            <md-step md-label="Data source"
                     :md-continue="dataSource_stepComplete"
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
                     ref="describeSamples">
                <sample-cart :show-buttons="false" ref="sampleCart"></sample-cart>
            </md-step>
            <md-step md-label="Pipeline settings"
                     md-message="Use the defaults Luke !"
                     md-button-continue="Start job"
                     :md-continue="pipelineSettings_stepComplete"
                     :md-disabled="!describeSamples_stepComplete"
                     ref="pipelineSettings">
                <pipeline-params :show-buttons="false" ref="pipelineParams"></pipeline-params>
            </md-step>
        </md-stepper>
    </div>
</template>


<script lang="ts">
    import 'vue-material/dist/vue-material.css';

    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import Component from 'vue-class-component';
    import {Emit, Inject, Model, Prop, Provide, Watch} from 'vue-property-decorator'
    import VueMaterial from 'vue-material';

    // import InputFilesForm from 'InputFilesForm.vue';

    //    interface RNASeqSetup extends Vue {
    //    }

    //    interface MdStep extends Vue {
    //        mdActive: boolean;
    //        mdContinue: boolean;
    //    }

    @Component({props: {}})
    export default class RNASeqSetup extends Vue {
//        components: {
//            // 'input-files-form': InputFilesForm
//        },

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
