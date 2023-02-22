<template>
  <md-dialog :md-open-from="openFrom" :md-close-to="closeTo" id="thisDialog" ref="thisDialog">
    <md-dialog-title>Downloading</md-dialog-title>

    <md-dialog-content>
      An archive of the job can be downloaded. <br>
      For authorization the URL must contain a valid <code>access_token</code>, or the request must provide an API
      key.<br>
      On the command line, run:<br><br>
      <template code v-if="hasAccessToken">
        <code>curl "{{ tarballUrl }}" >{{ filename }}</code>
      </template>
      <template v-else>
        <code>curl -H "Authorization: Bearer ${api_key}" "{{ tarballUrl }}" >{{ filename }}</code>
        <br><br>
        <p>
          Your <code>${api_key}</code> is available under <a href="/#/profile">User Profile</a>.
        </p>
      </template>
    </md-dialog-content>

    <md-dialog-actions>
      <md-button class="md-primary" @click="close()">Close</md-button>
    </md-dialog-actions>
  </md-dialog>
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
import { ComputeJob } from "../../model";
import { basename } from "../../util";
// import VueMarkdown from 'vue-markdown';

@Component({
  // components: {'vue-markdown': VueMarkdown},
  filters: {},
})
export default class DownloadHelpDialog extends Vue {
  @Prop({ type: String })
  tarballUrl: string;

  @Prop({ default: null, type: String })
  openFrom: string | null;

  @Prop({ default: null, type: String })
  closeTo: string | null;

  get filename() {
    return basename(new URL(this.tarballUrl).pathname);
  }

  get hasAccessToken() {
    return this.tarballUrl.includes("access_token=")
  }

  open() {
    // console.log('Opened: ' + refName);
    ((this.$refs as any)["thisDialog"] as any).open();
  }

  close() {
    // console.log('Closed: ' + refName);
    ((this.$refs as any)["thisDialog"] as any).close();
  }
}
</script>
