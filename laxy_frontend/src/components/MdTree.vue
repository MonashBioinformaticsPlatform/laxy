<template>

        <md-list>
            <tree-node :root="root">
            </tree-node>
        </md-list>

</template>

<script lang="ts">
    import Vue from 'vue';
    import VueMaterial from 'vue-material';
    import Component from 'vue-class-component';
    import { Emit, Inject, Model, Prop, Provide, Watch } from 'vue-property-decorator';

    import { TreeNode, DataFile, FileSet } from '../tree.ts';

//    import MdTreeNode from './MdTreeNode.vue';
//    Vue.component('tree-root', MdTreeNode);

    import * as dummy from '../dummyTreeData.ts';

    @Component({props: {}})
    export default class MdTree extends Vue {
        root: TreeNode = dummy.folderOne as TreeNode;
    }
</script>

<style>

</style>
