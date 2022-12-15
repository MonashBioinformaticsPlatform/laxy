<template>
  <md-layout md-column md-gutter>
    <md-layout style="margin: 24px" md-vertical-align="stretch" md-column>
      <md-whiteframe md-elevation="2" class="pad-32">

        <md-card>
          <md-card-header>
            <md-card-header-text class="pad-16">
              <div class="md-title">User Profile</div>
              <div class="md-subhead">{{ full_name }}</div>
            </md-card-header-text>

            <md-card-media class="pad-16">
              <img :src="profile_pic_url" alt="People">
            </md-card-media>
          </md-card-header>

          <md-card-content>
            <md-table>
              <md-table-row>
                <md-table-cell><strong>Name</strong></md-table-cell>
                <md-table-cell>{{ full_name }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Username</strong></md-table-cell>
                <md-table-cell>{{ username }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Email address</strong></md-table-cell>
                <md-table-cell>{{ email }}</md-table-cell>
              </md-table-row>
              <md-table-row>
                <md-table-cell><strong>Laxy user ID</strong></md-table-cell>
                <md-table-cell>{{ user_id }}</md-table-cell>
              </md-table-row>
            </md-table>
          </md-card-content>
        </md-card>

        <p>
          <md-whiteframe class="pad-16">
            <md-layout class="pad-8" md-vertical-align="center">
              <h3>Secret API token (JWT)</h3>
              <md-button id="helpButton" @click="openDialog('helpPopup')" class="md-icon-button md-raised md-dense">
                <md-icon style="color: #bdbdbd;">help</md-icon>
              </md-button>
            </md-layout>
            <md-layout md-column>
              <textarea readonly rows="4" class="token-area" :class="{ 'blur-text': hideToken }"
                v-model="masked_api_auth_token" style="resize: none; overflow: auto; word-break: break-all;">
            </textarea>
            </md-layout>

            <md-button class="md-raised" @click="toggleTokenVisibility()">
              <md-icon>visibility</md-icon><span class="pad-8-sides">Reveal token</span>
            </md-button>
            <md-button class="md-raised" @click="copyTokenToClipboard()">
              <md-icon>content_copy</md-icon><span class="pad-8-sides">Copy token to clipboard</span>
            </md-button>
          </md-whiteframe>
        </p>
      </md-whiteframe>
    </md-layout>
    <md-dialog md-open-from="#helpButton" md-close-to="#helpButton" id="helpPopup" ref="helpPopup">
      <md-dialog-title>API token help</md-dialog-title>

      <md-dialog-content>
        <p>
          You should treat this token as secret, since it allows access to your Laxy account and associated
          data.
          You can use this token in an HTTPS request header like <code>Authorization: Bearer {token_here}</code> when
          using the <a :href="`${openAPIUrl}`">Laxy Web API</a>.
          This token can also be used with the <a
            href="https://github.com/MonashBioinformaticsPlatform/laxyapi-r">laxyapi R package</a> (see vignette
          for example). Tokens expire after some time.
        </p>
      </md-dialog-content>

      <md-dialog-actions>
        <md-button class="md-primary" @click="closeDialog('helpPopup')">Close</md-button>
      </md-dialog-actions>
    </md-dialog>
  </md-layout>
</template>

<script lang="ts">
import get from "lodash-es/get";
import isString from "lodash-es/isString";

import Vue from "vue";
import Component, { mixins } from "vue-class-component";

import { Prop } from "vue-property-decorator";

import {
  AUTHENTICATE_USER,
  FETCH_PIPELINES,
  SET_GLOBAL_SNACKBAR,
  SET_USER_PROFILE,
} from "../store";
import { WebAPI } from "../web-api";

import { Snackbar } from "../snackbar";

import { CopyToClipboard } from '../clipboard-mixin';

@Component({})
export default class UserProfile extends mixins(CopyToClipboard) {

  public hideToken = true;

  public get is_authenticated(): boolean {
    return this.$store.getters.is_authenticated;
  }

  public get full_name(): string {
    const name = get(this.$store.state.user_profile, "full_name", null);
    if (!name || (isString(name) && !name.trim())) {
      return "Anonymous User";
    }
    return name;
  }

  public get username(): string {
    return get(this.$store.state.user_profile, "username", "anonymous");
  }

  public get user_id(): string {
    return get(this.$store.state.user_profile, "id", null);
  }

  public get email(): string {
    return get(this.$store.state.user_profile, "email", null);
  }

  public get profile_pic_url(): string {
    return get(this.$store.state.user_profile, "profile_pic", null);
  }

  public get openAPIUrl(): string {
    return WebAPI.baseUrl + "/swagger/v1/";
  }

  public get api_auth_token(): string {
    return get(this.$store.state.user_profile, "token", "");
  }

  public get masked_api_auth_token(): string {
    const token: string = this.api_auth_token;
    if (this.hideToken) {
      return "•".repeat(token.length)
    }

    return token;
  }

  toggleTokenVisibility() {
    this.hideToken = !this.hideToken;
  }

  copyTokenToClipboard() {
    // from CopyToClipboard mixin
    this.setClipboardFlash(this.api_auth_token, "Secret API token copied to clipboard");
  }

  openDialog(refName: string) {
    // console.log('Opened: ' + refName);
    ((this.$refs as any)[refName] as any).open();
  }

  closeDialog(refName: string) {
    // console.log('Closed: ' + refName);
    ((this.$refs as any)[refName] as any).close();
  }

  public async created() { }
}
</script>

<style lang="scss" scoped>
.md-card {
  width: 100%;
}

.md-whiteframe {
  width: 100%;
}

.token-area {
  overflow: auto;
  word-break: break-all;
  width: 100%;
  resize: none;
}

.blur-text {
  color: transparent !important;
  text-shadow: 0 0 8px rgba(0, 0, 0, 0.5) !important;
}
</style>
