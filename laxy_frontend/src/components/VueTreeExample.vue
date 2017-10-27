<template>
    <li :class="{file: !isFolder, folder: isFolder}">
        <div :class="{bold: isFolder}"
             @click="toggle"
             @dblclick="changeType">
            <span>{{model.name}}</span>
            <span v-if="isFolder">[{{open ? '-' : '+'}}]</span>
        </div>
        <ul v-show="open" v-if="isFolder">
            <vue-tree-item
                    class="item"
                    v-for="child in model.children"
                    :key="child.id"
                    :model="child">
            </vue-tree-item>
            <li class="add" @click="addChild">+</li>
        </ul>
    </li>
</template>

<script lang="ts">

    export const exampleTreeData = {
        name: 'My Tree',
        children: [
            {name: 'hello'},
            {name: 'wat'},
            {
                name: 'child folder',
                children: [
                    {
                        name: 'child folder',
                        children: [
                            {name: 'hello'},
                            {name: 'wat'}
                        ]
                    },
                    {name: 'hello'},
                    {name: 'wat'},
                    {
                        name: 'child folder',
                        children: [
                            {name: 'hello'},
                            {name: 'wat'}
                        ]
                    }
                ]
            }
        ]
    };

    // define the item component
    import Vue from 'vue';
    import VueMaterial from 'vue-material';
    import Component from 'vue-class-component';

    @Component({props: {model: Object}})
    export default class VueTreeExample extends Vue {

        model: any;
        open: boolean = false;

        get isFolder() {
            return this.model.children && this.model.children.length;
        }
        toggle() {
            if (this.isFolder) {
                this['open'] = !this.open;
            }
        }
        changeType() {
            if (!this.isFolder) {
                Vue.set(this.model, 'children', []);
                this.addChild();
                this['open'] = true;
            }
        }
        addChild() {
            this.model.children.push({
                name: 'new stuff'
            });
        }
    }

</script>

<style scoped>
    .bold {
        font-weight: bold;
        color: #3f51b5;
    }

    li.folder::before {
        content: "folder"; /* Material Icon name */
        font-family: "Material Icons";
        display: inline-block;
        margin-top: 1.3em; /* same as padding-left set on li */
        margin-left: -1.3em; /* same as padding-left set on li */
        width: 1.3em; /* same as padding-left set on li */
    }

    li.file::before {
        content: "insert drive file"; /* Material Icon name */
        font-family: "Material Icons";
        display: inline-block;
        margin-top: -1.3em; /* same as padding-left set on li */
        margin-left: -1.3em; /* same as padding-left set on li */
        width: 1.3em; /* same as padding-left set on li */
    }
</style>
