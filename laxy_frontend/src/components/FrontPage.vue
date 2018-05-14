<template>
    <div>
        <md-layout md-column md-gutter>
            <md-layout style="margin: 40px 10% 0 10%;"
                       md-vertical-align="stretch" md-column>
                <md-whiteframe md-elevation="2" class="pad-32">
                    <div class="pad-32">
                        <h1 class="md-display-2">Laxy &nbsp;&nbsp; <span class="md-subheading"><em>Genomics Pipelines for Humans</em></span>
                        </h1>
                        <md-boards :md-auto="true" :md-infinite="true" :md-duration="5000" :md-swipeable="true">
                            <md-board>
                                <div class="md-body-1">
                                    Laxy helps run analyses on genomic data.<br>
                                </div>
                            </md-board>
                            <md-board>
                                <div class="md-body-1">
                                    Give it your raw FASTQ reads and it will run an RNA-seq pipeline and allow you to
                                    explore the results.
                                </div>
                            </md-board>
                            <md-board>
                                <div class="md-body-1">FASTQ ⤇ Insight !<br></div>
                            </md-board>
                        </md-boards>

                    </div>
                    <md-layout>
                        <router-link to="/ENAflow">
                            <md-card md-with-hover id="rnaseq">
                                <md-card-header>
                                    <div class="md-title">RNA-Seq</div>
                                    <div class="md-subhead">using public data from ENA/SRA</div>
                                </md-card-header>

                                <md-card-content>
                                    <md-card-media>
                                        <md-layout md-align="center">
                                            <svg width="128px" height="64px"
                                                 viewBox="0 0 128 64">
                                                <rect x="0" y="0" width="32"
                                                      height="16"
                                                      style="fill: grey; stroke: black;"></rect>
                                                <rect x="42" y="0" width="32"
                                                      height="16"
                                                      style="fill: grey; stroke: black;"></rect>
                                                <rect x="24" y="20" width="32"
                                                      height="16"
                                                      style="fill: grey; stroke: black;"></rect>
                                                <rect x="64" y="20" width="32"
                                                      height="16"
                                                      style="fill: grey; stroke: black;"></rect>
                                                <rect x="0" y="40" width="120"
                                                      height="16"
                                                      style="fill: grey; stroke: black;"></rect>
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
                        </router-link>
                        <md-card md-with-hover id="chipseq">
                            <md-card-header>
                                <div class="md-title">ChIP-Seq</div>
                                <div class="md-subhead">using public data from ENA/SRA</div>
                            </md-card-header>

                            <md-card-content>
                                <md-card-media>
                                    <md-layout md-align="center">
                                        <svg width="128px" height="64px"
                                             viewBox="0 0 128 64">
                                            <rect x="0" y="0" width="32"
                                                  height="16"
                                                  style="fill: grey; stroke: black;"></rect>
                                            <rect x="42" y="0" width="32"
                                                  height="16"
                                                  style="fill: black; stroke: black; stroke-dasharray: 2;"></rect>
                                            <rect x="24" y="20" width="32"
                                                  height="16"
                                                  style="fill: grey; stroke: black;"></rect>
                                            <rect x="64" y="20" width="32"
                                                  height="16"
                                                  style="fill: grey; stroke: black;"></rect>
                                            <rect x="0" y="40" width="120"
                                                  height="16"
                                                  style="fill: grey; stroke: black;"></rect>
                                        </svg>
                                    </md-layout>
                                </md-card-media>
                                <br/>
                                <md-card-actions>
                                    <router-link tag="md-button"
                                                 disabled="true"
                                                 class="md-primary md-raised"
                                                 to="chipseq">
                                        Coming soon ...
                                    </router-link>
                                </md-card-actions>
                            </md-card-content>
                            <md-ink-ripple></md-ink-ripple>
                        </md-card>
                        <md-card md-with-hover id="variants">
                            <md-card-header>
                                <div class="md-title">Variant calls</div>
                                <div class="md-subhead">using public data from ENA/SRA</div>
                            </md-card-header>

                            <md-card-content>
                                <md-card-media>
                                    <md-layout md-align="center">
                                        <span class="md-title">
                                            T ⤇ C<br>
                                            G ⤇ A<br>
                                        </span>
                                    </md-layout>
                                </md-card-media>
                                <br/>
                                <md-card-actions>
                                    <router-link tag="md-button"
                                                 disabled="true"
                                                 class="md-primary md-raised"
                                                 to="variants">
                                        Coming soon ...
                                    </router-link>
                                </md-card-actions>
                            </md-card-content>
                            <md-ink-ripple></md-ink-ripple>
                        </md-card>
                    </md-layout>
                </md-whiteframe>
            </md-layout>
        </md-layout>
        <br/>
    </div>
</template>


<script lang="ts">
    import "vue-material/dist/vue-material.css";

    import * as _ from "lodash";
    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";

    const VueMaterial = require("vue-material");

    interface FrontPage extends Vue {
    }

    export default Vue.extend({
        components: {
            // 'input-files-form': InputFilesForm
        },
        props: {},
        data() {
            return {};
        },
        methods: {},
        computed: {},
        watch: {},
    });  // as ComponentOptions<RNASeqSetup>;

</script>
