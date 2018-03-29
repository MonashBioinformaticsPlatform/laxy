<template>
    <md-table @select="onSelect">
        <md-table-header>
            <md-table-row>
                <md-table-head v-for="field in fields" :key="field">
                    {{ field | deunderscore }}
                </md-table-head>
            </md-table-row>
        </md-table-header>
        <md-table-body>
            <md-table-row v-for="(sample, index) in samples" :key="sample.name"
                          :md-item="sample"
                          md-selection>
                <md-table-cell v-for="field in fields" :key="field">
                    <span v-if="editable_fields.includes(field)">
                        <md-input-container>
                            <md-input v-model="sample[field]"></md-input>
                        </md-input-container>
                    </span>
                    <!--
                    <span v-else-if="field === 'read_count'">
                          {{ sample[field] | numeral_format('0 a') }}
                    </span>
                    -->
                    <span v-else-if="field === 'R1' || field === 'R2'">
                        <span v-for="file in sample['files']">
                            {{ file[field] }}<br/>
                        </span>
                        <!-- {{ JSON.stringify(sample['files']) }} -->
                    </span>
                    <span v-else>
                        {{ sample[field] }}
                    </span>
                </md-table-cell>
            </md-table-row>
        </md-table-body>
    </md-table>
</template>

<script lang="ts">
    import "vue-material/dist/vue-material.css";

    import * as _ from "lodash";
    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
    import VueMaterial from "vue-material";
    import Component from "vue-class-component";
    import {Emit, Inject, Model, Prop, Provide, Watch} from "vue-property-decorator";

    import {DummySampleList as _dummySampleList} from "../test-data";

    @Component({props: {
                samples: Array,
                fields: Array,
                editable_fields: Array
        }, filters: {}})
    export default class SampleTable extends Vue {
        // public samples: Array<Sample> = _dummySampleList;
        public samples: Sample[];
        public selectedSamples: Array<Sample> = [];
        public fields: Array<string>; // = ["name", "condition", "R1", "R2"];
        public editable_fields: Array<string>; // = ["name", "condition"];

        // for lodash in templates
        get _() {
            return _;
        }

        created() {

        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
            this.$emit('selected', this.selectedSamples);
        }

        removeSelected() {
            for (const row of this.selectedSamples) {
                const i = this.samples.indexOf(row);
                this.samples.splice(i, 1);
            }
        }
    };

</script>
