<template>
    <md-dialog :md-open-from="openFrom" :md-close-to="closeTo"
               id="thisDialog" ref="thisDialog">
        <md-dialog-title>Job expiry</md-dialog-title>

        <md-dialog-content>
            Large files associated with this job will be deleted<template v-if="job"> on
            <strong>{{ job.expiry_time | moment('DD-MMM-YYYY(HH:mm UTCZ)') }}</strong></template>.
            <br/>
            If you wish to preserve these files, please archive them to another location.
            <br/>
            Small files such as reports and logs will be maintained.
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
    // import VueMarkdown from 'vue-markdown';

    @Component({
        // components: {'vue-markdown': VueMarkdown},
        filters: {}
    })
    export default class ExpiryDialog extends Vue {
        @Prop({type: Object})
        job: ComputeJob;

        @Prop({default: null, type: String})
        openFrom: string | null;

        @Prop({default: null, type: String})
        closeTo: string | null;

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
