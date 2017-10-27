<template>
    <div>
        <md-layout md-column>
            <md-layout md-column>
                <h2>Selected</h2>
                <md-whiteframe>
                    <div v-if="!selectedFiles" style="text-align: center">... <i>no files selected</i> ...</div>
                        <md-table>
                            <md-table-body>
                            <md-table-row v-for="file in selectedFiles" :key="file.id">
                                <md-table-cell class="has-ripple blue">
                                    <md-ink-ripple/>
                                    {{ file.name }}</md-table-cell>
                                <md-table-cell>
                                    <md-input-container>
                                        <md-select :name="file.id" v-model="file.pair">
                                        <md-option v-for="pairFile in selectedFiles"
                                                   :key="pairFile.id"
                                                   v-if="pairFile != file"
                                                   :value="pairFile.id"
                                                   id="pairFile.id">{{ pairFile.name }}
                                        </md-option>
                                        </md-select>
                                    </md-input-container>
                                </md-table-cell>
                                <md-table-cell>
                                <md-layout md-align="end">
                                  <md-button class="md-icon-button" @click="file.selected = false;">
                                  <md-icon>cancel</md-icon>
                                  <md-tooltip md-direction="top">Deselect all</md-tooltip>
                                </md-button>
                                </md-layout>
                                </md-table-cell>
                            </md-table-row>
                            </md-table-body>
                        </md-table>
                </md-whiteframe>
            </md-layout>
            <md-layout>
               <!-- <tree></tree> -->
                <ul id="demo">
                  <vue-tree-item
                    class="item"
                    :model="exampleTreeData">
                  </vue-tree-item>
                </ul>
            </md-layout>
            <md-layout md-gutter>
                <md-layout md-column md-flex="33">
                    <md-list class="md-dense" md-vertical-align="start">
                            <md-layout>
                              <h3>Project</h3>
                                <md-input-container>
                                    <!-- use: https://github.com/DannyFeliz/vue-js-search -->
                                    <md-input placeholder="Search (not implemented)"></md-input>
                                    <md-icon>search</md-icon>
                                </md-input-container>
                            </md-layout>
                            <!--<md-list-item v-for="fileset in filesets"-->
                            <!--:key="fileset.id">-->
                            <md-button @click="onSelectFileset(fileset);"
                                       class="md-raised md-dense"
                                       :class="{'md-primary': fileset.selected}"
                                       v-for="fileset in filesets"
                                       :key="fileset.id">
                                {{ fileset.name }}
                            </md-button>
                            <!--</md-list-item>-->
                    </md-list>

                </md-layout>
                <md-layout>
                    <div v-if="selected_fileset != null">
                        <md-list class="md-dense">
                            <md-layout md-column>
                              <h3>Files</h3>
                                <!-- <md-toolbar class="md-transparent"> -->
                                <md-whiteframe>
                                <md-button class="md-icon-button" @click="selectAll">
                                  <md-icon>select_all</md-icon>
                                  <md-tooltip md-direction="top">Select all</md-tooltip>
                                </md-button>
                                <md-button class="md-icon-button" @click="deselectAll">
                                  <md-icon>cancel</md-icon>
                                  <md-tooltip md-direction="top">Deselect all</md-tooltip>
                                </md-button>
                                </md-whiteframe>
                                <!-- </md-toolbar> -->
                            </md-layout>
                            <md-list-item v-for="file in selected_fileset.files"
                                          :key="file.id">
                                <md-checkbox v-model="file.selected"
                                             v-if="file.type == 'file'"
                                             class="md-primary">
                                    &nbsp;{{ file.name }}
                                </md-checkbox>
                                <div v-if="file.type == 'folder'">
                                    <md-icon class="md-primary">folder</md-icon><span class="folder-name">{{ file.name }}</span>
                                </div>
                            </md-list-item>
                        </md-list>
                    </div>
                    <div v-else>
                        .. no files ..
                    </div>
                </md-layout>
            </md-layout>
        </md-layout>
    </div>
</template>


<script lang="ts">
    declare function require(path: string): any;

    import 'vue-material/dist/vue-material.css';

    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import VueMaterial from 'vue-material';
    import Component from 'vue-class-component';
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator';

    import { TreeNode, DataFile, FileSet } from '../tree.ts';
    import * as dummy from '../dummyTreeData.ts';

    const exampleTreeData = {
        name: 'My Tree',
        children: [
            {name: 'hello'},
            {name: 'wat'},
            {
                name: 'child folder',
                children: [
                    {
                        name: 'child folder',
                        children: [
                            {name: 'hello'},
                            {name: 'wat'}
                        ]
                    },
                    {name: 'hello'},
                    {name: 'wat'},
                    {
                        name: 'child folder',
                        children: [
                            {name: 'hello'},
                            {name: 'wat'}
                        ]
                    }
                ]
            }
        ]
    };

    @Component({props: {}})
    export default class FileBrowser extends Vue {

        filesets: Array<FileSet> = dummy.fileSetData;
        selected_fileset: FileSet; // = dummy.fileSetData[0];
        exampleTreeData: object = dummy.nestedFileSet; // dummy.folderOne; // exampleTreeData;

        created() {
            this.onSelectFileset(this.filesets[0], null);
        }

        onSelectFileset(fileset: FileSet, old: FileSet | null) {
            if (fileset == null) return;

            for (let f of this.filesets) {
                (f as FileSet).selected = false;
            }
            (fileset as FileSet).selected = true;
            this.selected_fileset = fileset;
            // TODO: We shouldn't need this, but it seems required for the
            //       v-for over selected_fileset.files to re-render.
            this.$forceUpdate();
        }

        get selectedFiles() {
            const selected: Array<DataFile> = [];
            for (let fs of this.filesets) {
                for (let f of fs.files) {
                    if (f.selected) {
                        selected.push(f);
                    }
                }
            }

            return selected;
        }

        selectAll() {
            for (let file of this.selected_fileset.files) {
                file.selected = true;
            }
        }

        deselectAll() {
            for (let file of this.selected_fileset.files) {
                file.selected = false;
            }
        }
    };

</script>

<style>
    .folder-name {
        padding-left: 8px;
    }
</style>
