<template>
  <md-card md-with-hover id="rnaseq">
    <md-card-header>
      <div class="md-title">RNA-Seq</div>
      <div class="md-subhead">using public data, or your own</div>
    </md-card-header>

    <md-card-content>
      <md-card-media>
        <md-layout md-align="center">
          <svg width="200" height="200">
            <rect x="0" y="0" width="25" height="20" fill="#ccc" />
            <rect x="30" y="0" width="45" height="20" fill="#aaa" />
            <rect x="80" y="0" width="35" height="20" fill="#ccc" />
            <rect x="125" y="0" width="75" height="20" fill="#aaa" />
            <rect x="0" y="30" width="35" height="20" fill="#aaa" />
            <rect x="40" y="30" width="40" height="20" fill="#ccc" />
            <rect x="85" y="30" width="30" height="20" fill="#aaa" />
            <rect x="125" y="30" width="75" height="20" fill="#aaa" />
            <rect x="0" y="60" width="35" height="20" fill="#ccc" />
            <rect x="40" y="60" width="20" height="20" fill="#aaa" />
            <rect x="70" y="60" width="30" height="20" fill="#ccc" />
            <rect x="105" y="60" width="90" height="20" fill="#aaa" />
            <rect x="0" y="90" width="35" height="20" fill="#aaa" />
            <rect x="40" y="90" width="30" height="20" fill="#ccc" />
            <rect x="75" y="90" width="40" height="20" fill="#aaa" />
            <rect x="110" y="90" width="85" height="20" fill="#aaa" />
            <rect x="0" y="120" width="30" height="20" fill="#ccc" />
            <rect x="40" y="120" width="25" height="20" fill="#aaa" />
            <rect x="70" y="120" width="40" height="20" fill="#ccc" />
            <rect x="115" y="120" width="50" height="20" fill="#aaa" />
            <rect x="165" y="120" width="35" height="20" fill="#aaa" />
            <rect x="0" y="150" width="25" height="20" fill="#aaa" />
            <rect x="30" y="150" width="50" height="20" fill="#ccc" />
            <rect x="85" y="150" width="35" height="20" fill="#aaa" />
            <rect x="125" y="150" width="75" height="20" fill="#aaa" />
            <rect x="0" y="180" width="40" height="20" fill="#ccc" />
            <rect x="45" y="180" width="25" height="20" fill="#aaa" />
            <rect x="75" y="180" width="35" height="20" fill="#ccc" />
            <rect x="115" y="180" width="50" height="20" fill="#aaa" />
            <rect x="165" y="180" width="35" height="20" fill="#aaa" />
            <rect x="0" y="0" width="200" height="200" fill="none" stroke="#eee" stroke-width="10" />
          </svg>
        </md-layout>
      </md-card-media>
      <br />
      <!--<md-card-actions>-->
      <router-link tag="md-button" class="md-primary md-raised fill-width" :to="routeTo">Run an RNA-Seq
        analysis</router-link>
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
  @Prop({ type: String, default: "/run/nf-core-rnaseq" })
  routeTo: string;
}
</script>