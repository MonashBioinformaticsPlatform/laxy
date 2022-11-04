<template>
  <md-table>
    <md-table-header>
      <md-table-row>
        <md-table-head>Link</md-table-head>
        <md-table-head>Expires</md-table-head>
        <md-table-head style="text-align: right;">Action</md-table-head>
      </md-table-row>
    </md-table-header>
    <md-table-body>
      <md-table-row v-for="link in sharingLinks" :key="link.id">
        <md-table-cell>
          <a v-if="!linkIsExpired(link)" :id="link.id" :href="formatSharingLink(link)">
            <md-icon>link</md-icon>
            {{ formatSharingLink(link) | truncate }}
          </a>
          <span v-else>
            <md-icon>timer_off</md-icon>
            <span class="expired-link">{{ formatSharingLink(link) | truncate }}</span>
          </span>
        </md-table-cell>
        <md-table-cell>
          <span :class="{ 'expired-link': linkIsExpired(link) }">{{ formatExpiryString(link.expiry_time) }}</span>
          <md-menu v-if="allowExpiryEdit" md-size="4" class="push-left">
            <md-button class="md-icon-button" md-menu-trigger>
              <md-icon>arrow_drop_down</md-icon>
            </md-button>

            <md-menu-content>
              <span class="md-subheading" style="font-weight: bold; padding-left: 16px">Change expiry to</span>
              <!--  -->
              <md-menu-item v-for="expires_in in access_token_lifetime_options" :key="expires_in"
                @click="updateSharingLink(jobId, expires_in)">
                <span v-if="typeof expires_in == 'number'">{{ expires_in | duration('seconds').humanize() }} from
                  now</span>
                <span v-else>{{ expires_in }} expires</span>
              </md-menu-item>
            </md-menu-content>
          </md-menu>
        </md-table-cell>
        <md-table-cell md-numeric>
          <md-button v-if="!linkIsExpired(link)" class="md-icon-button push-right"
            @click="setClipboardFlash(formatSharingLink(link), 'Copied link to clipboard !')">
            <md-icon>file_copy</md-icon>
            <md-tooltip md-direction="top">Copy to clipboard</md-tooltip>
          </md-button>
          <md-button v-if="showDeleteButton" class="md-icon-button" :class="{ 'push-right': linkIsExpired(link) }"
            @click="deleteSharingLink(link.id)">
            <md-icon>delete</md-icon>
            <md-tooltip md-direction="top">Delete</md-tooltip>
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

import { Memoize } from "lodash-decorators";

import * as moment from "moment";

import { WebAPI } from "../web-api";

import { CopyToClipboard } from '../clipboard-mixin';

@Component({
  filters: {},
})
export default class SharingLinkList extends mixins(CopyToClipboard) {
  @Prop({ type: String })
  public jobId: string;

  @Prop({ type: Array })
  public sharingLinks: any[];

  @Prop({ type: Boolean, default: true })
  public showDeleteButton: boolean;

  @Prop({ type: Boolean, default: true })
  public allowExpiryEdit: boolean;

  private _days = 24 * 60 * 60; // seconds in a day
  public access_token_lifetime_options: any[] = [
    1 * this._days,
    2 * this._days,
    7 * this._days,
    30 * this._days,
    "Never (∞)",
  ];

  formatSharingLink(link: any) {
    const rel = `#/job/${link.object_id}/?access_token=${link.token}`;
    return this.relToFullLink(rel);
  }

  relToFullLink(rel_link: string) {
    const tmp_a = document.createElement("a") as HTMLAnchorElement;
    tmp_a.href = rel_link;
    const abs_link = tmp_a.href;
    return abs_link;
  }

  @Memoize((link: any) => link.id)
  linkIsExpired(link: any) {
    return moment(link.expiry_time).isBefore(Date.now());
  }

  formatExpiryString(expiry_time: Date | null, add_sentence_words?: boolean) {
    if (expiry_time == null) {
      if (add_sentence_words) {
        return ", never expires";
      } else {
        return "Never";
      }
    }
    const m = moment(expiry_time);
    let suffix = "from now";
    if (m.isBefore(Date.now())) {
      suffix = "ago";
    }
    let formatted = `${m.fromNow(true)} ${suffix} on ${m.format(
      "DD-MMM-YYYY (HH:mm UTCZ)"
    )}`;
    if (add_sentence_words) {
      formatted = ` until ${formatted}`;
    }
    return formatted;
  }

  async updateSharingLink(job_id: string, expires_in: number | string) {
    this.$emit("change-link", { job_id: job_id, expires_in: expires_in });
  }

  async deleteSharingLink(link_id: string) {
    this.$emit("delete-link", link_id);
  }

}
</script>
