<template>
  <banner-notice
    v-if="popupsAreBlocked && !popupWarningDismissed"
    @click="() => { popupWarningDismissed = true }"
    class="shadow"
    type="warning"
  >Please enable pop-ups for this site</banner-notice>
</template>

<script lang="ts">
import Vue from "vue";
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
// import {State2Way} from 'vuex-class-state2way'
import { State2Way } from "../vuex/state2way";

import {
  SET_POPUPS_ARE_BLOCKED,
  SET_POPUP_BLOCKER_TESTED,
  SET_POPUP_WARNING_DISMISSED,
} from "../store";
import BannerNotice from "./BannerNotice.vue";

@Component({
  components: { BannerNotice },
  filters: {},
})
export default class PopupBlockerBanner extends Vue {
  $store: any;

  @Prop({ type: Boolean, default: true })
  doTestOnCreate: boolean;

  created() {
    if (this.doTestOnCreate) {
      this._popupsBlockerTest();
    }
  }

  @State2Way(SET_POPUP_WARNING_DISMISSED, "popupWarningDismissed")
  public popupWarningDismissed: boolean;

  get popupsAreBlocked(): boolean {
    return this._popupsBlockerTest();
  }

  _popupsBlockerTest() {
    if (!this.$store.state.popupBlockerTested) {
      const w = window.open("", "_blank");
      window.focus();
      if (w == null || typeof w == undefined) {
        this.$store.commit(SET_POPUPS_ARE_BLOCKED, true);
      } else {
        w.close();
      }
      this.$store.commit(SET_POPUP_BLOCKER_TESTED, true);
    }

    return this.$store.state.popupsAreBlocked;
  }
}
</script>

<style lang="css">
</style>
