<template>
  <md-layout md-gutter>
    <div v-show="show_fileselect_slideout">
      <md-sidenav id="fileSelectSlideout" ref="fileSelectSlideout" class="md-right slideout-right wideSideNav"
        @open="openSlideout('fileSelectSlideout')" @close="closeSlideout('fileSelectSlideout')">
        <md-toolbar>
          <div class="md-toolbar-container">
            <h3 class="md-title">Select remote files</h3>
            <div class="push-right">
              <md-button @click="toggleSlideout('fileSelectSlideout')" class="md-icon-button md-mini md-dense md-clean">
                <md-icon>close</md-icon>
              </md-button>
            </div>
          </div>
        </md-toolbar>
        <remote-files-select :show-about-box="false" :show-buttons="true" :single-select="true"
          :auto-select-pair="false" add-button-label="Select" :start-url="custom_genome_fileselect_url"
          @files-added="addCustomGenomeFiles"
          :placeholder="`${ensemblReleaseUrl}/fasta/vicugna_pacos/dna/`"></remote-files-select>
      </md-sidenav>
    </div>
    <md-layout md-flex="100" md-column>
      <h3>Reference genome</h3>
      <transition name="fade">
        <div v-if="!use_custom_genome">
          <md-input-container>
            <label for="genome_organism">Species</label>
            <md-select name="genome_organism" id="genome_organism" :required="true" v-model="selected_genome_organism"
              @change="onOrganismChange">
              <md-option v-for="organism in genome_organism_list" :key="organism" :value="organism">{{
                organism
              }}</md-option>
            </md-select>
          </md-input-container>
          <md-input-container>
            <label for="genome">Reference genome</label>
            <md-select name="genome" id="genome" :required="true" v-model="reference_genome">
              <md-option v-for="genome in genomes_for_organism(selected_genome_organism)" :key="genome.id"
                :value="genome.id">{{ get_genome_description(genome) }}</md-option>
            </md-select>
          </md-input-container>
        </div>
      </transition>
      <md-switch v-model="use_custom_genome" id="custom-genome-toggle" name="custom-genome-toggle"
        class="md-primary">Use an externally provided reference genome</md-switch>
      <transition name="fade">
        <div v-if="use_custom_genome">
          <md-layout md-column>
            <banner-notice :show-close-button="false" class="shadow" type="warning">User-supplied reference genomes are
              currently experimental. In
              particular, draft genomes with many small contigs are likely to
              fail when building a STAR index.</banner-notice>
            <md-whiteframe md-elevation="8">
              <md-layout md-column class="pad-32">
                <md-input-container>
                  <md-icon v-if="!fasta_url_valid" class="md-warn">
                    warning
                    <md-tooltip>Invalid URL, or missing expected file extension
                      !</md-tooltip>
                  </md-icon>
                  <label for="custom-genome-fasta">
                    Reference genome sequence (.fasta, .fasta.gz)
                    <span>
                      <md-icon style="font-size: 16px">info</md-icon>
                      <md-tooltip md-direction="right">A URL to a gzipped FASTA format reference genome, eg
                        {{
                          ensemblReleaseUrl
                        }}/fasta/vicugna_pacos/dna/Vicugna_pacos.vicPac1.dna.toplevel.fa.gz</md-tooltip>
                    </span>
                  </label>
                  <md-input v-model="custom_genome_fasta_url" id="custom-genome-fasta" :readonly="false"
                    @change="onFastaUrlChange" :placeholder="
                      `URL to FASTA (eg ${ensemblReleaseUrl}/fasta/vicugna_pacos/dna/Vicugna_pacos.vicPac1.dna.toplevel.fa.gz)`
                    "></md-input>
                  <md-button class="md-icon-button" @click="toggleFileSelect(`${ensemblReleaseUrl}/fasta/`)">
                    <md-icon type="submit">attach_file</md-icon>
                  </md-button>
                </md-input-container>

                <md-input-container>
                  <md-icon v-if="!annotation_url_valid" class="md-warn">
                    warning
                    <md-tooltip>Invalid URL, or missing expected file extension
                      !</md-tooltip>
                  </md-icon>
                  <label for="custom-genome-annotation">
                    Reference genome annotation (.gtf, .gff, gtf.gz, .gff3.gz)
                    <span>
                      <md-icon style="font-size: 16px">info</md-icon>
                      <md-tooltip md-direction="right">A URL to a gzipped GTF or GFF format genome annotation,
                        eg
                        {{
                          ensemblReleaseUrl
                        }}/gtf/vicugna_pacos/Vicugna_pacos.vicPac1.97.gtf.gz</md-tooltip>
                    </span>
                  </label>
                  <md-input v-model="custom_genome_annotation_url" id="custom-genome-annotation" :readonly="false"
                    @change="onAnnotationUrlChange" :placeholder="
                      `URL to GTF / GFF (eg ${ensemblReleaseUrl}/gtf/vicugna_pacos/Vicugna_pacos.vicPac1.97.gtf.gz)`
                    "></md-input>
                  <md-button class="md-icon-button" @click="toggleFileSelect(`${ensemblReleaseUrl}/gtf/`)">
                    <md-icon type="submit">attach_file</md-icon>
                  </md-button>
                </md-input-container>
              </md-layout>
            </md-whiteframe>
          </md-layout>
        </div>
      </transition>
    </md-layout>
  </md-layout>
</template>

<script lang="ts">
import set from "lodash-es/set";
import filter from "lodash-es/filter";
import cloneDeep from "lodash-es/cloneDeep";
import get from "lodash-es/get";
import find from "lodash-es/find";
import map from "lodash-es/map";
import some from "lodash-es/some";
import every from "lodash-es/every";
import { Memoize } from "lodash-decorators";

import "es6-promise";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch
} from "vue-property-decorator";
import { FileListItem } from "../file-tree-util";
import { Sync } from "vuex-pathify";

import AVAILABLE_GENOMES from "../config/genomics/genomes";

import RemoteFilesSelect from "./RemoteSelect/RemoteFilesSelect.vue";
import RemoteFileSelectAboutBox from "./RemoteSelect/RemoteFileSelectAboutBox.vue";

import BannerNotice from "./BannerNotice.vue";

import { ReferenceGenome } from "../types";
import { isValidUrl } from "../util";

@Component({
  components: { RemoteFilesSelect, BannerNotice },
  filters: {}
})
export default class SelectGenome extends Vue {
  ensemblRelease: string = "111";
  public ensemblReleaseUrl: string = `http://ftp.ensembl.org/pub/release-${this.ensemblRelease}`;

  @Sync("pipelineParams@user_genome.fasta_url")
  public custom_genome_fasta_url: string;

  @Sync("pipelineParams@user_genome.annotation_url")
  public custom_genome_annotation_url: string;

  @Sync("pipelineParams@genome")
  public reference_genome: string;

  public custom_genome_fileselect_url: string = "";

  @Prop({ default: () => AVAILABLE_GENOMES, type: Array })
  public genomes: Array<ReferenceGenome>;

  @Sync("use_custom_genome")
  public use_custom_genome: boolean;

  @Watch("use_custom_genome")
  onCustomGenomeToggle(newVal: boolean, oldVal: boolean) {
    this.update_genome_values_valid();
  }

  // This variable is used in addition to the toggle()/open()/close()
  // methods on the mdSidenav component, since toggling closed doesn't
  // properly hide the component (eg if we scroll to the right in an MdStepper)
  // TODO: This isn't ideal, since we skip the open/close animation. Patching
  // mdSidenav with a v-show tied to the end of the open/close animation
  // would be better.
  public show_fileselect_slideout = false;

  public fasta_url_valid = true;
  public annotation_url_valid = true;

  ref_sequence_extensions = [
    ".fasta.gz",
    ".fasta",
    ".fa",
    ".fa.gz",
    ".fna",
    ".fna.gz"
  ];
  ref_annotation_extensions = [
    ".gtf.gz",
    ".gff.gz",
    ".gff3.gz",
    ".gtf",
    ".gff",
    ".gff3"
  ];

  get selected_genome_organism(): string {
    return (
      this.get_organism_from_genome_id(
        this.$store.state.pipelineParams.genome
      ) || "Homo sapiens"
    );
  }

  set selected_genome_organism(organism: string) {
    const id =
      this.get_first_genome_id_for_organism(organism) ||
      this.genomes[0].id;
    this.$store.set("pipelineParams@genome", id);
  }

  get genome_organism_list(): string[] {
    let organisms = new Set<string>();
    for (let g of this.genomes) {
      organisms.add(g.organism);
    }
    return Array.from(organisms.values());
  }

  @Memoize
  genomes_for_organism(organism: string): ReferenceGenome[] {
    const organism_genomes: ReferenceGenome[] = [];
    for (let g of this.genomes) {
      if (g.organism === organism) {
        organism_genomes.push(g);
      }
    }
    return organism_genomes;
  }

  @Memoize
  get_organism_from_genome_id(genome_id: string): string | undefined {
    return get(find(this.genomes, { id: genome_id }), "organism");
  }

  @Memoize
  get_first_genome_id_for_organism(organism: string): string | undefined {
    return get(find(this.genomes, { organism: organism }), "id");
  }

  @Memoize
  get_genome_description(reference: ReferenceGenome): string {
    const [org, centre, build] = reference.id.split("/");
    // return `${build} [${centre}] (${reference.organism})`;
    let desc = `${build} [${centre}]`;
    if (reference.recommended) {
      desc = `${desc} (recommended)`;
    }
    return desc;
  }

  update_genome_values_valid() {
    let valid = false;
    if (this.use_custom_genome) {
      valid =
        this.custom_genome_fasta_url !== "" &&
        this.custom_genome_annotation_url !== "" &&
        this.fasta_url_valid &&
        this.annotation_url_valid;
    } else {
      valid = this.$store.get("pipelineParams@genome") != null;
    }

    this.$store.set("genome_values_valid", valid);

    return valid;
  }

  onOrganismChange(e: any) {
    this.reference_genome = this.genomes_for_organism(
      this.selected_genome_organism
    )[0].id;
  }

  onFastaUrlChange(url: any) {
    this.fasta_url_valid =
      (url && isValidUrl(url, ["http", "https", "ftp"])) ||
      this.custom_genome_fasta_url === "";

    this.update_genome_values_valid();
  }

  onAnnotationUrlChange(url: any) {
    this.annotation_url_valid =
      (url && isValidUrl(url, ["http", "https", "ftp"])) ||
      this.custom_genome_annotation_url === "";

    this.update_genome_values_valid();
  }

  async addCustomGenomeFiles(addedFiles: FileListItem[]) {
    for (let f of addedFiles) {
      for (let ext of this.ref_sequence_extensions) {
        if (f.name.endsWith(ext)) {
          this.custom_genome_fasta_url = f.location;
          this.onFastaUrlChange(this.custom_genome_fasta_url);
        }
      }
      for (let ext of this.ref_annotation_extensions) {
        if (f.name.endsWith(ext)) {
          this.custom_genome_annotation_url = f.location;
          this.onAnnotationUrlChange(this.custom_genome_annotation_url);
        }
      }
    }

    this.toggleFileSelect();
    const el = document.getElementById("_top"); // this.$refs['custom-genome-section'] as Element;
    // el.scrollIntoView({behavior: "smooth", block: "start"});
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    // el.scrollTo(0, 0);
  }

  toggleFileSelect(url?: string) {
    this.custom_genome_fileselect_url = url || "";
    this.toggleSlideout("fileSelectSlideout");
  }

  toggleSlideout(refName: string) {
    const sidenav = (this.$refs as any)[refName] as any;
    sidenav.toggle();
  }

  openSlideout(ref: string) {
    if (ref === "fileSelectSlideout") {
      this.show_fileselect_slideout = true;
    }
    // console.log('Opened: ' + ref);
  }

  closeSlideout(ref: string) {
    if (ref === "fileSelectSlideout") {
      this.show_fileselect_slideout = false;
    }
    // console.log('Closed: ' + ref);
  }
}
</script>
