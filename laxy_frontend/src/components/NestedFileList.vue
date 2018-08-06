<template>
    <div class="filelist">
        <md-progress v-if="refreshing || searching" md-indeterminate></md-progress>
        <transition name="fade">
            <md-layout v-if="!refreshing">
                <md-toolbar class="md-transparent fill-width">
                    <h1 class="md-title">{{ titleText }}</h1>
                    <md-input-container v-if="!hideSearch" md-clearable>
                        <md-input v-model="searchQuery" placeholder="Search"></md-input>
                        <md-icon v-if="!searchQuery">search</md-icon>
                    </md-input-container>
                </md-toolbar>
                <md-toolbar class="md-transparent fill-width">
                    <div v-if="!searchQuery.trim()" class="breadcrumbs">
                        &nbsp;
                        <span v-for="node in pathToRoot">
                        <template v-if="node.id === '__root__'"><code>{{ rootPathName }} / </code></template>
                        <template v-else><code>{{ node.name }} / </code></template>
                    </span>
                        <br/>
                    </div>
                </md-toolbar>
                <md-table>
                    <md-table-body v-if="currentLevel">
                        <md-table-row v-if="currentLevel.parent" @click.native="upDirectory">
                            <md-table-cell>
                                <div class="push-left">
                                    <md-icon>folder_open</md-icon>&nbsp;..
                                </div>
                            </md-table-cell>
                            <md-table-cell md-numeric>
                                <md-button class="md-icon-button" :disabled="true">
                                    <!-- empty placeholder button to preserve layout -->
                                    <md-icon></md-icon>
                                </md-button>
                                <md-button class="md-icon-button push-right" :disabled="true">
                                    <md-icon>subdirectory_arrow_left</md-icon>
                                </md-button>
                            </md-table-cell>
                        </md-table-row>
                        <md-table-row v-for="node in currentLevelNodes" :key="node.id">
                            <template v-if="node.file">
                                <md-table-cell>
                                    <div class="truncate-text">{{ node.file.name }}</div>
                                </md-table-cell>
                                <md-table-cell md-numeric>
                                    <!--<div class="push-right">-->
                                    <md-button v-if="getDefaultViewMethod(node.file)"
                                               class="md-icon-button"
                                               @click="getDefaultViewMethod(node.file).method(node.file)">
                                        <md-tooltip md-direction="top">
                                            {{ getDefaultViewMethod(node.file).text }}
                                        </md-tooltip>
                                        <md-icon>{{ getDefaultViewMethod(node.file).icon }}</md-icon>
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
                                            <i class="md-caption" style="padding-left: 16px">{{ node.file.id }}</i>
                                            <!--  -->
                                            <md-menu-item
                                                    v-for="view in getViewMethodsForTags(node.file.type_tags)"
                                                    :key="view.text"
                                                    @click="view.method(node.file.id)">
                                                <md-icon>{{ view.icon }}</md-icon>
                                                <span>{{ view.text }}</span>
                                            </md-menu-item>
                                        </md-menu-content>
                                    </md-menu>
                                    <!--</div>-->
                                </md-table-cell>
                            </template>
                            <template v-else>
                                <!-- it's a directory, not a file -->
                                <md-table-cell @click.native="enterDirectory(node)">
                                    <div class="truncate-text">
                                        <md-icon>folder</md-icon>&nbsp;{{ node.name }}
                                    </div>
                                </md-table-cell>
                                <md-table-cell md-numeric @click.native="enterDirectory(node)">
                                    <md-button class="md-icon-button push-right" :disabled="true">
                                        <!-- <md-icon>subdirectory_arrow_right</md-icon> -->
                                        <!-- empty placeholder button to preserve layout -->
                                        <md-icon></md-icon>
                                    </md-button>
                                </md-table-cell>
                            </template>
                        </md-table-row>
                        <md-table-row v-if="currentLevel.children === 0">
                            <md-table-cell>No files</md-table-cell>
                        </md-table-row>
                    </md-table-body>
                </md-table>
            </md-layout>
        </transition>
    </div>
</template>

<script lang="ts">
    import "vue-material/dist/vue-material.css";

    // import * as _ from "lodash";

    import filter from "lodash-es/filter";
    import map from "lodash-es/map";
    import head from "lodash-es/head";
    import sortBy from "lodash-es/sortBy";
    import flatten from "lodash-es/flatten";
    import flatMapDeep from "lodash-es/flatMapDeep";

    import Memoize from "lodash-decorators/Memoize";
    import Debounce from "lodash-decorators/Debounce";

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
        viewFile,
        downloadFile,
        fileListToTree,
        flattenTree,
        TreeNode,
    } from "../file-tree-util";

    import {DummyFileSet as _dummyFileSet} from "../test-data";

    @Component({
        filters: {},
    })
    export default class NestedFileList extends Vue {
        _DEBUG: boolean = false;

        @Prop()
        public fileList: LaxyFile[];

        @Prop({type: String, default: ""})
        public rootPathName: string;

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

        public searchQuery: string = "";
        public searching: boolean = false;

        @Watch("fileTree")
        initCurrentLevel(new_val: TreeNode, old_value: TreeNode) {
            this.currentLevel = this.fileTree;
        }

        public currentLevel: TreeNode | null = null;

        @Debounce(1000)
        get searchFilteredNodes(): TreeNode[] {
            const query = this.searchQuery.trim();

            const nodes = flattenTree(this.fileTree.children);

            if (!query || query.length === 0) return nodes;

            const hits = filter(nodes,
                (node) => {
                    if (node.file) {
                        return `${node.file.name}/${node.file.name}`.includes(query);
                        // TODO: Make globbing work, or look at vuex-search
                        // return minimatch(`${node.file.name}/${node.file.name}`, query);
                    } else {
                        return node.name.includes(query);
                        // TODO: Make globbing work, or look at vuex-search
                        // return minimatch(node.name, query);
                    }
                });
            return hits;
        }

        get currentLevelNodes(): TreeNode[] {
            if (this.currentLevel) {
                let nodes = this.currentLevel.children;
                const query = this.searchQuery.trim();
                if (query.length >= this.minQueryLength) {
                    this.searching = true;
                    nodes = this.searchFilteredNodes;
                    this.searching = false;
                }
                return sortBy(nodes,
                    [
                        (n: TreeNode) => n.file != null,
                        "name"
                    ]);
            }
            return [];
        }

        get pathToRoot(): TreeNode[] {
            if (this.currentLevel) {
                let parent = this.currentLevel.parent;
                let nodes: TreeNode[] = [this.currentLevel];
                while (parent != null) {
                    if (parent.name) nodes.push(parent);
                    parent = parent.parent;
                }
                nodes.reverse();
                return nodes;
            }
            return [];
        }

        private _emptyTreeRoot: TreeNode = {
            id: "__root__",
            name: "/",
            file: null,
            parent: null,
            children: [],
        } as TreeNode;

        get fileTree(): TreeNode {
            if (this.files) {
                return fileListToTree(this.files);
            } else {
                return this._emptyTreeRoot;
            }
        }

        get currentLevelFiles(): (LaxyFile | null)[] {
            if (this.currentLevel) {
                return map(sortBy(this.currentLevel.children, ["name"]),
                    (node) => node.file);
            }
            return [];
        }

        upDirectory(): TreeNode | null {
            if (this.currentLevel && this.currentLevel.parent) {
                this.currentLevel = this.currentLevel.parent;
            }
            this.searchQuery = '';
            return this.currentLevel;
        }

        enterDirectory(node: TreeNode) {
            this.searchQuery = '';
            this.currentLevel = node;
        }

        private viewMethods: ViewMethod[] = [
            {
                text: "Open in new tab",
                icon: "open_in_new",
                tags: [],
                method: (file: LaxyFile) => {
                    viewFile(file, null, this.jobId);
                }
            },
            {
                text: "Download file",
                icon: "cloud_download",
                tags: [],
                method: (file: LaxyFile) => {
                    downloadFile(file, null, this.jobId);
                }
            },
            {
                text: "View report",
                icon: "remove_red_eye",
                tags: ["html", "report"],
                method: (file: LaxyFile) => {
                    viewFile(file, null, this.jobId);
                }
            },
            {
                text: "Open in Degust",
                icon: "dashboard",
                tags: ["counts", "degust"],
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
                    const url = `/api/v1/_action/send_to/degust/${file.id}/`;
                    const resp = await WebAPI.fetcher.post(url);
                    if (resp.data.status == 200) {
                        window.open(resp.data.redirect);
                    } else {
                        console.error(`Failed sending to Degust`);
                        console.log(resp);
                    }
                }
            },
        ];

        public refreshing: boolean = false;

        mounted() {
            // this.fileList = _dummyFileSet.files;
            // this.filesetId = _dummyFileSet.id;
            //this.currentLevel = this.fileTree[4];
            this.currentLevel = this.fileTree;
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
            let filtered: LaxyFile[] = this.fileList;
            filtered = filterByTag(filtered, this.tagFilters);
            filtered = filterByRegex(filtered, strToRegex(this.regexFilters));
            return filtered;
        }

        get titleText(): string {
            return this.title;
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
