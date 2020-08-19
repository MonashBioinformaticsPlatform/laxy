<template>
  <span>
    <slot></slot>
    <md-tooltip md-direction="bottom">{{ message }}</md-tooltip>
  </span>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";
import { Prop } from "vue-property-decorator";

@Component({
  components: {},
  filters: {},
})
export default class SplashTexts extends Vue {
  messages: string[] = [
    "Brought to you by the Monash Bioinformatics Platform",
    // "May contain technical replicates ...",
    // "When the cluster is working ...",
    // "... and maybe even some non-genomics pipelines",
  ];

  get message(): string {
    return this.messages[Math.floor(this.messages.length * Math.random())];
  }
}
</script>