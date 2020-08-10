<template>
  <div class="eventlog">
    <md-layout>
      <md-toolbar class="md-transparent">
        <h2 class="md-title">
          <md-icon>event_note</md-icon>&nbsp; Event log
        </h2>
      </md-toolbar>
      <md-table>
        <md-table-body>
          <md-table-row v-for="event in events" :key="event.id">
            <md-table-cell>{{ event.timestamp | moment('Do MMMM YYYY, h:mm:ss a') }}</md-table-cell>
            <md-table-cell>
              <template v-if="event.message">{{ event.message }}</template>
              <template v-else>{{ event.event }}</template>
              <span>
                <!--
                                <template v-if="event.extra.from">: {{ event.extra.from }}</template>
                                <template v-if="event.extra.to"> → {{ event.extra.to }}</template>
                -->
                <template v-if="event.extra.to === 'complete'">☺</template>
                <template v-if="event.extra.to === 'failed'">☹</template>
              </span>
            </md-table-cell>
          </md-table-row>
          <md-table-row v-if="events.length === 0">
            <md-table-cell>No event logs</md-table-cell>
          </md-table-row>
        </md-table-body>
      </md-table>
    </md-layout>
  </div>
</template>


<script lang="ts">
import * as _ from "lodash";
import "es6-promise";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch,
} from "vue-property-decorator";

import { State, Getter, Action, Mutation, namespace } from "vuex-class";

import { WebAPI } from "../web-api";

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

  created() {
    this.refresh();
  }

  public async refresh() {
    try {
      this.submitting = true;
      const response = await WebAPI.getJobEventLog(this.jobId);
      this.events = response.data.results;
      this.submitting = false;
    } catch (error) {
      console.log(error);
      this.submitting = false;
      this.$emit("refresh-error", error.toString());
      throw error;
    }
  }
}
</script>

<style scoped>
.md-table {
  width: 100%;
}
</style>
