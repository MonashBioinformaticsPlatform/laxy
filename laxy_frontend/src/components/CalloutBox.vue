<template>
  <md-whiteframe md-elevation="8" class="pad-32" style="text-align: center">
    <slot></slot>
  </md-whiteframe>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";

@Component({
  components: {},
  filters: {}
})
export default class CalloutBox extends Vue {
}
</script>

<style lang="css">
span.nobreak {
  white-space: nowrap;
}

.arrow_l {
  animation: wobble_horiz 1s ease-in-out infinite;
  margin-right: 10px;
}

.arrow_r {
  animation: wobble_horiz_phase180 1s ease-in-out infinite;
}

@keyframes wobble_horiz {
  0%,
  100% {
    transform: translate(0, 0);
  }

  50% {
    transform: translate(10px, 0);
  }
}

@keyframes wobble_horiz_phase180 {
  0%,
  100% {
    transform: translate(10px, 0);
  }

  50% {
    transform: translate(0, 0);
  }
}
</style>
