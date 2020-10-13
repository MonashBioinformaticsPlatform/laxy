<template>
  <md-card md-with-hover id="rnaseq">
    <md-card-header>
      <div class="md-title">RNA-Seq</div>
      <div class="md-subhead">using public data, or your own</div>
    </md-card-header>

    <md-card-content>
      <md-card-media>
        <md-layout md-align="center">
          <svg width="128px" height="64px" viewBox="0 0 128 64">
            <rect
              x="0"
              y="0"
              width="32"
              height="16"
              style="fill: grey; stroke: black"
            />
            <rect
              x="42"
              y="0"
              width="32"
              height="16"
              style="fill: grey; stroke: black"
            />
            <rect
              x="24"
              y="20"
              width="32"
              height="16"
              style="fill: grey; stroke: black"
            />
            <rect
              x="64"
              y="20"
              width="32"
              height="16"
              style="fill: grey; stroke: black"
            />
            <rect
              x="0"
              y="40"
              width="120"
              height="16"
              style="fill: grey; stroke: black"
            />
          </svg>
        </md-layout>
      </md-card-media>
      <br />
      <!--<md-card-actions>-->
      <router-link
        tag="md-button"
        class="md-primary md-raised fill-width"
        :to="routeTo"
        >Run an RNA-Seq analysis</router-link
      >
      <!--</md-card-actions>-->
    </md-card-content>
    <md-ink-ripple></md-ink-ripple>
  </md-card>
</template>


<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";
import { Prop } from "vue-property-decorator";

@Component({
  components: {},
  filters: {},
})
export default class RnaSeqLaunch extends Vue {
  @Prop({ type: String, default: "/run/rnasik" })
  routeTo: string;
}
</script>