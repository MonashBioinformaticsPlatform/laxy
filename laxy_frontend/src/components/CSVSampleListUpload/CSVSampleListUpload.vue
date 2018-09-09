<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>
        <md-layout md-column>
            <md-layout v-if="showAboutBox">
                <md-whiteframe md-elevation="5" style="padding: 16px; min-height: 100%; width: 100%;">
                    <slot name="about">
                        <CSVAboutBox></CSVAboutBox>
                    </slot>
                </md-whiteframe>
            </md-layout>
            <md-layout md-column>
                <h3>Select a file</h3>

                <md-input-container>
                    <label>From CSV</label>
                    <md-file v-model="csv_file" :disabled="submitting"
                             @selected="submitCSV"></md-file>
                </md-input-container>

                <md-snackbar md-position="bottom center" ref="snackbar"
                             :md-duration="snackbar_duration">
                    <span>{{ snackbar_message }}</span>
                    <md-button class="md-accent" @click="$refs.snackbar.close()">
                        Dismiss
                    </md-button>
                </md-snackbar>
            </md-layout>
        </md-layout>
    </div>
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

    import {Sample, SampleSet} from "../../model";
    import {ADD_SAMPLES} from "../../store";
    import {WebAPI} from "../../web-api";
    import CSVAboutBox from "./CSVAboutBox";

    @Component({
        components: {CSVAboutBox},
        props: {},
        filters: {},
    })
    export default class CSVSampleListUpload extends Vue {
        @Prop({default: true, type: Boolean})
        public showButtons: boolean;

        @Prop({default: true, type: Boolean})
        public showAboutBox: boolean;

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
