<template>
    <md-card class="fill-width" md-with-hover>
        <md-card-area>
            <md-card-header>
                <md-card-header-text>
                    <div class="md-title">
                        <slot name="title"></slot>
                    </div>
                    <div class="md-subhead">
                        <slot name="subtitle"></slot>
                    </div>
                </md-card-header-text>

            </md-card-header>
            <md-card-content>
                <ngl-viewer :download-url="downloadURL"></ngl-viewer>
                <!-- <a :href="downloadURL">Download</a> -->
            </md-card-content>
        </md-card-area>
        <md-card-actions v-if="showDownloadButton">
            <md-button @click="doDownload">
                <md-icon>download</md-icon>
                Download
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
import { WebAPI } from "../../../../web-api";

import {
    filterByTag,
    filterByRegex,
    filterByFullPath,
    filterByFilename,
    downloadFile,
} from "../../../../file-tree-util";

import { Store as store } from '../../../../store';

import NglViewer from "./NglViewer.vue";

@Component({
    filters: {},
    components: {
        NglViewer
    },
})
export default class LaxyNglViewer extends Vue {

    //pdbFileId: string = '4aIhItPH2ml0ZPCzW8WkLg';
    //jobId: string = '7iwC7PemKGkd5uxzvMIapu';

    @Prop({ type: String, default: "" })
    public jobId: string;

    @Prop({ type: String, default: "" })
    public fileId: string;

    @Prop({ type: Boolean, default: true })
    public showDownloadButton: boolean;

    get downloadURL() {
        const access_token = store.getters.jobAccessToken(this.jobId);
        return WebAPI.downloadFileByIdUrl(this.fileId, null, access_token)
    }

    doDownload(event: any) {
        window.open(this.downloadURL);
        //this.$emit("click");
    }
}
</script>