<template>
    <md-toolbar v-if="!closed"
                @click.native.stop="onClick"
                class="shadow"
                :class="materialClass">
        <span class="spacer"></span>
        <h4><slot>Carpe diem !</slot></h4>
        <span class="spacer"></span>
        <md-button v-if="showCloseButton" class="md-icon-button" @click.stop="onClosed">
            <md-icon>close</md-icon>
        </md-button>
    </md-toolbar>
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

    @Component({
        components: {},
        filters: {}
    })
    export default class BannerNotice extends Vue {
        @Prop({type: String, default: 'warning'})
        type: string;

        @Prop({type: Boolean, default: true})
        showCloseButton: boolean;

        private closed: boolean = false;

        get materialClass(): string {
            if (this.type === 'warning') return 'md-warn';
            if (this.type === 'info') return 'md-primary';
            if (this.type === 'clear') return 'md-transparent';
            if (this.type === 'error') return 'md-accent';

            return 'md-transparent';
        }

        onClick(event: any) {
            this.$emit('click', event);
        }

        onClosed(event: any) {
            this.closed = true;
            this.$emit('close', event);
        }
    }
</script>

<style lang="css" scoped>
    .spacer {
        flex: 1;
    }
</style>
