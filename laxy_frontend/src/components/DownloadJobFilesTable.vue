<template>
    <md-table>
        <md-table-header>
            <md-table-row>
                <md-table-head>
                    Link
                </md-table-head>
                <md-table-head style="text-align: right;">
                    Action
                </md-table-head>
            </md-table-row>
        </md-table-header>
        <md-table-body>
            <md-table-row v-for="link in [url]" :key="url">
                <md-table-cell>
                    <a :href="link"
                       @click.prevent="setClipboardFlash(link, 'Copied download link to clipboard !')">
                        <md-icon>link</md-icon>
                        {{ filename(url) | truncate }}
                    </a>
                </md-table-cell>
                <md-table-cell md-numeric>
                    <md-button class="md-icon-button push-right"
                               @click="setClipboardFlash(link, 'Copied download link to clipboard !')">
                        <md-icon>file_copy</md-icon>
                        <md-tooltip md-direction="top">Copy to clipboard</md-tooltip>
                    </md-button>
                </md-table-cell>
            </md-table-row>
        </md-table-body>
    </md-table>
</template>

<script lang="ts">
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

    const Clipboard = require('clipboard');

    @Component({
        filters: {},
    })
    export default class DownloadJobFilesTable extends Vue {
        @Prop({type: String})
        public url: string;

        filename(url: string): string | undefined {
            return new URL(url).pathname.split('/').pop();
        }

        async setClipboard(text: string) {
            return new Promise(function (resolve, reject) {
                const tmp_button = document.createElement('button');
                const clipboard = new Clipboard(tmp_button, {
                    text: function () {
                        return text
                    },
                    action: function () {
                        return 'copy'
                    },
                    container: document.body
                });
                clipboard.on('success', function (e: Promise<string>) {
                    clipboard.destroy();
                    resolve(e);
                });
                clipboard.on('error', function (e: Promise<string>) {
                    clipboard.destroy();
                    reject(e);
                });
                tmp_button.click();
            });
        }

        async setClipboardFlash(text: string, message: string, failMessage: string = "Failed to copy to clipboard :/") {
            try {
                const displayTime = (message.length * 20) + 500;
                await this.setClipboard(text);
                this.$emit('flash-message', {message: message, duration: displayTime});
            } catch (error) {
                const displayTime = (failMessage.length * 20) + 1000;
                this.$emit('flash-message', {message: failMessage, duration: displayTime});
            }
        }
    }

</script>
