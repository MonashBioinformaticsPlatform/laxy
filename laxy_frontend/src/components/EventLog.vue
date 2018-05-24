<template>
    <div class="eventlog">
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>

        <!--
        <md-card-header>
            <div class="md-title">Event log</div>
        </md-card-header>
        <md-table>
            <md-table-row v-for="event in events" :key="event.id">
                <md-table-cell>{{ event.timestamp | moment('Do MMMM YYYY, h:mm:ss a') }}
                </md-table-cell>
                <md-table-cell>{{ event.event }}</md-table-cell>
            </md-table-row>
        </md-table>
        -->
        <md-list>
            <md-list-item>
                <md-icon>event_note</md-icon>
                <span>Event log</span>
                <md-list-expand>
                    <md-list>
                        <md-list-item v-for="event in events" :key="event.id">
                            <div class="md-list-text-container">
                                <span>{{ event.event }}<template
                                        v-if="event.extra.to">: {{ event.extra.to }}</template></span>
                                <span>
                                  {{ event.timestamp | moment('Do MMMM YYYY, h:mm:ss a') }}
                                </span>
                            </div>
                        </md-list-item>
                    </md-list>
                </md-list-expand>
            </md-list-item>
        </md-list>

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
        public snackbar_message: string = "Everything is fine. ☃";
        public snackbar_duration: number = 2000;

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
                this.error_alert_message = error.toString();
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

        flashSnackBarMessage(msg: string, duration: number = 2000) {
            this.snackbar_message = msg;
            this.snackbar_duration = duration;
            (this.$refs.snackbar as any).open();
        }
    };

</script>

<style scoped>
    .md-table-card {
        width: 100%;
    }
</style>
