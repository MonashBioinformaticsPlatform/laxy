<template>
    <md-dialog :md-open-from="openFrom" :md-close-to="closeTo"
               id="thisDialog" ref="thisDialog">
        <md-dialog-title>Downloading</md-dialog-title>

        <md-dialog-content>
            An archive of the job can be downloaded.

            On the command line, run:

            <code>
            curl "{{ tarballUrl }}" >{{ filename }}
            </code>

        </md-dialog-content>

        <md-dialog-actions>
            <md-button class="md-primary" @click="close()">Close</md-button>
        </md-dialog-actions>
    </md-dialog>
</template>

<script lang="ts">
    import Vue from "vue";
    import Component from "vue-class-component";
        import {
        Emit,
        Inject,
        Model,
        Prop,
        Provide,
        Watch
    } from "vue-property-decorator";
    import {ComputeJob} from "../../model";
    import {basename} from "../../util";
    // import VueMarkdown from 'vue-markdown';

    @Component({
        // components: {'vue-markdown': VueMarkdown},
        filters: {}
    })
    export default class DownloadHelpDialog extends Vue {
        @Prop({type: String})
        tarballUrl: string;

        @Prop({default: null, type: String})
        openFrom: string | null;

        @Prop({default: null, type: String})
        closeTo: string | null;

        get filename() {
            return basename((new URL(this.tarballUrl)).pathname);
        }

        open() {
            // console.log('Opened: ' + refName);
            ((this.$refs as any)['thisDialog'] as any).open();
        }

        close() {
            // console.log('Closed: ' + refName);
            ((this.$refs as any)['thisDialog'] as any).close();
        }
    }
</script>
