<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-layout md-column>
            <md-layout v-if="showAboutBox">
                <md-whiteframe md-elevation="5" style="padding: 16px; min-height: 100%; width: 100%;">
                    <slot name="about">
                        <RemoteFileSelectAboutBox></RemoteFileSelectAboutBox>
                    </slot>
                </md-whiteframe>
            </md-layout>
            <md-layout md-column>
                <form @submit.stop.prevent="submitUrl(url)">
                    <md-input-container>
                        <label>URL
                            <span>
                                <md-icon style="font-size: 16px;">info</md-icon>
                                <md-tooltip md-direction="right">
                                    A page with links to your files, or a direct link to a TAR file.
                                </md-tooltip>
                            </span>
                        </label>
                        <md-input v-model="url"
                                  placeholder="https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/">
                        </md-input>
                        <md-button class="md-icon-button"
                                   @click="submitUrl(url)">
                            <md-icon type="submit">search</md-icon>
                        </md-button>
                    </md-input-container>
                </form>
            </md-layout>
            <md-layout v-if="submitting">
                <md-progress md-indeterminate></md-progress>
            </md-layout>
            <md-layout md-gutter>
                <md-layout v-if="!hasResults"
                           md-flex-large="75" md-flex-small="100">
                    <!-- no results -->
                </md-layout>
                <md-layout v-else
                           md-flex-large="75" md-flex-small="100">
                    <nested-file-list
                            v-if="listing && listing.length > 0"
                            id="remote-files-list"
                            class="fill-width"
                            ref="remote-files-list"
                            title="Links"
                            root-path-name=""
                            :fileTree="fileTree"
                            :hide-search="false"
                            :hide-actions="true"
                            :show-back-arrow="false"
                            :auto-select-pair="true"
                            search-box-placeholder="Filter"
                            @select="onSelect"
                            @refresh-error="showErrorDialog"
                            @back-button-clicked="listLinks(previousUrl)">

                        <span slot="breadcrumbs">
                            &nbsp;<code><a :href="navigatedUrl" target="_blank">{{ navigatedUrl }}</a></code>
                        </span>

                    </nested-file-list>
                </md-layout>
            </md-layout>
        </md-layout>
        <md-layout v-if="showButtons" md-gutter>
            <md-button @click="addToCart"
                       :disabled="submitting || selectedFiles.length === 0"
                       class="md-raised">Add to cart
            </md-button>
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

    import map from "lodash-es/map";
    import filter from "lodash-es/filter";

    import "es6-promise";

    import * as pluralize from "pluralize";
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

    import VueMarkdown from 'vue-markdown';

    import RemoteFileSelectAboutBox from "./RemoteFileSelectAboutBox";
    import FileList from "../FileList";
    import NestedFileList from "../NestedFileList";
    import {LaxyFile, Sample} from "../../model";
    import {ADD_SAMPLES} from "../../store";
    import {WebAPI} from "../../web-api";

    import {ENADummySampleList as _dummysampleList} from "../../test-data";
    import {
        EMPTY_TREE_ROOT, FileListItem,
        fileListToTree,
        findPair,
        flattenTree, is_archive_url, objListToTree,
        simplifyFastqName,
        TreeNode
    } from "../../file-tree-util";
    import {Snackbar} from "../../snackbar";

    import {longestCommonPrefix} from "../../prefix";
    import {escapeRegExp, reverseString} from "../../util";

    interface DbAccession {
        accession: string;
    }

    @Component({
        components: {
            RemoteFileSelectAboutBox,
            VueMarkdown,
            FileList,
            NestedFileList
        },
        props: {},
        filters: {}
    })
    export default class RemoteFileSelect extends Vue {
        @Prop({default: true, type: Boolean})
        public showButtons: boolean;

        @Prop({default: true, type: Boolean})
        public showAboutBox: boolean;

        public url: string = "";
        public initialUrl: string = "";  // the URL initially submitted to the form, for tracking navigation state
        public navigatedUrl: string = "";
        public previousUrl: string = "";
        public listing: Array<any> = [];

        public selectedFiles: any[] = [];

        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine.";

        created() {

        }

        get fileTree(): TreeNode<FileListItem> {
            // This file tree isn't actually a tree, but a single (non-nested) list of children on the root node.
            // This allows us to re-use the NestedFileList component.
            // Directory nodes are given 'meta.onclick' callbacks that trigger retrieving their remote listing, and
            // resulting in an update of this item listing.
            if (this.listing) {
                // Turn the list of items into a (single level) TreeNode object
                const tree = objListToTree<FileListItem>(
                    this.listing,
                    (i: FileListItem) => {
                        return [i.name];
                    },
                    (i: FileListItem) => {
                        return i.name;
                    });
                // const tree = fileListToTree<FileListItem>(this.listing);
                for (let node of tree.children) {
                    const item = node.obj as FileListItem;
                    node.meta.type = item.type;
                    node.meta.tags = item.tags;
                    // add onclick callbacks to directory and archive nodes
                    if (item && (item.type === 'directory' || item.tags.includes('archive'))) {
                        node.meta.onclick = () => this.listLinks(item.location);
                    }
                }
                return tree;
            } else {
                return EMPTY_TREE_ROOT;
            }
        }

        get hasResults() {
            return !(this.listing == null || this.listing.length === 0);
        }

        urlIsParentPath(longurl: string, shorturl: string): boolean {
            return longurl.length > shorturl.length && longurl.indexOf(shorturl) === 0;
        }

        onSelect(rows: any) {
            console.log(rows);
            // const fileList = this.$refs['remote-files-list'] as NestedFileList;
            // if (fileList) {
            //     this.selectedFiles = fileList.selectedFiles;
            // }
            this.selectedFiles = filter(rows, {type: 'file'});
        }

        remove(rows: LaxyFile[]) {
            for (const row of rows) {
                const i = this.listing.indexOf(row);
                this.listing.splice(i, 1);
            }
        }

        addToCart() {
            // console.log(this.selectedFiles);
            const cart_samples: Sample[] = [];
            const added_files: LaxyFile[] = [];

            const names: string[] = map(this.selectedFiles, (i) => {
                return reverseString(simplifyFastqName(i.name));
            });
            // console.dir(names);
            // actually longest common SUFFIX of (simplified) file names, since we reversed names above
            const lcp = longestCommonPrefix(names);
            // console.dir(lcp);
            const commonSuffix = lcp.length > 0 ? reverseString(lcp) : '';
            // console.dir(commonSuffix);

            for (let f of this.selectedFiles) {
                if (f.name === '..') {
                    continue;
                }
                if (added_files.includes(f)) continue;
                const pair = findPair(f, this.selectedFiles);

                let sname = f.name;
                if (pair != null) {
                    sname = simplifyFastqName(f.name);
                }
                sname = sname.replace(commonSuffix, '');
                if (sname === '') sname = commonSuffix;
                let sfiles: any = [{R1: f}];
                if (pair != null) {
                    sfiles = [{R1: f, R2: pair}];
                }
                cart_samples.push({
                    name: sname,
                    files: sfiles,
                    metadata: {condition: ""},
                } as Sample);
                added_files.push(f);
                if (pair != null) added_files.push(pair);
            }
            this.$store.commit(ADD_SAMPLES, cart_samples);
            let count = this.selectedFiles.length;
            Snackbar.flashMessage(`Added ${count} ${pluralize("file", count)} to cart.`);

            //this.remove(this.selectedFiles);
            //this.selectedFiles = [];
        }

        // rowHover(row: any) {
        //     this.hoveredSampleDetails = row;
        //     // console.log(row);
        // }

        async submitUrl(url: string) {
            url = url.trim();
            this.url = url;
            this.initialUrl = url;
            await this.listLinks(url);
        }

        async listLinks(url: string) {
            this.listing = [];
            try {
                this.submitting = true;
                const response = await WebAPI.remoteFilesList(url);
                this.submitting = false;
                this.previousUrl = `${this.navigatedUrl}`;
                this.navigatedUrl = url;
                this.populateSelectionList(response.data);
            } catch (error) {
                console.log(error);
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
                this.submitting = false;
            }
        }

        populateSelectionList(data: any) {
            // console.dir(data);
            this.listing = [];
            if (is_archive_url(this.navigatedUrl)) {
                // add a '..' entry to navigate out of TAR archive
                const parts = this.navigatedUrl.split('/');
                const archive_name = parts.pop();
                const parentDir = parts.join('/');
                this.listing.push({
                    location: parentDir,
                    name: '..',
                    type: 'directory',
                    tags: [],
                } as FileListItem)
            }
            for (let f of data['listing']) {
                if (f.type === 'directory') {

                    // don't allow navigation down the tree below the initially submitted URL
                    if (this.urlIsParentPath(this.initialUrl, f.location)) {
                        continue;
                    }

                    // rename URLs that lead down toward the base of the tree
                    if (this.urlIsParentPath(this.navigatedUrl, f.location)) {
                        f.name = '..';
                        // or skip them ?
                        // continue;
                    }

                    if (f.meta === undefined) f.meta = {};
                    f.meta.onclick = () => this.listLinks(f['location']);
                }
                this.listing.push(f);
            }
            // console.log(data['archives']);
        }

        showErrorDialog(message: string) {
            this.error_alert_message = message;
            this.openDialog("error_dialog");
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }
    };

</script>

<style lang="css" scoped>

</style>
