<template>
  <md-whiteframe class="pad-32">
    <div v-for="item of newsItems" :key="item.date">
      <div class="pad-16-sides" :style="cssStripe(stripeColor, 'left', 4)">
        <h3 class="md-subheading">
          <span class="md-caption">{{ item.date }}</span>
          <br />
          {{ item.title}}
        </h3>

        <span class="md-body-1">
          <vue-markdown>{{ item.text }}</vue-markdown>
        </span>
      </div>
    </div>
  </md-whiteframe>
</template>


<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";
import { Prop } from "vue-property-decorator";

import VueMarkdown from "vue-markdown";

import { cssStripe, getThemeColor, palette } from "../../palette";

@Component({
  components: { VueMarkdown },
  filters: {},
})
export default class LatestNews extends Vue {
  cssStripe = cssStripe;
  getThemeColor = getThemeColor;

  get stripeColor() {
    // return getThemeColor('primary');
    return palette.grey["300"];
  }

  newsItems: any[] = [
    {
      date: "18-Aug-2020",
      title: "User-supplied reference genomes are here !",
      text:
        "We recently added the ability to provide your own reference genome (FASTA + GTF/GFF) for RNA-Seq. This includes the ability to pull in reference genomes hosted on FTP sites, such as Ensembl. This feature should be considered experimental, since there are known cases (particularly for draft genomes with many small contigs) where the STAR index will fail to build.",
    },
  ];
}
</script>