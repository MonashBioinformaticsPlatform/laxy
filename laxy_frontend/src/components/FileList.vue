<template>
    <div class="filelist">
        <md-progress v-if="refreshing || searching" md-indeterminate></md-progress>
        <md-layout v-if="!refreshing">
            <md-toolbar class="md-transparent fill-width">
                <h1 class="md-title">{{ titleText }}</h1>
                <md-input-container v-if="!hideSearch" md-clearable>
                    <md-input v-model="searchQuery" placeholder="Search"></md-input>
                    <md-icon v-if="!searchQuery">search</md-icon>
                </md-input-container>
            </md-toolbar>
            <md-table>
                <md-table-body>
                    <md-table-row v-for="file in files" :key="file.id">
                        <md-table-cell>
                            <div class="no-line-break"><i class="md-caption">{{ file.path | truncate }}</i></div>
                            <div class="no-line-break" :class="{ strikethrough: file.deleted }">{{ file.name | truncate }}</div>
                        </md-table-cell>
                        <md-table-cell md-numeric v-if="!file.deleted">
                            <!--<div class="push-right">-->
                            <md-spinner v-if="actionRunning[file.id]"
                                        :md-size="20"
                                        class="push-right"
                                        md-indeterminate></md-spinner>
                            <md-button v-else-if="getDefaultViewMethod(file)"
                                       class="md-icon-button push-right"
                                       @click="getDefaultViewMethod(file).method(file)">
                                <md-tooltip md-direction="top">
                                    {{ getDefaultViewMethod(file).text }}
                                </md-tooltip>
                                <md-icon>{{ getDefaultViewMethod(file).icon }}</md-icon>
                            </md-button>
                            <md-button v-else
                                       :disabled="true"
                                       class="md-icon-button">
                                <!-- empty placeholder button to preserve layout -->
                                <md-icon></md-icon>
                            </md-button>
                            <md-menu v-if="!actionRunning[file.id]" md-size="4">
                                <md-button class="md-icon-button push-right" md-menu-trigger>
                                    <md-icon>arrow_drop_down</md-icon>
                                </md-button>

                                <md-menu-content>
                                    <i class="md-caption" style="padding-left: 16px">{{ file.id }}</i>
                                    <!--  -->
                                    <md-menu-item v-for="view in getViewMethodsForTags(file.type_tags)"
                                                  :key="view.text"
                                                  @click="view.method(file)">
                                        <md-icon>{{ view.icon }}</md-icon>
                                        <span>{{ view.text }}</span>
                                    </md-menu-item>
                                </md-menu-content>
                            </md-menu>
                            <!--</div>-->
                        </md-table-cell>
                        <md-table-cell v-else="file.deleted">
                            <md-button class="md-icon-button push-right">
                                <md-tooltip md-direction="left">
                                    File has expired and is no longer available.
                                </md-tooltip>
                                <md-icon style="color: #bdbdbd;">info</md-icon>
                            </md-button>
                        </md-table-cell>
                    </md-table-row>
                    <md-table-row v-if="files.length === 0">
                        <md-table-cell>No files</md-table-cell>
                    </md-table-row>
                </md-table-body>
            </md-table>
        </md-layout>
    </div>
</template>


<script lang="ts">
    import "es6-promise";

    import filter from "lodash-es/filter";
    import map from "lodash-es/map";
    import head from "lodash-es/head";

    import {Memoize} from "lodash-decorators";
    // import Memoize from "lodash-decorators/Memoize";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
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

    import {ComputeJob, LaxyFile} from "../model";
    import {WebAPI} from "../web-api";
    import {FETCH_FILESET} from "../store";
    import {strToRegex} from "../util";
    import {
        hasSharedTagOrEmpty,
        hasIntersection,
        filterByTag,
        filterByRegex,
        filterByFullPath,
        filterByFilename,
        viewFile,
        downloadFile,
    } from "../file-tree-util";

    import {DummyFileSet as _dummyFileSet} from "../test-data";
    import {Snackbar} from "../snackbar";

    @Component({
        filters: {},
    })
    export default class FileList extends Vue {
        _DEBUG: boolean = false;

        @Prop(String)
        public filesetId: string;

        @Prop(String)
        public title: string;

        @Prop({
            type: Array, default: () => {
                return [];
            }
        })
        public regexFilters: string[];

        @Prop({
            type: Array, default: () => {
                return [];
            }
        })
        public tagFilters: string[];

        @Prop({default: true})
        public hideSearch: boolean;

        @Prop({default: 3, type: Number})
        public minQueryLength: number;

        @Prop(String)
        public jobId: string | null;

        @Prop({type: Boolean, default: true})
        public refreshOnLoad: boolean;

        // @Prop()
        // fileset: LaxyFileSet;

        // @State(state => state.filesets)
        // filesets: {[key:string]: LaxyFileSet};

        // fileset(filesetId: string | null = null): any {
        //     if (filesetId == null) {
        //         filesetId = this.filesetId;
        //     }
        //     return this.$store.getters.fileset(filesetId);
        // }

        public searchQuery: string = '';
        public searching: boolean = false;

        public actionRunning: any = {};

        get fileset(): any {
            // this appears reactive. reading directl
            return this.$store.getters.fileset(this.filesetId);
        }

        private viewMethods: ViewMethod[] = [
            {
                text: "Open in new tab",
                icon: "open_in_new",
                tags: [],
                method: (file_id: string) => {
                    viewFile(file_id, this.fileset, this.jobId);
                }
            },
            {
                text: "Download file",
                icon: "cloud_download",
                tags: [],
                method: (file_id: string) => {
                    downloadFile(file_id, this.fileset, this.jobId);
                }
            },
            {
                text: "View report",
                icon: "remove_red_eye",
                tags: ["html", "report"],
                method: (file_id: string) => {
                    viewFile(file_id, this.fileset, this.jobId);
                }
            },
            {
                text: "Open in Degust",
                icon: "dashboard",
                tags: ["degust"],
                method: async (file: LaxyFile) => {
                    // This won't work clientside due to CSRF tokens and Cross-Origin rules
                    // (Degust could provide a proper API and get friendly with
                    //  it's CORS config / headers to fix this)
                    //
                    // const url = 'http://degust.erc.monash.edu/upload'
                    // const file = this.$store.getters.fileById(this.fileset, file_id);
                    // const get_file_resp: AxiosResponse = await WebAPI.fetcher.get(
                    //     WebAPI.downloadFileByIdUrl(file_id));
                    // const file_content = get_file_resp.data;
                    // let form = new FormData();
                    // form.append('filename', file_content, 'counts.txt');
                    // const resp = await axios.post(url, form,
                    //     { headers: { 'Content-Type': 'multipart/form-data' } });
                    // window.open(resp.url);

                    // We POST the counts file to Degust serverside, then
                    // return the resulting '?code=' URL from Degust back
                    // to the client to open a new tab.
                    // Sadly needs popup whitelisting by the user.
                    this.actionRunning[file.id] = true;
                    Snackbar.flashMessage("Please wait - sometimes sending counts to Degust takes time.", 5000);
                    const url = `/api/v1/action/send-to/degust/${file.id}/`;
                    const resp = await WebAPI.fetcher.post(url);
                    if (resp.data.status == 200) {
                        window.open(resp.data.redirect);
                    } else {
                        console.error(`Failed sending to Degust`);
                        console.log(resp);
                    }
                    this.actionRunning[file.id] = false;
                }
            },
        ];

        public refreshing: boolean = false;

        mounted() {
            // this.files = _dummyFileSet;
            // this.filesetId = _dummyFileSet.id;
            if (this.refreshOnLoad) this.refresh();
        }

        getViewMethodsForTags(tags: string[]) {
            return filter(this.viewMethods,
                vm => hasSharedTagOrEmpty(vm.tags, tags));
        }

        @Memoize((file: LaxyFile) => file.id)
        getDefaultViewMethod(file: LaxyFile) {
            return head(filter(this.viewMethods,
                vm => hasIntersection(vm.tags, file.type_tags)));
        }

        get files(): LaxyFile[] {
            const fileset = this.fileset;
            if (fileset == null ||
                fileset.files == null ||
                fileset.files.length === 0) {
                return [];
            }

            let filtered: LaxyFile[] = fileset.files;
            filtered = filterByTag(filtered, this.tagFilters);
            filtered = filterByRegex(filtered, strToRegex(this.regexFilters));
            const query = this.searchQuery.trim();
            if (query.length >= this.minQueryLength) {
                filtered = filterByFilename(filtered, query);
            }
            // const filtered = filter(this.fileset.files, (f) => {
            //     some(strToRegex(this.regexFilters), (p) => {f.name.matches(p)});
            // });
            return filtered;
        }

        get titleText(): string {
            return this.title == null ? this.fileset.name : this.title;
        }

        async refresh(force: boolean = false) {
            if (this.refreshing && !force) return;

            try {
                // const response = await WebAPI.getFileSet(this.filesetId);
                // this.fileset = response.data as LaxyFileSet;
                if (force || this.fileset == null) {
                    this.refreshing = true;
                    await this.$store.dispatch(FETCH_FILESET, this.filesetId);
                    this.$emit("refresh-success", "Updated !");
                    this.refreshing = false;
                }
            } catch (error) {
                console.log(error);
                this.refreshing = false;
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

    .strikethrough {
        text-decoration-line: line-through;
    }
</style>
