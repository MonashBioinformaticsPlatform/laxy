<template>
    <md-layout>
        <dalliance v-if="name && file && job && bamURI"
                   :name="name"
                   :bam-uri="bamURI"
                   :bai-uri="bamURI.replace(/\.bam$/, '.bai')"
                   :coord-system="coordSystem"
                   :chr="chromosome"
                   :view-start="viewStart"
                   :view-end="viewEnd">

        </dalliance>
    </md-layout>
</template>

<script lang="ts">
    import "vue-material/dist/vue-material.css";

    import * as _ from "lodash";
    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
    import VueMaterial from "vue-material";
    import Component from "vue-class-component";
    import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";

    import {
        State,
        Getter,
        Action,
        Mutation,
        namespace
    } from "vuex-class";

    import {Memoize, Once} from "lodash-decorators";

    import {FETCH_JOB} from "../store";
    import {WebAPI} from "../web-api";
    import {ComputeJob} from "../model";
    import Dalliance from "./Dalliance";

    @Component({
        components: {Dalliance},
        filters: {},
    })
    export default class BiodallianceView extends Vue {

        public file: any = {}; // LaxyFile;
        public job: any = {};  // ComputeJob;

        @Prop({type: String})
        public jobId: string;

        // @Prop({type: String})
        // public filesetId: string;

        @Prop({type: String})
        public fileId: string;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            this.getFile('', '');
            this.getJob('', '');
        }

        beforeMount() {

        }

        mounted() {

        }

        // @Watch('jobId', { immediate: true })
        async getJob(val: string, oldVal: string) {
            // return await this.$store.dispatch(FETCH_JOB, this.jobId);
            try {
                const response = await WebAPI.getJob(this.jobId);
                // this.$set(this, 'job', response.data as ComputeJob);
                this.job = response.data as ComputeJob;
            } catch (e) {
                console.error(e);
                throw e;
            }
        }

        // @Watch('fileId', { immediate: true })
        async getFile(val: string, oldVal: string) {
            try {
                const response = await WebAPI.getFileRecord(this.fileId);
                // this.$set(this, 'file', response.data as LaxyFile);
                this.file = response.data as LaxyFile;
            } catch (e) {
                console.error(e);
                throw e;
            }
        }

        get name() {
            return this.file.name;
        }

        get bamURI(): string {
            return WebAPI.viewJobFileByPathUrl(this.jobId,
                `${this.file.path}/${this.file.name}`);
        }

        get chromosome(): string {
            return "22";
        }

        get viewStart(): number {
            return 30000000;
        }

        get viewEnd(): number {
            return 30100000;
        }

        // TODO: Get this via job.params.params
        get coordSystem(): object {
            return {
                speciesName: "Mouse",
                taxon: 10090,
                auth: "GRCm",
                version: "38",
                ucscName: "mm10"
            };
        }
    }

</script>

<style scoped>

</style>
