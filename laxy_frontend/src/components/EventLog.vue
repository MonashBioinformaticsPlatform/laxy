<template>
    <div class="eventlog">
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <md-table-card>
            <md-toolbar>
                <h2 class="md-title">
                    <md-icon>event_note</md-icon>&nbsp; Event log
                </h2>
            </md-toolbar>
            <md-table>

                <md-table-row v-for="event in events" :key="event.id">
                    <md-table-cell>{{ event.timestamp | moment('Do MMMM YYYY, h:mm:ss a') }}
                    </md-table-cell>
                    <md-table-cell>{{ event.event }} <span>{{ event.event }}<template
                            v-if="event.extra.to">: {{ event.extra.to }}</template></span></md-table-cell>
                </md-table-row>
                <md-table-row v-if="events.length === 0">
                    <md-table-cell>No event logs</md-table-cell>
                </md-table-row>
            </md-table>
        </md-table-card>
    </div>
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

    import {
        State,
        Getter,
        Action,
        Mutation,
        namespace
    } from "vuex-class";

    import {WebAPI} from "../web-api";

    @Component({
        props: {
            jobId: String,
        },
        filters: {},
    })
    export default class EventLog extends Vue {

        public events: any[] = [];
        public jobId: string;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🐺";

        // for lodash in templates
        get _() {
            return _;
        }

        created() {
            this.refresh();
        }

        async refresh() {
            try {
                this.submitting = true;
                const response = await WebAPI.getJobEventLog(this.jobId);
                this.events = response.data.results;
                this.submitting = false;
            } catch (error) {
                console.log(error);
                this.submitting = false;
                this.$emit("refresh-error", error.toString());
                this.openDialog("error_dialog");
                throw error;
            }
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }
    };

</script>

<style scoped>
    .md-table {
        width: 100%;
    }
</style>
