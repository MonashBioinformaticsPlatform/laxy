<template>
  <md-boards :md-auto="true" :md-infinite="true" :md-duration="5000" :md-swipeable="true">
    <md-board>
      <div class="md-body-1">
        Laxy helps run analyses on genomic data.
        <br />
      </div>
    </md-board>
    <md-board>
      <div class="md-body-1">
        Give it your raw FASTQ reads and it will run an RNA-seq pipeline and allow you to
        explore the results.
      </div>
    </md-board>
    <md-board>
      <div class="md-body-1">
        View QC reports (MultiQC FTW !).
        <br />
      </div>
    </md-board>
    <md-board>
      <div class="md-body-1">
        Laxy lets you share analysis results with collaborators.
        <br />
      </div>
    </md-board>
    <md-board>
      <div class="md-body-1">
        Laxy can pass results to Degust to visualize differential gene expression.
        <br />
      </div>
    </md-board>
    <md-board>
      <div class="md-body-1">
        Want to save the results ? Download a tarball of the whole (reproducible) analysis.
        <br />
      </div>
    </md-board>
  </md-boards>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";

@Component({
  components: {},
  filters: {},
})
export default class CheezyScroller extends Vue {}
</script>