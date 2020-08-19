<template>
  <md-card md-with-hover id="variants">
    <md-card-header>
      <div class="md-title">Variant calls</div>
      <div class="md-subhead">using public data from ENA/SRA</div>
    </md-card-header>

    <md-card-content>
      <md-card-media>
        <md-layout md-align="center">
          <span class="md-title">
            T ⤇ C
            <br />G ⤇ A
            <br />
          </span>
        </md-layout>
      </md-card-media>
      <br />
      <!--<md-card-actions>-->
      <router-link
        tag="md-button"
        disabled="true"
        class="md-primary md-raised fill-width"
        to="variants"
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
export default class VariantCallsLaunch extends Vue {}
</script>