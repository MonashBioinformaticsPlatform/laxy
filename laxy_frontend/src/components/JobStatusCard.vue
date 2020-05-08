<template>
  <md-card class="fill-width" md-with-hover>
    <md-card-header>
      <md-layout>
        <md-layout md-column>
          <div class="md-title">{{ job.params.pipeline }} job</div>
          <div class="md-subhead">{{ job.params.description }}</div>
        </md-layout>
        <md-layout md-flex="20">
          <md-icon
            v-if="job.status === 'failed'"
            class="push-right md-size-2x md-accent"
          >error_outline</md-icon>
          <md-icon
            v-if="job.status === 'cancelled'"
            class="push-right md-size-2x md-warn"
          >cancel_presentation</md-icon>
          <md-icon
            v-if="job.status === 'complete'"
            class="push-right md-size-2x md-primary"
          >check_circle_outline</md-icon>
          <spinner-cube-grid
            v-if="job.status === 'running'"
            :colors="themeColors()"
            :time="1.5"
            :columns="4"
            :rows="4"
            :width="48"
            :height="48"
            :random-seed="hashCode(job.id)"
          ></spinner-cube-grid>
        </md-layout>
        <!--
                <md-layout v-if="job.status === 'running'" md-flex="20" md-align="center" class="pad-32">
                    <spinner-cube-grid v-if="job.status === 'running'"
                                       :colors="themeColors()"
                                       :time="1.5"
                                       :columns="4" :rows="4"
                                       :width="96" :height="96"
                                       :random-seed="hashCode(job.id)">

                    </spinner-cube-grid>
                </md-layout>
        -->
      </md-layout>
    </md-card-header>

    <md-card-content>
      <md-table>
        <md-table-body>
          <md-table-row>
            <md-table-cell>Status</md-table-cell>
            <md-table-cell>
              <span :style="{ color: getStatusColor(job.status) }">{{ job.status }}</span>
            </md-table-cell>
          </md-table-row>
          <md-table-row>
            <md-table-cell>Created</md-table-cell>
            <md-table-cell>
              <md-tooltip md-direction="top">{{ job.created_time }}</md-tooltip>
              {{ job.created_time| moment('from') }}
            </md-table-cell>
          </md-table-row>
          <md-table-row v-if="job && job.expiry_time">
            <md-table-cell>
              Large files expire on
              <md-button
                id="expiryInfoButton"
                @click="openDialog('expiryInfoDialog')"
                class="md-icon-button md-dense"
              >
                <md-icon style="color: #bdbdbd;">info</md-icon>
              </md-button>
            </md-table-cell>
            <md-table-cell>
              <md-tooltip md-direction="top">{{ job.expiry_time }}</md-tooltip>
              {{ job.expiry_time| moment('DD-MMM-YYYY') }} ({{ job.expiry_time| moment('from') }} from
              now)
            </md-table-cell>
          </md-table-row>
          <md-table-row v-for="row in extraTableRows" :key="row[0]">
            <md-table-cell>{{ row[0] }}</md-table-cell>
            <md-table-cell>
              {{ row[1] }}
              <!-- <span v-html="row[1]"></span> -->
            </md-table-cell>
          </md-table-row>
          <md-table-row v-if="job.completed_time">
            <md-table-cell>Completed</md-table-cell>
            <md-table-cell>
              <md-tooltip md-direction="top">{{ job.completed_time }}</md-tooltip>
              {{ job.completed_time| moment('from') }}
            </md-table-cell>
          </md-table-row>
          <md-table-row>
            <md-table-cell>Job ID</md-table-cell>
            <md-table-cell>{{ job.id }}</md-table-cell>
          </md-table-row>
        </md-table-body>
      </md-table>
    </md-card-content>

    <md-card-actions>
      <md-button
        v-if="showRunAgainButton && ['failed', 'cancelled', 'complete'].includes(job.status)"
        @click="cloneJob(job.id)"
      >
        <md-icon>content_copy</md-icon>Run again
      </md-button>
      <md-button v-if="showCancelButton && job.status === 'running'" @click="askCancelJob(job.id)">
        <md-icon>cancel</md-icon>Cancel
      </md-button>
    </md-card-actions>

    <ExpiryDialog ref="expiryInfoDialog" :job="job"></ExpiryDialog>
  </md-card>
</template>

<script lang="ts">
import "es6-promise";

import Vue, { ComponentOptions } from "vue";
import {
  palette,
  getStatusColor,
  themeColors,
} from "../palette";

import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch
} from "vue-property-decorator";

import { ComputeJob } from "../model";
import ExpiryDialog from "./Dialogs/ExpiryDialog.vue";

@Component({
  components: { ExpiryDialog },
  filters: {}})
export default class JobStatusCard extends Vue {
  @Prop({ type: Object })
  public job: ComputeJob | null;

  @Prop({ default: true, type: Boolean })
  showCancelButton: boolean;

  @Prop({ default: true, type: Boolean })
  showRunAgainButton: boolean;

  @Prop({ default: () => [], type: Array })
  public extraTableRows: string[][] | null;

  getStatusColor = getStatusColor;
  themeColors = themeColors;

  // http://werxltd.com/wp/2010/05/13/javascript-implementation-of-javas-string-hashcode-method/
  hashCode(s: string): number {
    var hash = 0;
    if (s.length == 0) return hash;
    for (let i = 0; i < s.length; i++) {
      let char = s.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
  }

  askCancelJob(id: string) {
    this.$emit("cancel-job-clicked", id);
  }

  cloneJob(id: string) {
    this.$emit("clone-job-clicked", id);
  }

  openDialog(refName: string) {
    // console.log('Opened: ' + refName);
    ((this.$refs as any)[refName] as any).open();
  }

  closeDialog(refName: string) {
    // console.log('Closed: ' + refName);
    ((this.$refs as any)[refName] as any).close();
  }
};

</script>

<style scoped>
.spin {
  animation: rotate 1s infinite linear;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(359deg);
  }
}
</style>
