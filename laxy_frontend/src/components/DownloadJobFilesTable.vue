<template>
  <md-table>
    <md-table-header>
      <md-table-row>
        <md-table-head>Link</md-table-head>
        <md-table-head style="text-align: right;">Action</md-table-head>
      </md-table-row>
    </md-table-header>
    <md-table-body>
      <md-table-row v-for="link in [url]" :key="url">
        <md-table-cell>
          <a :href="link" @click.prevent="setClipboardFlash(link, 'Copied download link to clipboard !')">
            <md-icon>link</md-icon>
            {{ filename(url) | truncate }}
          </a>
        </md-table-cell>
        <md-table-cell md-numeric>
          <md-button class="md-icon-button push-right"
            @click="setClipboardFlash(link, 'Copied download link to clipboard !')">
            <md-icon>file_copy</md-icon>
            <md-tooltip md-direction="top">Copy to clipboard</md-tooltip>
          </md-button>
        </md-table-cell>
      </md-table-row>
    </md-table-body>
  </md-table>
</template>

<script lang="ts">
import Vue, { ComponentOptions } from "vue";
import Component, { mixins } from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch,
} from "vue-property-decorator";

import { CopyToClipboard } from '../clipboard-mixin';

@Component({
  filters: {},
})
export default class DownloadJobFilesTable extends mixins(CopyToClipboard) {
  @Prop({ type: String })
  public url: string;

  filename(url: string): string | undefined {
    return new URL(url).pathname.split("/").pop();
  }
}
</script>
