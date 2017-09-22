<template>
    <div>
        <md-stepper>
            <md-step md-label="Data source" :md-continue="false"
                     ref="dataSource">
                <input-files-form v-on:stepDone="enableStep"></input-files-form>
            </md-step>
            <!--<md-step md-label="Analysis" md-message="Select one" :md-disabled="true" ref="analysis">-->
            <!--<p>Select your analysis: RNAseq, ChIPSeq</p>-->
            <!--</md-step>-->
            <md-step md-label="Describe samples" md-message="Pair those ends !"
                     :md-disabled="true" ref="describeSamples">
                <p>
                    Select samples from set to use, select pairs, add short sample
                    name and condition annotation</p>
                <p>Stranded/unstranded</p>
                <p>Reference genome</p>
            </md-step>
            <md-step md-label="Pipeline settings"
                     md-message="Use the defaults Luke !"
                     md-button-continue="Start job"
                     :md-disabled="true" ref="pipelineSettings">
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
    import Vue, {ComponentOptions} from "vue";
    const VueMaterial = require('vue-material');

    // import InputFilesForm from 'InputFilesForm.vue';

    interface RNASeqSetup extends Vue {
    }

    interface mdStep extends Vue {
        mdActive: boolean;
    }

    export default Vue.extend({
        components: {
            // 'input-files-form': InputFilesForm
        },
        props: {},
        data() {
            return {}
        },
        methods: {
            enableStep() {
                let refName = 'describeSamples';
                (this.$refs[refName] as mdStep).mdActive = true;
                console.log("Enabled step " + refName);
            }
        },
        computed: {},
        watch: {},
    });  // as ComponentOptions<RNASeqSetup>;

</script>
