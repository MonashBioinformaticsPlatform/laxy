<template>
    <div>
        <div id="svgHolder"></div>
    </div>
</template>

<script lang="ts">
    /*

    TODO: For dalliance-vue

     * Start using the NPM package when there is a one available
       (https://github.com/dasmoth/dalliance/issues/237)
     * Fix BAM/BAI fetching - seems that withCredentials isn't being properly
       set for BAM XMLHttpRequest's since I never see Cookies on .bam requests,
       fails with 401 Unauthorized.

     Tips to get this going as a Vue component gleaned from: https://github.com/dasmoth/headless-biodalliance

     */
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

    import {Debounce} from 'lodash-decorators';

    import {WebAPI} from "../web-api";

    const dalliance = require("dalliance");
    //const dalliance = require('../dalliance-all.js');
    // import * as dalliance from '../dalliance-all';
    //import {Browser} from '../dalliance-all';


    @Component({
        filters: {},
    })
    export default class Dalliance extends Vue {

        @Prop({type: String, default: ""})
        public name: string;

        @Prop({type: String})
        public bamUri: string;

        @Prop({type: String})
        public baiUri: string;

        @Prop({type: String, default: "22"})
        public chr: string;

        @Prop({type: Number, default: 30000000})
        public viewStart: string;

        @Prop({type: Number, default: 30100000})
        public viewEnd: string;

        @Prop({
            type: Object,
            default: {
                speciesName: "Mouse",
                taxon: 10090,
                auth: "GRCm",
                version: "38",
                ucscName: "mm10"
            }
        })
        public coordSystem: object;

        // for lodash in templates
        get _() {
            return _;
        }

        created() {

        }

        //@Debounce(200)
        //beforeUpdate() {
        mounted() {
            const browser = new dalliance.Browser({
                credentials: true,  // boolean passed to XMLHttpRequest.withCredentials

                pageName: "svgHolder",
                chr: "22",
                viewStart: 30000000,
                viewEnd: 30100000,

                coordSystem: this.coordSystem,

                sources: [
                    {
                        name: this.name,
                        bamURI: this.bamUri,
                        baiURI: this.baiUri,
                    }
                    // {
                    //     name: 'Genome',
                    //     twoBitURI: '//www.biodalliance.org/datasets/hg19.2bit',
                    //     tier_type: 'sequence'
                    // },
                    // {
                    //     name: 'Genes',
                    //     desc: 'Gene structures from GENCODE 19',
                    //     bwgURI: '//www.biodalliance.org/datasets/gencode.bb',
                    //     stylesheet_uri: '//www.biodalliance.org/stylesheets/gencode.xml',
                    //     collapseSuperGroups: true,
                    //     trixURI: '//www.biodalliance.org/datasets/geneIndex.ix'
                    // },
                    // {
                    //     name: 'Repeats',
                    //     desc: 'Repeat annotation from Ensembl',
                    //     bwgURI: '//www.biodalliance.org/datasets/repeats.bb',
                    //     stylesheet_uri: '//www.biodalliance.org/stylesheets/bb-repeats.xml'
                    // },
                    // {
                    //     name: 'Conservation',
                    //     desc: 'Conservation',
                    //     bwgURI: '//www.biodalliance.org/datasets/phastCons46way.bw',
                    //     noDownsample: true
                    // }
                ],
            });
        }
    }

</script>

<style scoped>

</style>
