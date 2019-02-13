<template>
    <md-card md-with-hover
             @click.native.stop="onClicked"
             :class="'md-' + cardClass"
             :style="!cardClass ? cssStripe(getThemeColor(stripeColor), 'left', 4): ''">
        <md-card-area>
            <md-card-header>
                <md-card-header-text>
                    <div class="md-title">
                        <slot name="title"></slot>
                    </div>
                    <div class="md-subhead">
                        <slot name="subtitle"></slot>
                    </div>
                </md-card-header-text>

                <md-card-media>
                    <md-icon class="md-size-4x" v-if="icon">{{ icon }}</md-icon>
                </md-card-media>

                <md-card-content>
                    <slot name="content"></slot>
                </md-card-content>
            </md-card-header>
        </md-card-area>

        <md-card-actions v-if="buttonIcon || buttonText">
            <md-button @click="onClicked" :class="{'md-icon-button': buttonText}">
                <md-icon v-if="buttonIcon">{{ buttonIcon }}</md-icon>
                {{ buttonText }}
            </md-button>
        </md-card-actions>
    </md-card>

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
    import {cssStripe, getThemeColor} from "../palette";

    @Component({
        filters: {},
    })
    export default class GenericPip extends Vue {
        @Prop({type: String, default: 'info'})
        public icon: string | null;

        @Prop({type: String, default: null})
        public buttonIcon: string | null;

        @Prop({type: String, default: ''})
        public buttonText: string;

        @Prop({type: String, default: 'primary'})
        public stripeColor: '' | 'primary' | 'accent' | 'warn' | 'transparent';

        @Prop({type: String, default: ''})
        public cardClass: '' | 'primary' | 'accent' | 'warn';

        cssStripe = cssStripe;
        getThemeColor = getThemeColor;

        onClicked(event: any) {
            this.$emit('click')
        }
    }
</script>
