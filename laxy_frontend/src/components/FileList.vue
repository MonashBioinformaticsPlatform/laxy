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
                            <div class="no-line-break"><i class="md-caption">{{ file.path | magic_truncate }}</i></div>
                            <div class="no-line-break" :class="{ strikethrough: file.deleted }">{{ file.name | magic_truncate }}</div>
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
    import sortBy from "lodash-es/sortBy";

    import {Memoize, Debounce} from "lodash-decorators";

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

    // import {DummyFileSet as _dummyFileSet} from "../test-data";
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

        @Prop({default: 2, type: Number})
        public minQueryLength: number;

        @Prop(String)
        public jobId: string | null;

        @Prop({type: Boolean, default: true})
        public refreshOnLoad: boolean;

        public searchQuery: string = '';
        public searching: boolean = false;

        public actionRunning: any = {};

        get fileset(): any {
            // this appears reactive. reading directly
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
                    window.open(WebAPI.getExternalAppRedirectUrl('degust', file.id), '_blank');
                }
            },
        ];

        public refreshing: boolean = false;

        mounted() {
            // this.files = _dummyFileSet;
            // this.filesetId = _dummyFileSet.id;
            if (this.refreshOnLoad) this.refresh();
        }

        // we need this wrapped in a method otherwise the viewMethod.method
        // doesn't have the correct 'this' context to $emit events.
        emitActionError(msg: string) {
            this.$emit('action-error', msg);
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

        @Debounce(600)
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
                filtered = filterByFilename(filtered, query, false);
            }
            // const filtered = filter(this.fileset.files, (f) => {
            //     some(strToRegex(this.regexFilters), (p) => {f.name.matches(p)});
            // });
            filtered = sortBy(filtered, ['path', 'name']);
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
                if (this.filesetId && (force || this.fileset == null)) {
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
