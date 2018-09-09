<template>
    <md-layout>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <h3>Select a file</h3>

        <md-input-container>
            <label>From CSV</label>
            <md-file v-model="csv_file" :disabled="submitting"
                     @selected="submitCSV"></md-file>
        </md-input-container>

        Example format (Sample name, R1, R2):
        <pre>
                        SampleA,ftp://bla_lane1_R1.fastq.gz,ftp://bla_lane1_R2.fastq.gz
                        SampleA,ftp://bla_lane2_R1.fastq.gz,ftp://bla_lane2_R2.fastq.gz
                        SampleB,ftp://bla2_R1_001.fastq.gz,ftp://bla2_R2_001.fastq.gz
                               ,ftp://bla2_R1_002.fastq.gz,ftp://bla2_R2_002.fastq.gz
                        SampleC,ftp://foo2_lane4_1.fastq.gz,ftp://foo2_lane4_2.fastq.gz
                        SampleC,ftp://foo2_lane5_1.fastq.gz,ftp://foo2_lane5_2.fastq.gz
        </pre>
        Each row represents a biological replicate (sample + condition +
        biological replicate).
        Rows with identical sample names are considered technical
        replicates and may be merged for
        analysis.
        For single-end data, omit the R2 column.
        <md-snackbar md-position="bottom center" ref="snackbar"
                     :md-duration="snackbar_duration">
            <span>{{ snackbar_message }}</span>
            <md-button class="md-accent" @click="$refs.snackbar.close()">
                Dismiss
            </md-button>
        </md-snackbar>

    </md-layout>
</template>

<script lang="ts">
    import map from "lodash-es/map";
    import axios, {AxiosResponse} from "axios";

    import Vue from "vue";
    import Component from "vue-class-component";
    import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";

    import {Sample, SampleSet} from "../model";
    import {ADD_SAMPLES} from "../store";
    import {WebAPI} from "../web-api";

    interface IFormData {
        entries(): Array<any>; // Iterator<Array<any>>;

        append(name: string, value: string | Blob | File, fileName?: string): void;

        delete(name: string): void;

        get(name: string): FormDataEntryValue | null;

        getAll(name: string): FormDataEntryValue[];

        has(name: string): boolean;

        set(name: string, value: string | Blob | File, fileName?: string): void;
    }

    @Component({
        props: {showButtons: Boolean},
        filters: {},
    })
    export default class CSVSampleListUpload extends Vue {
        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;
        public csv_file: string = "";

        async submitCSV(filelist: FileList) {
            console.log(filelist);
            const file: File = filelist[0];
            const formData = new FormData() as IFormData;  // automatically uses 'content-type': 'multipart/form-data' in axios ?
            formData.append("name", file.name);
            formData.append("file", file, file.name);
            for (const k of formData.entries()) {
                console.log(`formData: {${k[0]}: ${k[1]}}`);
            }
            //const headers = {headers: {'content-type': 'multipart/form-data'}};
            try {
                this.submitting = true;
                const response = await WebAPI.createSampleset(formData) as AxiosResponse;
                // TODO: CSV upload doesn't append/merge, it aways creates a new SampleSet.
                //       Implement backend PATCH method so we can append/merge an uploaded CSV
                //       (or parse and merge CSV clientside - probably a bad idea since we really
                //        want to be able to validate CSV serverside before allowing it to be accepted)
                // let response = null;
                // if (this.samples.id == null) {
                //     const response = await WebAPI.fetcher.post("/api/v1/sampleset/", data) as AxiosResponse;
                //     this._samples.id = response.data.id;
                // } else {
                //     const response = await WebAPI.fetcher.patch(`/api/v1/sampleset/{this.samples.id}`, data) as AxiosResponse;
                // }
                this.submitting = false;
                this.flashSnackBarMessage("Saved !");
                // coerce JSON into a list of proper Sample objects, ensuring all properties are present
                const _samples: Sample[] = map(response.data.samples, (s) => {
                    return new Sample(s)
                });
                this.$store.commit(ADD_SAMPLES, _samples);
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                throw error;
            }
        }

        flashSnackBarMessage(msg: string, duration: number = 2000) {
            this.snackbar_message = msg;
            this.snackbar_duration = duration;
            (this.$refs.snackbar as any).open();
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }

    }
</script>
