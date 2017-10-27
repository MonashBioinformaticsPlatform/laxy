<template>

    <md-list-item>
        <div :class="{bold: isContainer}"
             @click="toggle">
            {{nodeName}}
            <span v-if="isContainer">[{{open ? '-' : '+'}}]</span>
        </div>
        <md-list v-show="open" v-if="isContainer">
            <md-list-item v-for="n in node.children"
                          :key="n.id"
                          :model="n">
            </md-list-item>
        </md-list>
    </md-list-item>

</template>

<script lang="ts">
    import Vue from 'vue';
    import VueMaterial from 'vue-material';
    import Component from 'vue-class-component';
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator';

    import { TreeNode, DataFile, FileSet } from '../tree.ts';

    @Component({props: {root: TreeNode}})
    export default class MdTreeNode extends Vue {

        root: TreeNode;
        open: boolean = false;
        node: TreeNode = this.root;

        created() {
            this.node = this.root;
        }

        toggle() {
            if (this.isContainer()) {
                this.open = !this.open;
            }
        }

        isContainer() {
            if (this.node == null) return false;
            return this.node.isContainer();
        }

        nodeName() {
            if (this.node == null) return 'undefined';
            return this.node.name;
        }
    }
</script>

<style>

</style>
