<template>
  <div>
    <md-layout md-column md-gutter>
      <md-layout style="margin: 40px 10% 0 10%;" md-vertical-align="stretch" md-column>
        <md-whiteframe md-elevation="2" class="pad-32">
          <div class="pad-32" style="background: #2196f3">
            <h1 class="md-display-2" style="text-align: center">
              <span class="large-text logo-font" style="color: white;">Laxy</span> &nbsp;&nbsp;
              <span class="md-subheading" style="color: white;">
                <em>
                  Streamlined Genomics Pipelines
                  <!--
                  <span>
                    *
                    <md-tooltip
                      md-direction="bottom"
                    >Brought to you be the Monash Bioinformatics Platform</md-tooltip>
                  </span>
                  -->
                  <splash-texts>
                    <sup style="font-size: 8px">*</sup>
                  </splash-texts>
                </em>
              </span>
            </h1>
          </div>
          <md-layout md-align="start" md-column>
            <h1 class="md-display-1">Latest news</h1>
            <latest-news></latest-news>
            <h1 class="md-display-1">Launch a pipeline</h1>
            <router-link to="/run/rnaseq">
              <rna-seq-launch route-to="/run/rnaseq"></rna-seq-launch>
            </router-link>
            <variant-calls-launch></variant-calls-launch>
            <nullarbor-launch></nullarbor-launch>
          </md-layout>
        </md-whiteframe>
      </md-layout>
    </md-layout>
    <br />
  </div>
</template>


<script lang="ts">
import * as _ from "lodash";
import "es6-promise";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";
import CalloutBox from "./CalloutBox.vue";
import NullarborLaunch from "./FrontPageCards/NullarborLaunch.vue";
import VariantCallsLaunch from "./FrontPageCards/VariantCallsLaunch.vue";
import RnaSeqLaunch from "./FrontPageCards/RnaSeqLaunch.vue";
import LatestNews from "./FrontPageCards/LatestNews.vue";
import SplashTexts from "./FrontPageCards/SplashTexts.vue";

interface FrontPage extends Vue {}

export default Vue.extend({
  components: {
    // 'input-files-form': InputFilesForm
    "callout-box": CalloutBox,
    "splash-texts": SplashTexts,
    "latest-news": LatestNews,
    "rna-seq-launch": RnaSeqLaunch,
    "nullarbor-launch": NullarborLaunch,
    "variant-calls-launch": VariantCallsLaunch,
  },
  props: {},
  data() {
    return {};
  },
  methods: {},
  computed: {},
  watch: {},
}); // as ComponentOptions<RNASeqSetup>;
</script>
