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
                          :key="JSON.stringify([sample.id, sample.name, sample.files])"
                          :md-item="sample"
                          :md-selection="selectable">
                <md-table-cell v-for="field in fields" :key="field">
                    <span v-if="editableFields.includes(field)">
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
                        <span v-for="file in filter(sample.files, (f) => get(f, field, false))">
                            {{ file_basename(get(file, field, '')) }}
                                <md-tooltip>{{ file[field] }}</md-tooltip>
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

    import get from "lodash-es/get";
    import set from "lodash-es/set";
    import filter from "lodash-es/filter";

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

    import {Sample, SampleSet} from "../model";

    import {DummySampleList as _dummySampleList} from "../test-data";

    @Component({
        filters: {}
    })
    export default class SampleTable extends Vue {
        // public samples: Array<Sample> = _dummySampleList;

        @Prop({default: {}, type: SampleSet})
        public samples: SampleSet;

        ////
        // fields and editableFields can be either top level properties of
        // Sample (eg name, id) or properties of metadata (eg metadata.condition),
        // specified via dot notation: metadata.condition

        // = ["name", "metadata.condition", "R1", "R2"];
        @Prop({default: () => [], type: Array})
        public fields: Array<string>;

        // = ["name", "metadata.condition"];
        @Prop({default: () => [], type: Array})
        public editableFields: Array<string>;
        ////

        @Prop({default: true, type: Boolean})
        public selectable: boolean;

        public selectedSamples: Array<Sample> = [];

        // for lodash in templates
        // get _() {
        //     return _;
        // }

        // lodash for templates
        get = get;
        filter  = filter;

        /* Sets/retrieves a property deeply.nested.in.an.object */
        deep_path(obj: any, path: string): any {
            return get(obj, path);
        }

        file_basename(filepath: string): string | undefined {
            return filepath.split('/').pop();
        }

        created() {

        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
            this.$emit("selected", this.selectedSamples);
        }

        onChangeField(sample: Sample, field_path: string, newValue: string) {
            set(sample, field_path, newValue);
        }

        removeSelected() {
            for (const row of this.selectedSamples) {
                const i = this.samples.items.indexOf(row);
                this.samples.items.splice(i, 1);
            }
        }
    };

</script>
