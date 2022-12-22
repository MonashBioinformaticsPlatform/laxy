<template>
  <div class="ngl_viewport" :id="viewportId"></div>
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
import { WebAPI } from "../../../../web-api";

const NGL = require('ngl');

@Component({
  filters: {},
})
export default class NglViewer extends Vue {

  pdbFileId: string = '4aIhItPH2ml0ZPCzW8WkLg';
  jobId: string = '7iwC7PemKGkd5uxzvMIapu';
  viewportId: string = 'ngl_view';

  @Prop({ type: Boolean, default: true })
  public showDownloadButton: boolean;

  @Prop({ type: String, default: "" })
  public downloadUrl: string;

  async created() {
    // viewportId is set to a random value for the lifetime of the component
    this.viewportId = `ngl_view_${Math.random().toString(36).substring(7)}`;

    await this.loadStructure(this.downloadUrl);
  }

  async loadStructure(url: string) {
    const pdbResponse = await WebAPI.getBlobByUrl(url);
    const pdbBlob = pdbResponse.data;
    const stage = new NGL.Stage(this.viewportId);
    stage.loadFile(pdbBlob, { ext: "pdb", defaultRepresentation: true });
  }
}
</script>

<style scoped>
.ngl_viewport {
  height: 400px;
}
</style>