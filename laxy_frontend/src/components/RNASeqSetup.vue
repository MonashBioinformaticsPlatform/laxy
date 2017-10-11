<template>
    <div>
        <md-stepper>
            <md-step md-label="Data source"
                     :md-continue="dataSource_stepComplete"
                     ref="dataSource">
                <input-files-form v-on:stepDone="dataSource_stepComplete = true"
                                  v-on:invalidData="dataSource_stepComplete = false"
                                  v-on:dataSourceChanged="dataSource_stepComplete = false">
                </input-files-form>
            </md-step>
            <!--<md-step md-label="Analysis" md-message="Select one" :md-disabled="true" ref="analysis">-->
            <!--<p>Select your analysis: RNAseq, ChIPSeq</p>-->
            <!--</md-step>-->
            <md-step md-label="Describe samples" md-message="Pair those ends !"
                     :md-continue="describeSamples_stepComplete"
                     :md-disabled="!dataSource_stepComplete"
                     ref="describeSamples">
                <p>
                    Select samples from set to use, select pairs, add short sample
                    name and condition annotation</p>
                <p>Stranded/unstranded</p>
                <p>Reference genome</p>
            </md-step>
            <md-step md-label="Pipeline settings"
                     md-message="Use the defaults Luke !"
                     md-button-continue="Start job"
                     :md-continue="pipelineSettings_stepComplete"
                     :md-disabled="!describeSamples_stepComplete"
                     ref="pipelineSettings">
                <div class="placeholder">
                    <p><em>Damn yer wench, feed the sail. Ho-ho-ho! courage of grace.</em></p>
                </div>
                <p>Advanced</p>
            </md-step>
        </md-stepper>
    </div>
</template>


<script lang="ts">
    declare function require(path: string): any;

    import 'vue-material/dist/vue-material.css';

    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import Component from 'vue-class-component';
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator'
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
        dataSource_stepComplete: boolean = false;
        describeSamples_stepComplete: boolean = false;
        pipelineSettings_stepComplete: boolean = false;

//        enableStep() {
//            let refName = 'describeSamples';
//            (this.$refs[refName] as mdStep).mdActive = true;
//            console.log("Enabled step " + refName);
//
//            this.dataSource_stepComplete = true;
//        }
    }

</script>
