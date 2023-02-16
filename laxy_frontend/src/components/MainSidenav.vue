<template>
  <md-sidenav class="md-left" ref="sidenav" @open="open('Left')" @close="close('Left')">
    <md-toolbar class="md-large">
      <h3 class="md-title">~</h3>
    </md-toolbar>
    <md-list md-dense>
      <md-list-item>
        <router-link :to="{ name: 'home' }" exact>
          <span @click="toggle('sidenav')">
            <md-icon>home</md-icon>&nbsp;&nbsp;Home
          </span>
        </router-link>
      </md-list-item>
      <md-list-item>
        <router-link :to="{ name: 'about' }" exact>
          <span @click="toggle('sidenav')">
            <md-icon>help_center</md-icon>&nbsp;&nbsp;About
          </span>
        </router-link>
      </md-list-item>
      <md-list-item v-if="showJobsLink">
        <router-link to="/jobs">
          <span @click="toggle('sidenav')">
            <md-icon>view_list</md-icon>&nbsp;&nbsp;My Jobs
          </span>
        </router-link>
      </md-list-item>
      <!-- <md-list-item>
        <router-link to="/run/rnasik">
          <span @click="toggle('sidenav')">
            <md-icon>play_circle_outline</md-icon>&nbsp;&nbsp;Run an RNA-Seq analysis
          </span>
        </router-link>
      </md-list-item>-->
      <md-list-item v-for="pipeline in availablePipelines" :key="pipeline.id">
        <router-link :to="`/run/${pipeline.name.replace('_', '-')}`">
          <span @click="toggle('sidenav')">
            <md-icon>play_circle_outline</md-icon>
            &nbsp;&nbsp;Run {{ getPipelineShortDescription(pipeline.name) }}
          </span>
          <span>
            <md-icon v-if="!pipeline.public">lock</md-icon>
            <md-tooltip md-direction="right">Private pipeline (not publicly available)</md-tooltip>
          </span>
        </router-link>
      </md-list-item>
    </md-list>
    <div>
      <span style="position: absolute; bottom: 0; padding: 16px" class="md-caption">
        <slot name="footer"></slot>
      </span>
    </div>
  </md-sidenav>
</template>


<script lang="ts">
import "es6-promise";

import get from "lodash-es/get";
import sortBy from "lodash-es/sortBy";

import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch
} from "vue-property-decorator";

@Component({
  components: {},
  props: {},
  filters: {}
})
export default class MainSidenav extends Vue {
  @Prop({ default: false, type: Boolean })
  showJobsLink: boolean;

  get availablePipelines() {
    return sortBy(
      this.$store.state.availablePipelines,
      p => !get(p, "public", true)
    );
  }

  getPipelineShortDescription(name: string) {
    return get(
      this.$store.state.availablePipelines[name],
      "metadata.short_description",
      name
    );
  }

  routeTo(name: string, params: any = {}) {
    this.$router.push({ name: name, params: params });
  }
  toggle(refName: string) {
    ((this.$refs as any)["sidenav"] as any).toggle();
  }
  open(ref: string) {
    // console.log('Opened: ' + ref);
  }
  close(ref: string) {
    // console.log('Closed: ' + ref);
  }
}
</script>

<style scoped>
.md-sidenav .md-sidenav-content {
  width: 320px;
}
</style>
