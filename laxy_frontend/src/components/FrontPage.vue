<template>
    <div>
        <md-layout md-column md-gutter>
            <md-layout style="margin: 40px 10% 0 10%;"
                       md-vertical-align="stretch" md-column>

                <h1>Laxy Genomics Pipelines</h1>
                <span class="md-subheading"><em>All your reads belong to us</em></span>
                <hr>
                <div class="md-body-1">
                    This is a web application for running analysis on genomic data.
                    It will run an RNA-seq pipeline, but you'll still need some kind of bioinformatician.
                    <div class="placeholder">
                        <em>The disconnection is a strange space suit. Why does the green people tremble?
                            Klingons are the transporters of the crazy honor. The green people is proudly sub-light.
                            Bravely translate a space suit. It is a gravimetric honor, sir. Why does the collective die?</em>
                    </div>
                </div>
                <hr>
                <md-layout md-flex="20">
                    <md-card md-with-hover>
                        <md-card-header>
                            <div class="md-title">RNA-Seq</div>
                            <div class="md-subhead">with RNAsik</div>
                        </md-card-header>

                        <md-card-content>
                            <md-card-media>
                                <md-layout md-align="center">
                                    <svg width="128px" height="64px"
                                         viewBox="0 0 128 64">
                                        <rect x="0" y="0" width="32"
                                              height="16"
                                              style="fill: grey; stroke: black;"/>
                                        <rect x="42" y="0" width="32"
                                              height="16"
                                              style="fill: grey; stroke: black;"/>
                                        <rect x="24" y="20" width="32"
                                              height="16"
                                              style="fill: grey; stroke: black;"/>
                                        <rect x="64" y="20" width="32"
                                              height="16"
                                              style="fill: grey; stroke: black;"/>
                                        <rect x="0" y="40" width="120"
                                              height="16"
                                              style="fill: grey; stroke: black;"/>
                                    </svg>
                                </md-layout>
                            </md-card-media>
                            <br/>
                            <md-card-actions>
                                <router-link tag="md-button"
                                             class="md-primary md-raised"
                                             to="rnaseq">
                                    Run an RNA-Seq analysis
                                </router-link>
                            </md-card-actions>
                        </md-card-content>
                        <md-ink-ripple></md-ink-ripple>
                    </md-card>
                </md-layout>
            </md-layout>
        </md-layout>
        <br/>
    </div>
</template>


<script lang="ts">
    declare function require(path: string): any;

    import 'vue-material/dist/vue-material.css';

    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from "vue";
    const VueMaterial = require('vue-material');

    interface FrontPage extends Vue {
    }

    export default Vue.extend({
        components: {
            // 'input-files-form': InputFilesForm
        },
        props: {},
        data() {
            return {}
        },
        methods: {},
        computed: {},
        watch: {},
    });  // as ComponentOptions<RNASeqSetup>;

</script>
