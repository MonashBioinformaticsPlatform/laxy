<template>
    <div>
        <md-dialog-alert :md-content-html="error_alert_message"
                         :md-content="error_alert_message" ref="error_dialog">
        </md-dialog-alert>
        <md-sidenav id="fileSelectSlideout"
                    ref="fileSelectSlideout"
                    class="md-right slideout-right"
                    @open="openSlideout('fileSelectSlideout')"
                    @close="closeSlideout('fileSelectSlideout')">
            <md-toolbar>
                <div class="md-toolbar-container">
                    <h3 class="md-title">Select remote files</h3>
                    <div class="push-right">
                        <md-button @click="toggleSlideout('fileSelectSlideout')"
                                   class="md-icon-button md-mini md-dense md-clean">
                            <md-icon>close</md-icon>
                        </md-button>
                    </div>
                </div>
            </md-toolbar>
            <remote-files-select
                    :show-about-box="false" :show-buttons="true"
                    :single-select="true" :auto-select-pair="false"
                    add-button-label="Select"
                    :start-url="custom_genome_fileselect_url"
                    @files-added="addCustomGenomeFiles"
                    placeholder="http://ftp.ensembl.org/pub/release-97/fasta/vicugna_pacos/dna/">
            </remote-files-select>
        </md-sidenav>

        <banner-notice v-if="!isValid_samples_added" type="error" :show-close-button="false">
            Please add some samples before submitting your job.
        </banner-notice>
        <banner-notice v-if="!isValid_reference_genome" type="error" :show-close-button="false">
            Selected reference genome is invalid.
        </banner-notice>
        <md-layout md-column>
            <form novalidate>
                <md-whiteframe style="padding: 32px;">
                    <h2 id="_top">RNAsik</h2>
                    <h3>Pipeline parameters</h3>
                    <md-input-container>
                        <label>Description</label>
                        <md-input v-model="description" placeholder="Description of pipeline run ..."></md-input>
                    </md-input-container>
                    <md-input-container v-if="!show_custom_genome">
                        <label for="genome-organism">Species</label>
                        <md-select name="genome-organism"
                                   id="genome-organism"
                                   :required="true"
                                   v-model="selected_genome_organism"
                                   @change="onOrganismChange">
                            <md-option v-for="organism in genome_organism_list"
                                       :key="organism"
                                       :value="organism">
                                {{ organism }}
                            </md-option>
                        </md-select>
                    </md-input-container>
                    <transition name="fade">
                        <md-input-container v-if="!show_custom_genome">
                            <label for="genome">Reference genome</label>
                            <md-select name="genome"
                                       id="genome"
                                       :required="true"
                                       v-model="reference_genome">
                                <md-option v-for="genome in genomes_for_organism(selected_genome_organism)"
                                           :key="genome.id"
                                           :value="genome.id">
                                    {{ get_genome_description(genome) }}
                                </md-option>
                            </md-select>
                        </md-input-container>
                    </transition>
                    <md-switch v-model="show_custom_genome"
                               id="custom-genome-toggle"
                               name="custom-genome-toggle"
                               class="md-primary">
                        Use a custom reference genome
                    </md-switch>
                    <transition name="fade">

                        <md-layout md-column>
                            <md-whiteframe md-elevation="8">
                                <md-layout md-column class="pad-32" v-if="show_custom_genome">
                                    <md-input-container>
                                        <label for="custom-genome-fasta">Reference genome sequence (.fasta.gz)
                                            <span>
                                            <md-icon style="font-size: 16px;">info</md-icon>
                                            <md-tooltip md-direction="right">A URL to a gzipped FASTA format reference genome, eg http://ftp.ensembl.org/pub/release-97/fasta/vicugna_pacos/dna/Vicugna_pacos.vicPac1.dna.toplevel.fa.gz</md-tooltip>
                                        </span>
                                        </label>
                                        <md-input v-model="custom_genome_fasta_url"
                                                  id="custom-genome-fasta"
                                                  :readonly="false"
                                                  placeholder="http://ftp.ensembl.org/pub/release-97/fasta/vicugna_pacos/dna/Vicugna_pacos.vicPac1.dna.toplevel.fa.gz"></md-input>
                                        <md-button class="md-icon-button"
                                                   @click="toggleFileSelect('http://ftp.ensembl.org/pub/release-97/fasta/')">
                                            <md-icon type="submit">attach_file</md-icon>
                                        </md-button>
                                    </md-input-container>

                                    <md-input-container>
                                        <label for="custom-genome-annotation">Reference genome annotation (.gtf, .gff,
                                            gtf.gz, .gff3.gz)
                                            <span>
                                            <md-icon style="font-size: 16px;">info</md-icon>
                                            <md-tooltip md-direction="right">A URL to a gzipped GTF or GFF format genome annotation, eg https://ftp.ensembl.org/pub/release-97/gtf/vicugna_pacos/Vicugna_pacos.vicPac1.97.gtf.gz</md-tooltip>
                                        </span>
                                        </label>
                                        <md-input v-model="custom_genome_annotation_url"
                                                  id="custom-genome-annotation"
                                                  :readonly="false"
                                                  placeholder="http://ftp.ensembl.org/pub/release-97/gtf/vicugna_pacos/Vicugna_pacos.vicPac1.97.gtf.gz"></md-input>
                                        <md-button class="md-icon-button"
                                                   @click="toggleFileSelect('http://ftp.ensembl.org/pub/release-97/gtf/')">
                                            <md-icon type="submit">attach_file</md-icon>
                                        </md-button>
                                    </md-input-container>
                                </md-layout>
                            </md-whiteframe>
                        </md-layout>

                    </transition>
                    <md-switch v-model="show_advanced" id="advanced-toggle" name="advanced-toggle" class="md-primary">
                        Show advanced options
                    </md-switch>
                    <transition name="fade">
                        <md-layout v-if="show_advanced">
                            <md-input-container v-if="show_advanced">
                                <label for="genome">Pipeline version</label>
                                <md-select name="pipeline-version"
                                           id="pipeline-version"
                                           v-model="pipeline_version">
                                    <md-option v-for="version in pipeline_versions"
                                               :key="version"
                                               :value="version">
                                        {{ version }}
                                    </md-option>
                                </md-select>
                            </md-input-container>
                        </md-layout>
                    </transition>
                </md-whiteframe>
            </form>

            <md-whiteframe style="padding: 32px;">
                <h3>Sample summary</h3>
                <sample-cart v-if="samples.items.length > 0"
                             :samples="samples"
                             :fields="['name', 'metadata.condition', 'R1', 'R2']"
                             :show-toolbar="false"
                             :show-add-menu="false"
                             :show-buttons="false"
                             :editable-set-name="false"
                             :selectable="false"
                             @selected="onSelect"></sample-cart>
                <div v-if="samples.items.length === 0">
                    No samples in cart.
                </div>
            </md-whiteframe>
            <md-layout v-if="showButtons">
                <md-button class="md-primary md-raised" @click="save">
                    Save
                </md-button>
                <md-button :disabled="isValid_params" class="md-primary md-raised" @click="run">
                    Run the pipeline
                </md-button>
            </md-layout>
        </md-layout>

        <md-snackbar md-position="bottom center" ref="snackbar"
                     :md-duration="snackbar_duration">
            <span>{{ snackbar_message }}</span>
            <md-button class="md-accent" @click="$refs.snackbar.close()">
                Dismiss
            </md-button>
        </md-snackbar>
    </div>
</template>


<script lang="ts">
    import cloneDeep from "lodash-es/cloneDeep";
    import get from "lodash-es/get";
    import find from "lodash-es/find";
    import map from "lodash-es/map";
    import {Memoize} from "lodash-decorators";

    import "es6-promise";

    import axios, {AxiosResponse} from "axios";
    import Vue, {ComponentOptions} from "vue";
    import Component from "vue-class-component";
    import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";
    
    import {Get, Sync, Call} from 'vuex-pathify';

    import {
        SET_SAMPLES,
        CLEAR_SAMPLE_CART,
    } from "../store";

    import {Sample, SampleCartItems} from "../model";
    import {WebAPI} from "../web-api";

    import AVAILABLE_GENOMES from "../config/genomics/genomes";

    import {DummySampleList as _dummySampleList} from "../test-data";
    import {DummyPipelineConfig as _dummyPipelineConfig} from "../test-data";
    import {Snackbar} from "../snackbar";
    import BannerNotice from "./BannerNotice.vue";
    import RemoteFilesSelect from "./RemoteSelect/RemoteFilesSelect";
    import {FileListItem} from "../file-tree-util";
    import {filenameFromUrl} from "../util";
    // import RemoteFileSelectAboutBox from "./RemoteSelect/RemoteFileSelectAboutBox";

    @Component({
        components: {
            BannerNotice,
            RemoteFilesSelect,
        },
        props: {},
        filters: {},
        beforeRouteLeave(to: any, from: any, next: any) {
            (this as any).beforeRouteLeave(to, from, next);
        }
    })
    export default class PipelineParams extends Vue {

        @Prop({default: true, type: Boolean})
        public showButtons: boolean;
        public show_advanced = false;
        public show_custom_genome = false;

        public submitting: boolean = false;
        public error_alert_message: string = "Everything is fine. 🏩";
        public snackbar_message: string = "Everything is fine. ௐ";
        public snackbar_duration: number = 2000;

        public pipelinerun_uuid: string | null = null;
        public selectedSamples: Array<Sample> = [];

        public available_genomes: Array<ReferenceGenome> = AVAILABLE_GENOMES;

        public reference_genome_valid: boolean = true;

        get selected_genome_organism(): string {
            return this.get_organism_from_genome_id(this.$store.state.pipelineParams.genome)
                || 'Homo sapiens';
        }

        set selected_genome_organism(organism: string) {
            const id = this.get_first_genome_id_for_organism(organism)
                || AVAILABLE_GENOMES[0].id;
            this.$store.set('pipelineParams@genome', id);
        }

        public pipeline_versions = ['1.5.3', '1.5.2', '1.5.3-laxydev', '1.5.4'];

        public _samples: SampleCartItems;
        get samples(): SampleCartItems {
            this._samples = cloneDeep(this.$store.state.samples);
            // We do this so that if samples change validation runs
            const _ = this.isValid_params;
            return this._samples;
        }

        @Sync('pipelineParams@description')
        public description: string;

        @Sync('pipelineParams@custom_genome.fasta_url')
        public custom_genome_fasta_url: string;

        @Sync('pipelineParams@custom_genome.annotation_url')
        public custom_genome_annotation_url: string;

        @Sync('pipelineParams@genome')
        public reference_genome: string;

        @Sync('pipelineParams@pipeline_version')
        public pipeline_version: string;

        public custom_genome_fileselect_url: string = '';

        get genome_organism_list(): string[] {
            let organisms = new Set();
            for (let g of this.available_genomes) {
                organisms.add(g.organism);
            }
            organisms.add("Custom genome");
            return Array.from(organisms.values());
        }

        @Memoize
        genomes_for_organism(organism: string): ReferenceGenome[] {
            const genomes: ReferenceGenome[] = [];
            for (let g of this.available_genomes) {
                if (g.organism === organism) {
                    genomes.push(g);
                }
            }
            return genomes;
        }

        @Memoize
        get_organism_from_genome_id(genome_id: string): string | undefined {
            return get(find(AVAILABLE_GENOMES, {'id': genome_id}), 'organism');
        }

        @Memoize
        get_first_genome_id_for_organism(organism: string): string | undefined {
            return get(find(AVAILABLE_GENOMES,
                {'organism': organism}), 'id');
        }

        @Memoize
        get_genome_description(reference: ReferenceGenome): string {
            const [org, centre, build] = reference.id.split('/');
            // return `${build} [${centre}] (${reference.organism})`;
            let desc = `${build} [${centre}]`;
            if (reference.recommended) {
                desc = `${desc} (recommended)`;
            }
            return desc;
        }

        onOrganismChange(e: any) {
            this.reference_genome = this.genomes_for_organism(this.selected_genome_organism)[0].id;
        }

        created() {
            this._samples = cloneDeep(this.$store.state.samples);
        }

        prepareData() {
            let data: any = {
                "sample_cart": this.$store.state.samples.id,
                "params": cloneDeep(this.$store.get('pipelineParams')),
                "pipeline": "rnasik",
                "description": this.description,
            };

            // TODO: Idea - make a 'files' (or 'input_files') attribute here, with a list of
            //       input files that laxydl will grab. We could phase out 'sample_cart' and put sample files in here too.
            //       An extension to this idea would be to use the API to create an FileSet and just pass the ID of the FileSet here
            //       views.JobCreate would populate, PipelineConfig.metdata.files which becomes `pipeline_config.json` on the compute node.
            // "input_files": [{location: this.$store.getters.pipelineParams.custom_genome.fasta_url, type_tags: ['reference', 'fasta']},
            //                 {location: this.$store.getters.pipelineParams.custom_genome.annotation_url, type_tags: ['reference', 'annotation']}
            //                 ] as ILaxyFile[]
            const fasta_url = this.custom_genome_fasta_url.trim();
            const annotation_url = this.custom_genome_annotation_url.trim();
            if (fasta_url && annotation_url) {
                data.params.genome = '__UserSupplied__';
                const input_files =
                    [
                        {
                            location: fasta_url,
                            name: filenameFromUrl(fasta_url),
                            path: 'reference_genome',
                            type_tags: ['reference', 'fasta']
                        },
                        {
                            location: annotation_url,
                            name: filenameFromUrl(annotation_url),
                            path: 'reference_genome',
                            type_tags: ['reference', 'annotation']
                        }
                    ] as ILaxyFile[];

                data['params']['input_files'] = input_files;
            }

            return data;
        }

        get isValid_reference_genome() {
            return map(this.available_genomes, 'id').includes(this.reference_genome) ||
                this.reference_genome == '__UserSupplied__';
        }

        get isValid_samples_added() {
            // return (this.samples.items.length != 0);
            return this.$store.getters.sample_cart_count > 0;
        }

        get isValid_params() {
            let is_valid = false;
            if (this.isValid_reference_genome &&
                this.isValid_samples_added) {
                is_valid = true;
            }
            this.$store.set('pipelineParams_valid', is_valid);

            return is_valid;
        }

        async save() {
            try {
                this.submitting = true;
                await this.$store.dispatch(SET_SAMPLES, this._samples);

                const data = this.prepareData();
                // console.log(data);

                if (this.pipelinerun_uuid == null) {
                    const response = await WebAPI.fetcher.post("/api/v1/pipelinerun/", data) as AxiosResponse;
                    this.pipelinerun_uuid = response.data.id;
                } else {
                    await WebAPI.fetcher.put(`/api/v1/pipelinerun/${this.pipelinerun_uuid}/`, data) as AxiosResponse;
                }
                Snackbar.flashMessage("Saved !");
            } catch (error) {
                console.log(error);
                this.error_alert_message = error.toString();
                this.openDialog("error_dialog");
            }

            this.submitting = false;
        }

        async run() {
            try {
                this.submitting = true;
                await this.save();

                if (!this.isValid_params) {
                    Snackbar.flashMessage("Please correct errors before submitting.");
                    this.submitting = false;
                    return null;
                }

                try {
                    let response = null;
                    response = await WebAPI.fetcher.post(
                        `/api/v1/job/?pipeline_run_id=${this.pipelinerun_uuid}`, {}) as AxiosResponse;
                    Snackbar.flashMessage("Saved !");
                    await this.clearCart();
                    this.submitting = false;
                    return response;
                } catch (error) {
                    console.log(error);
                    this.error_alert_message = error.toString();
                    this.openDialog("error_dialog");
                }

            } catch (error) {
                console.error(error);
            }

            this.submitting = false;
            return null;
        }

        async addCustomGenomeFiles(addedFiles: FileListItem[]) {
            const sequence_extensions = ['.fasta.gz', '.fasta', '.fa', '.fa.gz'];
            const annotation_extensions = ['.gtf.gz', '.gff.gz', '.gff3.gz', '.gtf', '.gff', '.gff3'];
            for (let f of addedFiles) {
                for (let ext of sequence_extensions) {
                    if (f.name.endsWith(ext)) {
                        this.custom_genome_fasta_url = f.location;
                    }
                }
                for (let ext of annotation_extensions) {
                    if (f.name.endsWith(ext)) {
                        this.custom_genome_annotation_url = f.location;
                    }
                }
            }
            this.toggleFileSelect();
            const el = document.getElementById('_top');  // this.$refs['custom-genome-section'] as Element;
            // el.scrollIntoView({behavior: "smooth", block: "start"});
            if (el) el.scrollIntoView({behavior: "smooth", block: "start"});
            // el.scrollTo(0, 0);
        }

        toggleFileSelect(url?: string) {
            this.custom_genome_fileselect_url = url || '';
            this.toggleSlideout('fileSelectSlideout');
        }

        toggleSlideout(refName: string) {
            ((this.$refs as any)[refName] as any).toggle();
        }

        openSlideout(ref: string) {
            // console.log('Opened: ' + ref);
        }

        closeSlideout(ref: string) {
            // console.log('Closed: ' + ref);
        }

        async clearCart() {
            await this.$store.dispatch(CLEAR_SAMPLE_CART);
        }

        openDialog(ref: string) {
            (this.$refs[ref] as MdDialog).open();
        }

        closeDialog(ref: string) {
            (this.$refs[ref] as MdDialog).close();
        }

        onSelect(rows: any) {
            this.selectedSamples = rows as Array<Sample>;
        }

        beforeRouteLeave(to: any, from: any, next: any) {
            // console.log([to, from, next]);
            this.$store.commit(SET_SAMPLES, this._samples);
            next();
        }
    };

</script>
