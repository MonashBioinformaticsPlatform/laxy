<template>
  <div class="download-job-files-table">
    <md-table>
    <md-table-header>
      <md-table-row>
        <md-table-head>Link</md-table-head>
        <md-table-head style="text-align: right;">Action</md-table-head>
      </md-table-row>
    </md-table-header>
    <md-table-body>
      <md-table-row v-for="(row, idx) in linkRows" :key="idx">
        <md-table-cell>
          <a :href="row.url" @click.prevent="setClipboardFlash(row.url, 'Copied download link to clipboard !')">
            <md-icon>link</md-icon>
            {{ row.label | truncate }}
          </a>
        </md-table-cell>
        <md-table-cell md-numeric>
          <div class="download-actions">
            <md-button class="md-icon-button"
              @click="setClipboardFlash(row.url, 'Copied download link to clipboard !')">
              <md-icon>file_copy</md-icon>
              <md-tooltip md-direction="top">Copy to clipboard</md-tooltip>
            </md-button>
            <md-button class="md-icon-button" @click="requestBrowserDownload(row)">
              <md-icon>cloud_download</md-icon>
              <md-tooltip md-direction="top">Download</md-tooltip>
            </md-button>
          </div>
        </md-table-cell>
      </md-table-row>
    </md-table-body>
  </md-table>

    <md-dialog ref="downloadConfirmDialog">
      <md-dialog-title>Download</md-dialog-title>
      <md-dialog-content>
        <div class="download-confirm-body">
          <md-icon v-if="showLargeDownloadWarning" class="download-size-warning-icon">warning</md-icon>
          <span class="download-confirm-text">{{ confirmDialogText }}</span>
        </div>
      </md-dialog-content>
      <md-dialog-actions>
        <md-button @click="closeConfirmDialog">Cancel</md-button>
        <md-button class="md-primary" @click="confirmPendingDownload">Yes</md-button>
      </md-dialog-actions>
    </md-dialog>
  </div>
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

/** SI megabytes, consistent with the humanize_bytes filter (1000-based). */
const LARGE_DOWNLOAD_WARNING_BYTES = 100 * 1000 * 1000;

export type DownloadLinkScope = "all" | "input" | "output";

export interface DownloadLinkRow {
  label: string;
  url: string;
  /** If set, confirmation copy names this download; otherwise generic. */
  downloadScope?: DownloadLinkScope | null;
  /** Approximate total size in bytes; omitted in dialog if unknown or non-positive. */
  approxBytes?: number | null;
}

@Component({
  filters: {},
})
export default class DownloadJobFilesTable extends mixins(CopyToClipboard) {
  @Prop({ type: String, default: "" })
  public url: string;

  @Prop({ type: Array })
  public links?: DownloadLinkRow[];

  public confirmDialogText: string = "";
  public pendingDownloadUrl: string | null = null;
  public pendingApproxBytes: number | null = null;

  filename(url: string): string | undefined {
    return new URL(url).pathname.split("/").pop();
  }

  get linkRows(): DownloadLinkRow[] {
    if (Array.isArray(this.links) && this.links.length > 0) {
      return this.links;
    }
    if (this.url) {
      const name = this.filename(this.url);
      return [{ label: name || "Download", url: this.url }];
    }
    return [];
  }

  get showLargeDownloadWarning(): boolean {
    const b = this.pendingApproxBytes;
    return b != null && b > LARGE_DOWNLOAD_WARNING_BYTES;
  }

  buildConfirmMessage(row: DownloadLinkRow): string {
    const scope = row.downloadScope;
    let subject: string;
    if (scope === "all") {
      subject = "all job files";
    } else if (scope === "input") {
      subject = "input files";
    } else if (scope === "output") {
      subject = "output files";
    } else {
      subject = "files";
    }
    const bytes = row.approxBytes;
    if (bytes != null && bytes > 0) {
      const fmt = (this.$options.filters as { humanize_bytes?: (b: number) => string })
        .humanize_bytes;
      const human = fmt ? fmt(bytes) : `${bytes} B`;
      return `Download ${subject} (${human} total)?`;
    }
    return `Download ${subject}?`;
  }

  requestBrowserDownload(row: DownloadLinkRow) {
    this.pendingDownloadUrl = row.url;
    const bytes = row.approxBytes;
    this.pendingApproxBytes =
      bytes != null && bytes > 0 ? bytes : null;
    this.confirmDialogText = this.buildConfirmMessage(row);
    (this.$refs.downloadConfirmDialog as MdDialog).open();
  }

  closeConfirmDialog() {
    (this.$refs.downloadConfirmDialog as MdDialog).close();
    this.pendingDownloadUrl = null;
    this.pendingApproxBytes = null;
  }

  confirmPendingDownload() {
    const url = this.pendingDownloadUrl;
    (this.$refs.downloadConfirmDialog as MdDialog).close();
    this.pendingDownloadUrl = null;
    this.pendingApproxBytes = null;
    if (url) {
      window.open(url, "_blank");
    }
  }
}
</script>

<style scoped>
.download-job-files-table {
  width: 100%;
}

.download-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: nowrap;
  width: 100%;
}

.download-confirm-body {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.download-confirm-text {
  flex: 1;
  min-width: 0;
}

.download-size-warning-icon {
  color: #f9a825;
  flex-shrink: 0;
}
</style>
