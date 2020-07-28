<template>
  <!-- eg multiqc report link -->
  <md-card
    md-with-hover
    @click.native.stop="openLinkInTab(url)"
    :style="cssStripe(getThemeColor('primary'), 'left', 4)"
  >
    <md-card-header>
      <md-card-header-text>
        <div class="md-title">
          <slot name="title"></slot>
        </div>
        <div class="md-subhead">
          <slot name="subtitle"></slot>
        </div>
      </md-card-header-text>

      <md-card-media>
        <md-icon class="md-size-4x">{{ icon }}</md-icon>
      </md-card-media>
    </md-card-header>

    <md-card-actions>
      <md-button @click.stop="openLinkInTab(url)">
        <md-icon>remove_red_eye</md-icon>View
      </md-button>
    </md-card-actions>
  </md-card>
</template>

<script lang="ts">
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
import { getThemeColor, cssStripe } from "../palette";

@Component({
  filters: {},
})
export default class FileLinkPip extends Vue {
  @Prop({ type: String })
  public url: string;

  @Prop({ type: String, default: "view_list" })
  public icon: string;

  getThemeColor = getThemeColor;
  cssStripe = cssStripe;

  openLinkInTab(url: string) {
    window.open(url);
  }
}
</script>
