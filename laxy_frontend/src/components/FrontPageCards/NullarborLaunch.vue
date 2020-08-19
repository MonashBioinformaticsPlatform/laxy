<template>
  <md-card md-with-hover id="nullarbor">
    <md-card-header>
      <div class="md-title">Bacterial genome assembly and annotation</div>
      <div class="md-subhead">"Reads to report" using Nullarbor</div>
    </md-card-header>

    <md-card-content>
      <md-card-media>
        <md-layout md-align="center">
          <svg width="128px" height="64px" viewBox="0 0 128 64">
            <rect x="0" y="0" width="32" height="16" style="fill: grey; stroke: black;" />
            <rect
              x="42"
              y="0"
              width="32"
              height="16"
              style="fill: black; stroke: black; stroke-dasharray: 2;"
            />
            <rect x="24" y="20" width="32" height="16" style="fill: grey; stroke: black;" />
            <rect x="64" y="20" width="32" height="16" style="fill: grey; stroke: black;" />
            <rect x="0" y="40" width="120" height="16" style="fill: grey; stroke: black;" />
          </svg>
        </md-layout>
      </md-card-media>
      <br />
      <!--<md-card-actions>-->
      <router-link
        tag="md-button"
        disabled="true"
        class="md-primary md-raised fill-width"
        to="chipseq"
      >Coming soon ...</router-link>
      <!--</md-card-actions>-->
    </md-card-content>
    <md-ink-ripple></md-ink-ripple>
  </md-card>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";

@Component({
  components: {},
  filters: {},
})
export default class NullarborLaunch extends Vue {}
</script>