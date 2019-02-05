<template>
    <div>
        <md-layout md-gutter>
            <md-layout md-flex="100"
                       md-column>
                <h3>Input data</h3>
                <form novalidate @submit.stop.prevent="submit">
                    <md-layout>
                        <md-layout>
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
                        </md-layout>
                        <md-layout md-flex="5" md-vertical-align="center">
                            <md-button id="helpButton"
                                       @click="openDialog('helpPopup')"
                                       class="push-right md-icon-button md-raised md-dense">
                                <md-icon style="color: #bdbdbd;">help</md-icon>
                            </md-button>
                        </md-layout>
                    </md-layout>

                    <div id="ena_form" v-if="selected_source == 'ENA'">
                        <ena-file-select :show-about-box="false" :show-buttons="true" ref="enaSearch">
                        </ena-file-select>
                    </div>

                    <div id="url_form" v-if="selected_source == 'URL'">
                        <remote-files-select :show-about-box="false" :show-buttons="true"></remote-files-select>
                    </div>
                    <div id="csv_form" v-if="selected_source == 'CSV'">
                        <CSVSampleListUpload :show-about-box="false"></CSVSampleListUpload>
                    </div>
                    <div id="cloudstor_form" v-if="selected_source == 'CLOUDSTOR'">
                        <md-whiteframe md-elevation="5" class="pad-16 fill-vertical">
                            <div ref="aboutClourStor">
                                Paste a link to a shared <a
                                    href="https://cloudstor.aarnet.edu.au/plus/index.php/apps/files/">CloudStor</a>
                                folder here (eg
                                <code>https://cloudstor.aarnet.edu.au/plus/index.php/s/RaNd0MlooK1NgID</code>)
                                and the password if required.
                            </div>
                        </md-whiteframe>
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
                        <md-whiteframe md-elevation="5" class="pad-16 fill-vertical">
                            <div ref="aboutSFTP">
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
                        <div v-show="!sftp_upload_credentials">
                            <h4>Generate upload credentials</h4>
                            <md-input-container :class="{'md-input-invalid': dataset_name_invalid }">
                                <label>Dataset name</label>
                                <md-input required id="dataset_name" v-model="dataset_name"></md-input>
                                <span class="md-error">Dataset name must be specified</span>
                            </md-input-container>
                            <md-button class="md-raised md-primary" @click="generateSFTPUploadCredentials()">
                                Generate
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

                            This password expires in {{ password_valid_days }}
                            days (upload before {{ password_expiry | moment("dddd, MMMM Do YYYY, h:mm:ss a") }}).
                        </div>
                        <hr>
                    </div>
                    <br/>
                </form>
            </md-layout>

            <md-dialog md-open-from="#helpButton" md-close-to="#helpButton"
                       id="helpPopup" ref="helpPopup">
                <md-dialog-title>Input data source help</md-dialog-title>

                <md-dialog-content>
                    <ENASearchAboutBox v-if="selected_source == 'ENA'" ref="aboutENA"></ENASearchAboutBox>
                    <RemoteFileSelectAboutBox v-if="selected_source == 'URL'"></RemoteFileSelectAboutBox>
                    <CSVAboutBox v-if="selected_source == 'CSV'"></CSVAboutBox>
                </md-dialog-content>

                <md-dialog-actions>
                    <md-button class="md-primary" @click="closeDialog('helpPopup')">Close</md-button>
                </md-dialog-actions>
            </md-dialog>
        </md-layout>
    </div>
</template>

<script lang="ts">
    import * as _ from 'lodash';
    import 'es6-promise';

    import axios, {AxiosResponse} from 'axios';
    import Vue, {ComponentOptions} from 'vue';
    import Component from 'vue-class-component';
    import {Emit, Inject, Model, Prop, Provide, Watch} from 'vue-property-decorator'
    import ENAFileSelect from "./ENA/ENAFileSelect";
    import ENASearchAboutBox from "./ENA/ENASearchAboutBox";
    import RemoteFilesSelect from "./RemoteSelect/RemoteFilesSelect";
    import RemoteFileSelectAboutBox from "./RemoteSelect/RemoteFileSelectAboutBox";
    import CSVSampleListUpload from "./CSVSampleListUpload/CSVSampleListUpload";
    import CSVAboutBox from "./CSVSampleListUpload/CSVAboutBox";

    interface DbAccession {
        accession: string;
    }

    @Component({
        components: {
            ENASearchAboutBox, 'ena-file-select': ENAFileSelect,
            RemoteFilesSelect, RemoteFileSelectAboutBox,
            CSVSampleListUpload,
            CSVAboutBox,
        },
        props: {}
    })
    export default class InputFilesForm extends Vue {

        sources: object = [
            {type: 'ENA', text: 'Public data from ENA or SRA'},
            {type: 'URL', text: 'Files on a web or FTP server (URL)'},
            {type: 'CSV', text: 'Sample list from CSV / Excel'},
            // {type: 'CLOUDSTOR', text: 'CloudStor'},
            // {type: 'SFTP_UPLOAD', text: 'SFTP upload'},
        ];
        selected_source: string = 'ENA';
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

        // for lodash in templates
        get _() {
            return _;
        }

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

        openDialog(refName: string) {
            // console.log('Opened: ' + refName);
            ((this.$refs as any)[refName] as any).open();
        }

        closeDialog(refName: string) {
            // console.log('Closed: ' + refName);
            ((this.$refs as any)[refName] as any).close();
        }

        @Watch('selected_source')
        onDataSourceChanged(newVal: string, oldVal: string) {
            this.$emit('dataSourceChanged');
        }

        @Watch('url_input', {immediate: true})
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
    #helpPopup > div.md-dialog {
        width: 90%;
    }
</style>
