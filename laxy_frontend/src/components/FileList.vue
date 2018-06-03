<template>
    <div class="filelist">
        <md-layout>
            <md-spinner v-if="submitting" md-indeterminate></md-spinner>
            <md-layout v-if="!submitting">
                <md-toolbar class="md-transparent fill-width">
                    <h1 class="md-title">{{ titleText }}</h1>
                    <md-button v-if="!hideSearch" class="md-icon-button push-right">
                        <md-icon>search</md-icon>
                    </md-button>
                </md-toolbar>
                <md-table>
                    <md-table-body>
                        <md-table-row v-for="file in files" :key="file.id">
                            <md-table-cell>
                                <div class="truncate-text">{{ file.name }}</div>
                            </md-table-cell>
                            <md-table-cell>
                                <div class="push-right">
                                    <md-button class="md-icon-button"
                                               @click="viewFile(file.id)">
                                        <md-tooltip md-direction="top">View</md-tooltip>
                                        <md-icon>remove_red_eye</md-icon>
                                    </md-button>
                                    <md-menu md-size="4">
                                        <md-button class="md-icon-button push-right" md-menu-trigger>
                                            <md-icon>arrow_drop_down</md-icon>
                                        </md-button>

                                        <md-menu-content>
                                            <md-menu-item v-for="view in viewMethods" :key="view.text"
                                                          @click="view.method(file.id)">
                                                <md-icon>{{ view.icon }}</md-icon>
                                                <span>{{ view.text }}</span>
                                            </md-menu-item>
                                        </md-menu-content>
                                    </md-menu>
                                </div>
                            </md-table-cell>
                        </md-table-row>
                        <md-table-row v-if="files.length === 0">
                            <md-table-cell>No files</md-table-cell>
                        </md-table-row>
                    </md-table-body>
                </md-table>
            </md-layout>
        </md-layout>
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
        public fileset: LaxyFileSet;
        public regexFilters: string[];
        public hideSearch: boolean;

        private viewMethods = [
            {
                text: "Open in new tab",
                icon: "open_in_new",
                method: (file_id: string) => { this.viewFile(file_id) }
            },
            {
                text: "Download file",
                icon: "cloud_download",
                method: (file_id: string) => { this.downloadFile(file_id) }
            },
        ];

        public submitting: boolean = false;

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

        fileById(file_id: string): LaxyFile | undefined {
            if (this.fileset == null) {
                return undefined;
            }
            return _.first(_.filter(this.fileset.files, (f) => {
                return f.id === file_id;
            }));
        }

        viewFile(file_id: string) {
            const file = this.fileById(file_id);
            if (file) {
                // window.open(WebAPI.viewFileUrl(file.id, file.name), '_blank');
                window.open(WebAPI.viewFileUrl(file.id, file.name));
            } else {
                console.error(`Invalid file_id: ${file_id}`);
            }
        }

        downloadFile(file_id: string) {
            const file = this.fileById(file_id);
            if (file) {
                window.open(WebAPI.downloadFileUrl(file.id, file.name));
            } else {
                console.error(`Invalid file_id: ${file_id}`);
            }
        }

        async refresh() {
            try {
                this.submitting = true;
                const response = await WebAPI.getFileSet(this.filesetId);
                this.fileset = response.data as LaxyFileSet;
                this.submitting = false;
                this.$emit("refresh-success", "Updated !");
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.$emit("refresh-error", error.toString() + ` (filesetId: ${this.filesetId})`);
                throw error;
            }
        }
    };

</script>

<style scoped>
    /*.md-table-card {*/
    /*width: 100%;*/
    /*}*/

    .truncate-text {
        width: 600px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
