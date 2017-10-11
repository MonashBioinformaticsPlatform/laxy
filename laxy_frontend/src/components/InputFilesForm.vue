<template>
    <div>
        <md-layout md-gutter>

            <md-layout md-column>
                <h3>Input data</h3>
                <form novalidate @submit.stop.prevent="submit">

                    <md-input-container>
                        <label for="data_source">Select a data source</label>
                        <md-select name="data_source" id="data_source"
                                   v-model="selected_source">
                            <md-option v-for="(source, i) in sources"
                                       :key="source.type"
                                       :value="source.type">{{ source.text }}
                            </md-option>
                        </md-select>
                    </md-input-container>

                    <div id="ena_form" v-if="selected_source == 'ENA'">
                        <md-input-container>
                            <label>Accession</label>
                            <md-input v-model="ena_id"></md-input>
                        </md-input-container>
                    </div>

                    <div id="sra_form" v-if="selected_source == 'SRA'">
                        <md-input-container>
                            <label>Accession</label>
                            <md-input v-model="sra_id"></md-input>
                        </md-input-container>
                    </div>

                    <div id="url_form" v-if="selected_source == 'URL'">
                        <md-input-container>
                            <label>URL</label>
                            <md-input v-model="url_input"></md-input>
                        </md-input-container>
                    </div>
                    <div id="cloudstor_form" v-if="selected_source == 'CLOUDSTOR'">
                        <md-input-container>
                            <label>CloudStor share link</label>
                            <md-input v-model="url_input"
                                      placeholder="https://cloudstor.aarnet.edu.au/plus/index.php/s/"></md-input>
                        </md-input-container>
                        <md-input-container>
                            <label>Link password</label>
                            <md-input v-model="cloudstor_link_password"></md-input>
                        </md-input-container>
                    </div>
                    <div id="sftp_upload_form" v-if="selected_source == 'SFTP_UPLOAD'">
                        <div v-show="!sftp_upload_credentials">
                            <h4>Generate upload credentials</h4>
                            <md-input-container :class="{'md-input-invalid': dataset_name_invalid }">
                                <label>Dataset name</label>
                                <md-input required id="dataset_name" v-model="dataset_name"></md-input>
                                <span class="md-error">Dataset name must be specified</span>
                            </md-input-container>
                            <md-button class="md-raised md-primary" @click="generateSFTPUploadCredentials()">Generate
                            </md-button>
                        </div>
                        <div id="sftp_upload_credentials" v-show="sftp_upload_credentials">
                            <h4>Upload location generated !</h4>

                            Please upload your data using SFTP to:<br/>
                            <a :href="'sftp://'+sftp_upload_credentials">sftp://{{ sftp_upload_credentials }}</a>

                            <p>Username: <code>{{ email_username() }}_{{ email_domain() }}</code></p>
                            <p>Password: <code>{{ sftp_otp() }}</code></p>
                            <p>Host: <code>{{ sftp_upload_host }}</code></p>
                            <p>Path: <code>{{ sftp_upload_path }}</code></p>

                            This password expires in {{ password_valid_days
                            }} days (upload before {{ password_expiry | moment("dddd, MMMM Do YYYY, h:mm:ss a") }}).
                        </div>
                        <hr>
                    </div>
                    <br/>
                </form>
            </md-layout>

            <md-layout md-column style="padding: 16px;">
                <md-whiteframe md-elevation="5" style="padding: 16px; min-height: 100%;">
                    <div v-if="selected_source == 'ENA'">The <a href="http://www.ebi.ac.uk/ena">European Nucleotide Archive (ENA)</a>
                        at
                        EMBL-EBI stores publicly available raw sequencing data from high-throughput sequencing platforms
                    </div>
                    <div v-if="selected_source == 'SRA'">
                        The <a href="https://www.ncbi.nlm.nih.gov/sra">Sequence Read Archive (SRA)</a> at NCBI
                        stores publicly available raw sequencing data from high-throughput sequencing platforms.
                    </div>
                    <div v-if="selected_source == 'URL'">
                        If your raw read FASTQ data exists at a particular URL, you can paste it here.
                        Valid protocols are <code>http://</code>, <code>https://</code> or <code>ftp://</code>.

                        You files can be in an index directory or a single tar archive, eg:

                        <a href="http://bioinformatics.erc.monash.edu/~andrewperry/laxy/test1/">
                            http://bioinformatics.erc.monash.edu/~andrewperry/laxy/test1/</a>

                        or

                        <a href="http://bioinformatics.erc.monash.edu/~andrewperry/laxy/test2/my_fastqs.tar">
                            http://bioinformatics.erc.monash.edu/~andrewperry/laxy/test2/my_fastqs.tar</a>
                    </div>
                    <div v-if="selected_source == 'CLOUDSTOR'">
                        Paste a link to a shared <a href="https://cloudstor.aarnet.edu.au/plus/index.php/apps/files/">CloudStor</a>
                        folder here (eg <code>https://cloudstor.aarnet.edu.au/plus/index.php/s/RaNd0MlooK1NgID</code>)
                        and the password if required.
                    </div>
                    <div v-if="selected_source == 'SFTP_UPLOAD'">
                        <p>
                            FASTQ data can be uploaded to our secure server for analysis.
                            When you enter a dataset name and press <em>"Generate"</em>, a
                            username and temporary password will be created for you on the
                            <em>{{ sftp_upload_host }}</em> server.
                            You can use these to upload your data via SFTP.
                        </p>
                        <p>
                            <em>Please note that raw data uploaded is deleted after two weeks.</em>
                        </p>

                    </div>

                </md-whiteframe>
            </md-layout>

        </md-layout>
    </div>
</template>

<script lang="ts">
    declare function require(path: string): any;

    import 'vue-material/dist/vue-material.css';

    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import Component from 'vue-class-component';
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator'

    @Component({props: {}})
    export default class InputFilesForm extends Vue {

        sources: object = [
            {type: 'ENA', text: 'European Nucleotide Archive at EBI-EMBL (ENA)'},
            {type: 'SRA', text: 'Sequence Read Archive at NCBI (SRA)'},
            {type: 'URL', text: 'URL'},
            {type: 'CLOUDSTOR', text: 'CloudStor'},
            {type: 'SFTP_UPLOAD', text: 'SFTP upload'},
        ];
        selected_source: string = 'SFTP_UPLOAD';
        ena_id: string = '';
        sra_id: string = '';
        url_input: string = '';
        cloudstor_link_password: string = '';
        user_email: string = 'my.username@example.com';
        sftp_upload_host: string = 'laxy.erc.monash.edu';
        sftp_upload_path: string = '';
        sftp_upload_credentials: string = '';
        dataset_name: string = '';
        password_valid_days: number = 2;
        password_expiry: Date = this.daysInFuture(2);
        dataset_name_invalid: boolean = false;

        email_username() {
            return this.user_email.split('@')[0];
        }

        email_domain() {
            return this.user_email.split('@')[1];
        }

        sftp_otp() {
            return Math.random().toString(36).substring(7);
        }

        generateSFTPUploadCredentials(): void {
            if (!this.dataset_name) {
                this.dataset_name_invalid = true;
            } else {
                let username = this.email_username();
                let domain = this.email_domain();
                let otp = this.sftp_otp();
                this.sftp_upload_path = `${this.dataset_name}`;
                this.sftp_upload_credentials = `${username}_${domain}:${otp}@${this.sftp_upload_host}/${this.sftp_upload_path}/`;

                this.$emit('stepDone');
            }
        }

        daysInFuture(days: number): Date {
            let now = new Date();
            now.setDate(now.getDate() + days);
            return now;
        }

        // TODO: We might want to use: https://validatejs.org/#validators-url instead
        isValidURL(url: string): boolean {
           const valid_protocols = ['http:', 'https:', 'ftp:'];
           const a = document.createElement('a');
           a.href = url;
           return (a.host != null &&
                   a.host != window.location.host &&
                   _.includes(valid_protocols, a.protocol)
           );
        }

        isCloudStorURL(url: string): boolean {
           const valid_protocols = ['https:'];
           const a = document.createElement('a');
           a.href = url;
           return (a.host != null &&
                   a.host != window.location.host &&
                   _.includes(valid_protocols, a.protocol) &&
                   a.host == 'cloudstor.aarnet.edu.au'
           );
        }

        @Watch('selected_source')
        onDataSourceChanged(newVal: string, oldVal: string) {
            this.$emit('dataSourceChanged');
        }

        @Watch('ena_id', { immediate: true })
        onENAIdChanged(newVal: string, oldVal: string) {
            // validate newVal
            // https://www.ebi.ac.uk/ena/submit/accession-number-formats
            if (newVal.trim().length >= 9) {
                this.$emit('stepDone');
            } else {
                this.$emit('invalidData');
            }
        }

        @Watch('sra_id', { immediate: true })
        onSRAIdChanged(newVal: string, oldVal: string) {
            // validate newVal
            // https://www.ncbi.nlm.nih.gov/books/NBK56913/#search.why_does_sra_have_so_many_differe
            if (newVal.trim().length >= 9) {
                this.$emit('stepDone');
            } else {
                this.$emit('invalidData');
            }
        }

        @Watch('url_input', { immediate: true })
        onURLInputChanged(newVal: string, oldVal: string) {
            if (this.selected_source == 'URL' &&
                    this.isValidURL(newVal)) {
                this.$emit('stepDone');
            } else if (this.selected_source == 'CLOUDSTOR' &&
                    this.isCloudStorURL(newVal)) {
                this.$emit('stepDone');
            } else {
                this.$emit('invalidData');
            }
        }
    };

</script>

<style>
    /* CSS to apply to this component */
</style>
