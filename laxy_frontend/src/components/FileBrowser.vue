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
                                  <md-button class="md-icon-button" @click="file.checked = false;">
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
                                <md-checkbox v-model="file.checked"
                                             class="md-primary">
                                    &nbsp; {{ file.name }}
                                </md-checkbox>
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
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator'

    interface DataFile {
        id: string,
        name: string,
        checked: boolean,
        pair?: DataFile,
    }

    interface FileSet {
        id: string,
        name: string,
        files: Array<DataFile>,
        selected: boolean;
    }

//    interface FileBrowser extends Vue {
//        filesets: Array<FileSet>,
//        selected_fileset: FileSet,
//    }
    const dummyFileListOne: Array<DataFile> = [
        {
            id: '1rgerhfkejwrbf1',
            name: 'ChookSample1_R1.fastq.gz',
            checked: false
        },
        {
            id: '2rgerhfkejwrbf2',
            name: 'ChookSample1_R2.fastq.gz',
            checked: false
        },
        {
            id: '3rgerhfkejwrbf3',
            name: 'ChookSample2_R1.fastq.gz',
            checked: false
        },
        {
            id: '4rgerhfkejwrbf4',
            name: 'ChookSample2_R2.fastq.gz',
            checked: false
        },
    ];

    const dummyFileListTwo: Array<DataFile> = [
        {id: '1sdfa', name: 'XYZZY_1.fastq.gz', checked: false},
        {id: '2dfgdfg', name: 'XYZZY_2.fastq.gz', checked: false},

    ];

    const dummyFileListThree: Array<DataFile> = [
        {id: '1sdfwdf', name: 'Sample3_C_rep1_R1.fastq.gz', checked: false},
        {id: '2dffdgds', name: 'Sample3_C_rep1_R2.fastq.gz', checked: false},
        {id: '3dfgsefg', name: 'Sample4_C_rep2_R1.fastq.gz', checked: false},
        {id: '4dfsfhsf', name: 'Sample4_C_rep2_R2.fastq.gz', checked: false},
        {id: '5dfgsefg', name: 'Sample5_T_rep1_R1.fastq.gz', checked: false},
        {id: '6dfsfhsf', name: 'Sample5_T_rep1_R2.fastq.gz', checked: false},
        {id: '7dffjefg', name: 'Sample5_T_rep2_R1.fastq.gz', checked: false},
        {id: '8dfsfhsf', name: 'Sample5_T_rep2_R2.fastq.gz', checked: false},
    ];
    const dummyFileSetData: Array<FileSet> = [
        {
            id: "1dfbsegdfgvdrgasef",
            name: "Chicken Teeth RNAseq study",
            files: dummyFileListOne,
            selected: true,
        },
        {
            id: "2gewrgsrtgstrgergesfw",
            name: "Single replicate Unicorn transcriptome",
            files: dummyFileListTwo,
            selected: false,
        },
        {
            id: "3erwgresrtgsrtgwgwbt",
            name: "Sea Kelpie single cell",
            files: dummyFileListThree,
            selected: false,
        },
    ];

    @Component({props: {}})
    export default class FileBrowser extends Vue {

        filesets: Array<FileSet> = dummyFileSetData;
        selected_fileset: FileSet; // = dummyFileSetData[0];

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
                    if (f.checked) {
                        selected.push(f);
                    }
                }
            }

            return selected;
        }

        selectAll() {
            for (let file of this.selected_fileset.files) {
                file.checked = true;
            }
        }

        deselectAll() {
            for (let file of this.selected_fileset.files) {
                file.checked = false;
            }
        }
    };

</script>
