<template>
  <md-layout md-column md-gutter>
    <md-layout style="margin: 24px" md-vertical-align="stretch" :md-column-medium="true" :md-row-large="true">
      <md-whiteframe md-elevation="2" class="pad-32">
        <h1 class="md-title">API keys</h1>
        <p>
          Named keys authenticate as you on the REST API and MCP.
          The secret is shown only once when you create a key.
        </p>

        <md-whiteframe v-if="issuedKey" md-elevation="1" class="pad-16 issued-panel">
          <h3>New API key created</h3>
          <p><strong>Copy this key now — it will not be shown again.</strong></p>
          <md-layout md-vertical-align="center">
            <code class="secret-box" ref="secretCode">{{ issuedKey.key }}</code>
          </md-layout>
          <md-button class="md-raised md-primary" @click="copyIssuedKey">
            <md-icon>content_copy</md-icon>
            <span class="pad-8-sides">Copy</span>
          </md-button>
          <md-button class="md-raised" @click="issuedKey = null">Dismiss</md-button>

          <div>
            <md-button class="md-dense" @click="curlExpanded = !curlExpanded">
              {{ curlExpanded ? 'Hide curl example' : 'Show curl example' }}
            </md-button>
            <pre v-if="curlExpanded" class="snippet">{{ curlSnippet }}</pre>
          </div>
          <div>
            <md-button class="md-dense" @click="mcpExpanded = !mcpExpanded">
              {{ mcpExpanded ? 'Hide AI agent (MCP) setup' : 'Use with Claude Code, Cursor or another AI agent (MCP)' }}
            </md-button>
            <div v-if="mcpExpanded">
              <p>
                Laxy speaks
                <a href="https://modelcontextprotocol.io" target="_blank" rel="noopener">MCP</a>,
                so an agent can list jobs, inspect files and event logs, and download results.
              </p>
              <h4>Claude Code — one command</h4>
              <p class="hint">
                Run this in a terminal. Use <code>--scope project</code> instead to share it via a
                <code>.mcp.json</code> in the repo (that file would contain your key).
              </p>
              <pre class="snippet">{{ mcpCliSnippet }}</pre>
              <md-button class="md-dense md-raised" @click="copyText(mcpCliSnippet, 'Command copied.')">Copy</md-button>
              <h4>Or edit the config file directly</h4>
              <p class="hint">
                Add to <code>~/.cursor/mcp.json</code> or a project <code>.mcp.json</code>.
                Other MCP clients take the same <code>mcpServers</code> shape.
              </p>
              <pre class="snippet">{{ mcpJsonSnippet }}</pre>
              <md-button class="md-dense md-raised" @click="copyText(mcpJsonSnippet, 'Config copied.')">Copy</md-button>
              <p class="hint">
                The key is stored in that config file in plain text. Prefer a dedicated, expiring
                key for each agent, and revoke it here when you are done.
              </p>
            </div>
          </div>
        </md-whiteframe>

        <md-whiteframe md-elevation="1" class="pad-16" style="margin-top: 16px;">
          <h3>Create a new key</h3>
          <md-layout md-gutter md-vertical-align="center">
            <md-layout md-flex="40">
              <md-input-container>
                <label>Key name</label>
                <md-input v-model="newKeyName" @keyup.enter.native="createKey"></md-input>
              </md-input-container>
            </md-layout>
            <md-layout md-flex="25">
              <md-input-container>
                <label>Expiry</label>
                <md-select v-model="expiryPreset" name="expiry" id="expiry">
                  <md-option value="7">7 days</md-option>
                  <md-option value="30">30 days</md-option>
                  <md-option value="90">90 days</md-option>
                  <md-option value="never">Never</md-option>
                  <md-option value="custom">Custom datetime</md-option>
                </md-select>
              </md-input-container>
            </md-layout>
            <md-layout v-if="expiryPreset === 'custom'" md-flex="25">
              <md-input-container>
                <label>Expires at</label>
                <input type="datetime-local" v-model="customExpiry" class="datetime-input" />
              </md-input-container>
            </md-layout>
            <md-layout md-flex="10">
              <md-button
                class="md-raised md-primary"
                :disabled="creating || !newKeyName.trim()"
                @click="createKey"
              >
                <md-icon>add</md-icon>
                <span class="pad-8-sides">Create</span>
              </md-button>
            </md-layout>
          </md-layout>
          <p v-if="createError" class="error-text">{{ createError }}</p>
        </md-whiteframe>

        <md-table-card style="width: 100%; margin-top: 16px;">
          <md-toolbar>
            <h2 class="md-title">Your API keys</h2>
            <md-button class="md-icon-button" @click="loadKeys">
              <md-icon :class="{ spin: loading }">refresh</md-icon>
            </md-button>
          </md-toolbar>
          <p v-if="listError" class="error-text pad-16">{{ listError }}</p>
          <md-table>
            <md-table-header>
              <md-table-row>
                <md-table-head>Name</md-table-head>
                <md-table-head>Prefix</md-table-head>
                <md-table-head>Created</md-table-head>
                <md-table-head>Last used</md-table-head>
                <md-table-head>Expires</md-table-head>
                <md-table-head>Status</md-table-head>
                <md-table-head>Actions</md-table-head>
              </md-table-row>
            </md-table-header>
            <md-table-body>
              <md-table-row v-if="!loading && keys.length === 0">
                <md-table-cell colspan="7">No API keys yet.</md-table-cell>
              </md-table-row>
              <md-table-row v-for="key in keys" :key="key.id">
                <md-table-cell>{{ key.name }}</md-table-cell>
                <md-table-cell><code>{{ key.prefix }}…</code></md-table-cell>
                <md-table-cell>{{ formatDate(key.created_time) }}</md-table-cell>
                <md-table-cell>{{ formatDate(key.last_used_at) }}</md-table-cell>
                <md-table-cell>{{ key.expires_at ? formatDate(key.expires_at) : 'Never' }}</md-table-cell>
                <md-table-cell>{{ key.status }}</md-table-cell>
                <md-table-cell>
                  <md-button
                    v-if="key.status === 'active'"
                    class="md-dense md-accent"
                    :disabled="revokingId === key.id"
                    @click="confirmRevoke(key)"
                  >
                    Revoke
                  </md-button>
                </md-table-cell>
              </md-table-row>
            </md-table-body>
          </md-table>
        </md-table-card>
      </md-whiteframe>
    </md-layout>
  </md-layout>
</template>

<script lang="ts">
import Component, { mixins } from "vue-class-component";
import * as moment from "moment";

import { WebAPI } from "../web-api";
import { Snackbar } from "../snackbar";
import { CopyToClipboard } from "../clipboard-mixin";

interface ApiKeyRow {
  id: string;
  name: string;
  prefix: string;
  created_time: string;
  expires_at: string | null;
  last_used_at: string | null;
  status: "active" | "expired" | "revoked";
}

interface CreatedApiKey extends ApiKeyRow {
  key: string;
}

@Component({})
export default class ApiKeysPage extends mixins(CopyToClipboard) {
  public keys: ApiKeyRow[] = [];
  public loading = false;
  public creating = false;
  public listError: string | null = null;
  public createError: string | null = null;
  public newKeyName = "";
  public expiryPreset = "7";
  public customExpiry = "";
  public issuedKey: CreatedApiKey | null = null;
  public curlExpanded = false;
  public mcpExpanded = false;
  public revokingId: string | null = null;

  public get mcpUrl(): string {
    return `${WebAPI.baseUrl.replace(/\/$/, "")}/api/v1/mcp/`;
  }

  public formatDate(value: string | null): string {
    if (!value) {
      return "—";
    }
    return moment(value).format("Do MMM YYYY, HH:mm");
  }

  public get curlSnippet(): string {
    if (!this.issuedKey) {
      return "";
    }
    const origin = WebAPI.baseUrl.replace(/\/$/, "");
    return `curl -H "Authorization: Bearer ${this.issuedKey.key}" ${origin}/api/v1/user/profile/`;
  }

  public get mcpCliSnippet(): string {
    if (!this.issuedKey) {
      return "";
    }
    return [
      "claude mcp add --transport http --scope user laxy \\",
      `  ${this.mcpUrl} \\`,
      `  --header "Authorization: Bearer ${this.issuedKey.key}"`,
    ].join("\n");
  }

  public get mcpJsonSnippet(): string {
    if (!this.issuedKey) {
      return "";
    }
    return JSON.stringify(
      {
        mcpServers: {
          laxy: {
            type: "http",
            url: this.mcpUrl,
            headers: { Authorization: `Bearer ${this.issuedKey.key}` },
          },
        },
      },
      null,
      2
    );
  }

  public async created() {
    await this.loadKeys();
  }

  public async loadKeys() {
    this.loading = true;
    this.listError = null;
    try {
      const response = await WebAPI.listApiKeys();
      this.keys = response.data.keys || [];
    } catch (error) {
      this.listError = this.errorMessage(error, "Failed to load API keys");
    } finally {
      this.loading = false;
    }
  }

  public async createKey() {
    const name = this.newKeyName.trim();
    if (!name) {
      return;
    }
    this.creating = true;
    this.createError = null;
    try {
      const extras: { expires_in_days?: number | null; expires_at?: string | null } = {};
      if (this.expiryPreset === "never") {
        // omit both fields — never expires
      } else if (this.expiryPreset === "custom") {
        if (!this.customExpiry) {
          this.createError = "Choose an expiry datetime.";
          this.creating = false;
          return;
        }
        extras.expires_at = new Date(this.customExpiry).toISOString();
      } else {
        extras.expires_in_days = parseInt(this.expiryPreset, 10);
      }
      const response = await WebAPI.createApiKey(name, extras);
      this.issuedKey = response.data;
      this.curlExpanded = false;
      this.mcpExpanded = false;
      this.newKeyName = "";
      this.expiryPreset = "7";
      this.customExpiry = "";
      Snackbar.flashMessage(`API key "${response.data.name}" created.`, 4000);
      await this.loadKeys();
    } catch (error) {
      this.createError = this.errorMessage(error, "Failed to create API key");
    } finally {
      this.creating = false;
    }
  }

  public async confirmRevoke(key: ApiKeyRow) {
    if (
      !window.confirm(
        `Revoke API key "${key.name}"? Any client using it will stop working immediately.`
      )
    ) {
      return;
    }
    this.revokingId = key.id;
    try {
      await WebAPI.revokeApiKey(key.id);
      Snackbar.flashMessage(`API key "${key.name}" revoked.`, 4000);
      await this.loadKeys();
    } catch (error) {
      Snackbar.flashMessage(this.errorMessage(error, "Failed to revoke API key"), 5000);
    } finally {
      this.revokingId = null;
    }
  }

  public async copyIssuedKey() {
    if (!this.issuedKey) {
      return;
    }
    try {
      await this.setClipboard(this.issuedKey.key);
      Snackbar.flashMessage("API key copied to clipboard.", 3000);
    } catch (error) {
      const el = this.$refs.secretCode as HTMLElement | undefined;
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
      }
      Snackbar.flashMessage(
        "Clipboard unavailable — the key text has been selected so you can copy it.",
        6000
      );
    }
  }

  public async copyText(text: string, successDetail: string) {
    try {
      await this.setClipboard(text);
      Snackbar.flashMessage(successDetail, 3000);
    } catch (error) {
      Snackbar.flashMessage("Clipboard unavailable — select the text and copy it manually.", 6000);
    }
  }

  public errorMessage(error: unknown, fallback: string): string {
    const err = error as { response?: { data?: any }; message?: string };
    const data = err.response && err.response.data;
    if (data && typeof data === "object") {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      if (typeof data.name === "string") {
        return data.name;
      }
      if (Array.isArray(data.name)) {
        return data.name.join(" ");
      }
    }
    if (err.message) {
      return err.message;
    }
    return fallback;
  }
}
</script>

<style lang="scss" scoped>
.md-whiteframe {
  width: 100%;
}

.issued-panel {
  background: #fff8e1;
  margin-bottom: 8px;
}

.secret-box {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  word-break: break-all;
  margin: 8px 0;
}

.snippet {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.hint {
  font-size: 0.875rem;
  color: #495057;
}

.error-text {
  color: #c62828;
}

.datetime-input {
  margin-top: 18px;
  padding: 6px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
