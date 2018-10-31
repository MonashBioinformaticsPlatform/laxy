<template>
    <md-card :style="cssGradient(getThemedStatusColor(job.status))">
        <md-card-header>
            <md-card-header-text>
                <div class="md-title">Job {{ job.status }}
                </div>
                <div v-if="job.status != 'running' && job.completed_time" class="md-subhead">
                    It took about {{ job.created_time | moment("from", job.completed_time, true) }}
                </div>
                <div v-if="job.status == 'running'" class="md-subhead">
                    for {{ job.created_time | moment("from", 'now', true) }}
                </div>
            </md-card-header-text>

            <md-card-media>
                <img v-if="job.status == 'running'"
                     src="assets/outline-directions_run-24px.svg" alt="running">
                <img v-if="job.status == 'complete'"
                     src="assets/outline-check_circle_outline-24px.svg" alt="complete">
                <img v-if="job.status == 'cancelled'"
                     src="assets/outline-cancel_presentation-24px.svg" alt="cancelled">
                <img v-if="job.status == 'failed'"
                     src="assets/outline-error_outline-24px.svg" alt="failed">
            </md-card-media>
        </md-card-header>

        <md-card-actions>
            <!-- TODO: Implement feature to re-run job with tweaked params:
                       https://github.com/MonashBioinformaticsPlatform/laxy/issues/10
            <md-button v-if="job.status !== 'running'"
                       @click="cloneJob(job.id)">
                <md-icon>content_copy</md-icon>
                Run again
            </md-button>
            -->
            <md-button v-if="job.status === 'running'"
                       @click="askCancelJob(job.id)">
                <md-icon>cancel</md-icon>
                Cancel
            </md-button>
        </md-card-actions>
    </md-card>
</template>

<script lang="ts">
    import '../../assets/outline-directions_run-24px.svg';
    import '../../assets/outline-check_circle_outline-24px.svg';
    import '../../assets/outline-cancel_presentation-24px.svg';
    import '../../assets/outline-error_outline-24px.svg';

    import Component from "vue-class-component";
    import {getThemedStatusColor, cssGradient} from "../palette";
    import JobStatusCard from "./JobStatusCard.vue";

    @Component({
        props: {
            job: {type: Object},
        },
        filters: {},
    })
    export default class JobStatusPip extends JobStatusCard {
        getThemedStatusColor = getThemedStatusColor;
        cssGradient = cssGradient;
    }

</script>
