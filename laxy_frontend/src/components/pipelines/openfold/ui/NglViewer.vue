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
    const structure = await stage.loadFile(pdbBlob, { ext: "pdb", defaultRepresentation: true });
    // TODO: The representation should be passed in as a @Prop, overriding the default
    // TODO: Show a key for the color scale in the md-card on the LaxyNglViewer component
    // Color by B-factor value ranges (Alphafold/Openfold put the pLDDT score in this field)
    structure.addRepresentation('cartoon', {
      colorDomain: [0, 49.999, 50, 69.999, 70, 89.999, 90, 100],
      colorScale: ['#ff7d45', '#ff7d45', '#ffdb13', '#ffdb13', '#65cbf3', '#65cbf3', '#0053d6', '#0053d6'],
      colorScheme: 'bfactor'
    })
  }
}
</script>

<style scoped>
.ngl_viewport {
  height: 400px;
}
</style>