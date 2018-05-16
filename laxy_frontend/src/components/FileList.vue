<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-layout md-gutter>
                <md-layout>
                    <md-spinner v-if="submitting" md-indeterminate></md-spinner>
                    <md-table-card v-if="!submitting">
                        <md-toolbar>
                            <h1 class="md-title">{{ titleText }}</h1>
                            <md-button v-if="!hideSearch" class="md-icon-button">
                                <md-icon>search</md-icon>
                            </md-button>
                        </md-toolbar>
                        <md-table>
                            <md-table-body>
                                <md-table-row v-for="file in files" :key="file.id">
                                    <md-table-cell>{{ file.name }}</md-table-cell>
                                    <md-table-cell>
                                        <md-button class="md-icon-button"
                                                   @click="viewFile(file.id)">
                                            <md-tooltip md-direction="top">View</md-tooltip>
                                            <md-icon>pageview</md-icon>
                                        </md-button>
                                    </md-table-cell>
                                </md-table-row>
                            </md-table-body>
                        </md-table>
                    </md-table-card>
                </md-layout>
            </md-layout>
        </md-layout>
        <md-snackbar md-position="bottom center" ref="snackbar"
                     :md-duration="snackbar_duration">
            <span>{{ snackbar_message }}</span>
            <md-button class="md-accent" @click="$refs.snackbar.close()">
                Dismiss
            </md-button>
        </md-snackbar>
    </div>
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

    import {ComputeJob} from "../model";
    import {WebAPI} from "../web-api";

    import {DummyFileSet as _dummyFileSet} from "../test-data";

    @Component({
        props: {
            filesetId: String,
            title: String,
            regexFilters: Array,
            hideSearch: Boolean,
        },
        filters: {},
    })
    export default class FileList extends Vue {
        _DEBUG: boolean = false;

        public filesetId: string;
        public title: string;
        public fileset: any = {};
        public regexFilters: string[];
        public hideSearch: boolean;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            // this.files = _dummyFileSet;
            // this.filesetId = _dummyFileSet.id;
            this.refresh();
        }

        get patterns(): RegExp[] {
            if (!this.regexFilters) return [];
            return _.map(this.regexFilters, (p) => {
                return new RegExp(p);
            });
        }

        get files(): any[] {
            if (!this.fileset || !this.fileset.files) {
                return [];
            }
            if (!this.regexFilters) {
                return this.fileset.files;
            }

            let filtered = [];
            for (let file of this.fileset.files) {
                for (let regex of this.patterns) {
                    if (regex.test(file.name)) {
                        filtered.push(file);
                    }
                }
            }

            // const filtered = _.filter(this.fileset.files, (f) => {
            //     _.some(this.patterns, (p) => {f.name.matches(p)});
            // });
            return filtered;
        }

        get titleText(): string {
            return this.title == null ? this.fileset.name : this.title;
        }

        viewFile(file_id: string) {
            const file = _.first(_.filter(this.fileset.files, (f) => {
                return f.id === file_id;
            }));
            this.error_alert_message = `Not implemented (yet!)<br><pre>${JSON.stringify(file, null, 2)}</pre>`;
            this.openDialog("error_dialog");
        }

        async refresh() {
            try {
                this.submitting = true;
                const response = await WebAPI.getFileSet(this.filesetId);
                this.fileset = response.data;
                this.submitting = false;
                // this.flashSnackBarMessage("Updated", 500);
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                throw error;
            }
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }

        flashSnackBarMessage(msg: string, duration: number = 2000) {
            this.snackbar_message = msg;
            this.snackbar_duration = duration;
            (this.$refs.snackbar as any).open();
        }
    };

</script>

<style scoped>
    .md-table-card {
        width: 100%;
    }
</style>
