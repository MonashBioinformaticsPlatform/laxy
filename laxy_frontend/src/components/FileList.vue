<template>
    <div class="filelist">
        <md-layout>
            <md-progress v-if="refreshing" md-indeterminate></md-progress>
            <md-layout v-if="!refreshing">
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
                                <div class="truncate-text"><i class="md-caption">{{ file.path }}</i></div>
                                <div class="truncate-text">{{ file.name }}</div>
                            </md-table-cell>
                            <md-table-cell md-numeric>
                                <!--<div class="push-right">-->
                                <md-button v-if="getDefaultViewMethod(file)"
                                           class="md-icon-button"
                                           @click="getDefaultViewMethod(file).method(file.id)">
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
                                <md-menu md-size="4">
                                    <md-button class="md-icon-button push-right" md-menu-trigger>
                                        <md-icon>arrow_drop_down</md-icon>
                                    </md-button>

                                    <md-menu-content>
                                        <i class="md-caption" style="padding-left: 16px">{{ file.id }}</i>
                                        <!--  -->
                                        <md-menu-item v-for="view in getViewMethodsForTags(file.type_tags)" :key="view.text"
                                                      @click="view.method(file.id)">
                                            <md-icon>{{ view.icon }}</md-icon>
                                            <span>{{ view.text }}</span>
                                        </md-menu-item>
                                    </md-menu-content>
                                </md-menu>
                                <!--</div>-->
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
    import { Memoize } from 'lodash-decorators';
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
    import {FETCH_FILESET} from "../store";

    import {DummyFileSet as _dummyFileSet} from "../test-data";

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
                    this.viewFile(file_id);
                }
            },
            {
                text: "Download file",
                icon: "cloud_download",
                tags: [],
                method: (file_id: string) => {
                    this.downloadFile(file_id);
                }
            },
            {
                text: "View report",
                icon: "remove_red_eye",
                tags: ['html', 'report'],
                method: (file_id: string) => {
                    this.viewFile(file_id);
                }
            },
            {
                text: "Open in Degust",
                icon: "dashboard",
                tags: ['counts', 'degust'],
                method: async (file_id: string) => {
                    // This won't work clientside due to CSRF tokens and Cross-Origin rules
                    // (Degust could provide a proper API and get friendly with
                    //  it's CORS config / headers to fix this)
                    //
                    // const url = 'http://degust.erc.monash.edu/upload'
                    // const file = this.fileById(file_id);
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
                    const url = `/api/v1/_action/send_to/degust/${file_id}/`;
                    const resp = await WebAPI.fetcher.post(url);
                    if (resp.data.status == 200) {
                        window.open(resp.data.redirect);
                    } else {
                        console.error(`Failed sending to Degust`);
                        console.log(resp);
                    }
                }
            },
            {
                text: "View genome",
                icon: "open_in_new",
                tags: ['bam'],
                method: (file_id: string) => {
                    window.open(this.getDallianceUrl(this.jobId, file_id));
                }
            },
        ];

        public refreshing: boolean = false;

        // for lodash in templates
        get _() {
            return _;
        }

        mounted() {
            // this.files = _dummyFileSet;
            // this.filesetId = _dummyFileSet.id;
            if (this.refreshOnLoad) this.refresh();
        }

        strToRegex(patterns: string[]): RegExp[] {
            if (!patterns) return [];
            return _.map(patterns, (p) => {
                return new RegExp(p);
            });
        }

        hasIntersection(a: any[] | null, b: any[] | null): boolean {
            if (a == null || b == null ||
                a.length === 0 || b.length === 0) return false;

            return _.some(a, i => b.includes(i));
        }

        hasSharedTagOrEmpty(viewMethodTags: any[], file_type_tags: any[]) {
            return viewMethodTags.length == 0 ||
                this.hasIntersection(viewMethodTags, file_type_tags);
        }

        getViewMethodsForTags(tags: string[]) {
            return _.filter(this.viewMethods,
                vm => this.hasSharedTagOrEmpty(vm.tags, tags))
        }

        @Memoize((file: LaxyFile) => file.id)
        getDefaultViewMethod(file: LaxyFile) {
            return _(this.viewMethods)
                .filter(vm => this.hasIntersection(vm.tags, file.type_tags))
                .first();
        }

        get regexPatterns(): RegExp[] {
            return this.strToRegex(this.regexFilters);
        }

        _filterByTag(files: LaxyFile[], tags: string[] | null): LaxyFile[] {
            if (tags == null || tags.length === 0) {
                return files;
            }
            const fileset = this.fileset;
            let tag_filtered: LaxyFile[] = [];
            for (let file of fileset.files) {
                for (let tag of tags) {
                    if (file.type_tags.includes(tag) &&
                        !tag_filtered.includes(file)) {
                        tag_filtered.push(file);
                    }
                }
            }

            return tag_filtered;
        }

        _filterByRegex(files: LaxyFile[], patterns: RegExp[] | null): LaxyFile[] {
            if (patterns == null || patterns.length === 0) {
                return files;
            }
            let regex_filtered: LaxyFile[] = [];
            for (let file of files) {
                for (let regex of patterns) {
                    if (regex.test(file.name) &&
                        !regex_filtered.includes(file)) {
                        regex_filtered.push(file);
                    }
                }
            }

            return regex_filtered;
        }

        get files(): LaxyFile[] {
            const fileset = this.fileset;
            if (fileset == null ||
                fileset.files == null ||
                fileset.files.length === 0) {
                return [];
            }

            let filtered: LaxyFile[] = fileset.files;
            filtered = this._filterByTag(filtered, this.tagFilters);
            filtered = this._filterByRegex(filtered, this.regexPatterns);

            // const filtered = _.filter(this.fileset.files, (f) => {
            //     _.some(this.regexPatterns, (p) => {f.name.matches(p)});
            // });
            return filtered;
        }

        get titleText(): string {
            return this.title == null ? this.fileset.name : this.title;
        }

        fileById(file_id: string): LaxyFile | undefined {
            const fileset = this.fileset;
            if (fileset == null) {
                return undefined;
            }
            return _.first(_.filter(fileset.files, (f) => {
                return f.id === file_id;
            }));
        }

        viewFile(file_id: string) {
            const file = this.fileById(file_id);
            if (file) {
                if (this.jobId) {
                    const filepath = `${file.path}/${file.name}`;
                    window.open(WebAPI.viewJobFileByPathUrl(this.jobId, filepath));
                } else {
                    // window.open(WebAPI.viewFileByIdUrl(file.id, file.name), '_blank');
                    window.open(WebAPI.viewFileByIdUrl(file.id, file.name));
                }
            } else {
                console.error(`Invalid file_id: ${file_id}`);
            }
        }

        downloadFile(file_id: string) {
            const file = this.fileById(file_id);
            if (file) {
                if (this.jobId) {
                    const filepath = `${file.path}/${file.name}`;
                    window.open(WebAPI.downloadJobFileByPathUrl(this.jobId, filepath));
                } else {
                    window.open(WebAPI.downloadFileByIdUrl(file.id, file.name));
                }
            } else {
                console.error(`Invalid file_id: ${file_id}`);
            }
        }

        getDallianceUrl(job_id: string | null, file_id: string): string {
            const a = document.createElement('a');
            a.href = this.$router.resolve(`/view/dalliance/${job_id}/${file_id}`).href;
            return `${a.protocol}//${a.host}${a.pathname}${a.search}${a.hash}`;
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

    .truncate-text {
        width: 600px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
