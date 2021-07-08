<template>
  <div>
    <md-layout md-column md-gutter>
      <md-layout
        style="margin: 40px 10% 0 10%; max-width: 600px;"
        md-vertical-align="stretch"
        md-column
      >
        <md-whiteframe md-elevation="2">
          <md-layout md-align="start" md-column>
            <md-whiteframe md-elevation="8" class="pad-32">
              <h1 class="md-display-1">About Laxy</h1>

              Laxy is a web application designed to streamline access to large
              computing resources for bioinformatics. It is developed and
              maintained by the Monash Bioinformatics Platform, with compute and
              storage support from Monash eResearch.

              <h2 class="md-display-1">Laxy is open source</h2>
              Laxy is already useful, but is also under constant development to
              fix bugs and add new features. Your bug reports and feedback (and
              pull requests !) are appreciated.<br />
              <p>
                <a
                  href="https://github.com/MonashBioinformaticsPlatform/laxy/issues"
                  target="_blank"
                  >Please report issues and suggestions on Github</a
                >
                &nbsp;
                <a
                  href="https://github.com/MonashBioinformaticsPlatform/laxy/issues"
                  target="_blank"
                  style="text-decoration: none"
                >
                  <md-icon
                    md-iconset="ion-logo-github"
                    class="md-size-1x"
                    style="padding-bottom: 4px"
                  >
                  </md-icon>
                </a>
              </p>

              <h2 class="md-display-1">
                Citing Laxy
              </h2>
              If Laxy has contributed to the work in your manuscript, please
              cite it as:
              <div class="pad-32">
                <a href="https://doi.org/10.5281/zenodo.3767371"
                  >https://doi.org/10.5281/zenodo.3767371</a
                >
              </div>
            </md-whiteframe>
          </md-layout>
        </md-whiteframe>
      </md-layout>
    </md-layout>
    <br />
  </div>
</template>


<script lang="ts">
import "es6-promise";

import Vue, { ComponentOptions } from "vue";

interface AboutPage extends Vue {}

export default Vue.extend({
  components: {},
  props: {},
  data() {
    return {};
  },
  methods: {},
  computed: {},
  watch: {}
});
</script>
