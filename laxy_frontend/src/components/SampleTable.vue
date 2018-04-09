<template>
    <md-table @select="onSelect">
        <md-table-header>
            <md-table-row>
                <md-table-head v-for="field in fields" :key="field">
                    {{ field.split('metadata.').pop() | deunderscore }}
                </md-table-head>
            </md-table-row>
        </md-table-header>
        <md-table-body>
            <md-table-row v-for="(sample, index) in samples.items"
                          :key="sample.name"
                          :md-item="sample"
                          md-selection>
                <md-table-cell v-for="field in fields" :key="field">
                    <span v-if="editable_fields.includes(field)">
                        <md-input-container v-if="field.startsWith('metadata.')">
                            <md-input v-model="sample.metadata[field.split('metadata.').pop()]"
                                      :placeholder="field.split('metadata.').pop()">
                            </md-input>
                        </md-input-container>
                       <md-input-container v-else>
                          <md-input v-model="sample[field]"
                                    :placeholder="field"></md-input>
                        </md-input-container>
                    </span>
                    <span v-else-if="field.endsWith('read_count')">
                          {{ deep_path(sample, field) | numeral_format('0 a') }}
                    </span>
                    <span v-else-if="field === 'R1' || field === 'R2'">
                        <span v-for="file in sample.files">
                            <span>{{ _.get(file, field, '').split('/').pop() }}
                                <md-tooltip>{{ file[field] }}</md-tooltip>
                            </span><br/>
                        </span>
                    </span>
                    <span v-else>
                        {{ deep_path(sample, field) }}
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
    import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";

    import {SampleSet} from "../model";

    import {DummySampleList as _dummySampleList} from "../test-data";

    @Component({
        props: {
            samples: {},
            fields: Array,
            editable_fields: Array
        },
        filters: {}
    })
    export default class SampleTable extends Vue {
        // public samples: Array<Sample> = _dummySampleList;
        public samples: SampleSet;
        public selectedSamples: Array<Sample> = [];

        // fields and editable_fields can be either top level properties of
        // Sample (eg name, id) or properties of metadata (eg metadata.condition),
        // specified via dot notation: metadata.condition
        public fields: Array<string>; // = ["name", "metadata.condition", "R1", "R2"];
        public editable_fields: Array<string>; // = ["name", "metadata.condition"];

        // for lodash in templates
        get _() {
            return _;
        }

        /* Sets/retrieves a property deeply.nested.in.an.object */
        deep_path(obj: any, path: string): any {
            return _.get(obj, path);
        }

        created() {

        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
            this.$emit("selected", this.selectedSamples);
        }

        onChangeField(sample: Sample, field_path: string, newValue: string) {
            _.set(sample, field_path, newValue);
        }

        removeSelected() {
            for (const row of this.selectedSamples) {
                const i = this.samples.items.indexOf(row);
                this.samples.items.splice(i, 1);
            }
        }
    };

</script>
