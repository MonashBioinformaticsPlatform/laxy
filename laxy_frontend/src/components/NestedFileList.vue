<template>
  <div class="filelist">
    <md-progress v-if="refreshing || searching" md-indeterminate></md-progress>
    <transition name="fade">
      <md-layout v-if="!refreshing">
        <md-toolbar class="md-transparent fill-width">
          <h1 class="md-title">{{ titleText }}</h1>
          <md-input-container v-if="!hideSearch" md-clearable>
            <md-input v-model="searchQuery" :placeholder="searchBoxPlaceholder"></md-input>
            <md-icon v-if="!searchQuery">search</md-icon>
          </md-input-container>
        </md-toolbar>
        <md-toolbar class="md-transparent fill-width">
          <slot name="breadcrumbs">
            <div v-if="!searchQuery.trim()" class="breadcrumbs">
              &nbsp;
              <span v-for="node in pathToRoot">
                <template v-if="node.id === '__root__'">
                  <code>{{ rootPathName }} /</code>
                </template>
                <template v-else>
                  <code>{{ node.name }} /</code>
                </template>
              </span>
              <br />
            </div>
          </slot>
        </md-toolbar>
        <md-table ref="file-table" @select="onSelect">
          <md-table-header>
            <md-table-row>
              <md-table-head>File</md-table-head>
              <md-table-head v-if="!hideActions" style="text-align: right;">Action</md-table-head>
            </md-table-row>
          </md-table-header>
          <md-table-body v-if="currentLevel">
            <md-table-row v-if="currentLevel.parent" @click.native="upDirectory">
              <md-table-cell class="md-table-selection">
                <div class="push-left">
                  <md-icon>folder_open</md-icon>
                </div>
              </md-table-cell>
              <md-table-cell>
                <div class="no-line-break">..</div>
              </md-table-cell>
              <md-table-cell md-numeric>
                <md-button class="md-icon-button" :disabled="true">
                  <!-- empty placeholder button to preserve layout -->
                  <md-icon></md-icon>
                </md-button>
                <md-button class="md-icon-button push-right" :disabled="true">
                  <md-icon>subdirectory_arrow_left</md-icon>
                </md-button>
              </md-table-cell>
            </md-table-row>
            <md-table-row v-if="showBackArrow" @click.native="$emit('back-button-clicked')">
              <md-table-cell class="md-table-selection">
                <div class="push-left">
                  <md-icon>arrow_back</md-icon>
                </div>
              </md-table-cell>
              <md-table-cell>
                <div class="no-line-break"></div>
              </md-table-cell>
              <md-table-cell md-numeric>
                <md-button class="md-icon-button" :disabled="true">
                  <!-- empty placeholder button to preserve layout -->
                  <md-icon></md-icon>
                </md-button>
                <md-button class="md-icon-button push-right" :disabled="true">
                  <md-icon></md-icon>
                </md-button>
              </md-table-cell>
            </md-table-row>
            <md-table-row v-for="node in currentLevelNodes" :md-item="node.obj" :key="node.id"
              :md-selection="node.obj && selectableTypes.includes(node.meta.type) && !shouldDisableCheckbox(node.obj)"
              @selected="onSelectedRow(node.obj)" @deselected="onDeselectedRow(node.obj)">
              <template v-if="node.meta.type === 'file'">
                <!-- when in cart, insert a disabled checkbox
                (since :md-selection="false"  _removes_ the checkbox)-->
                <md-table-cell v-if="shouldDisableCheckbox(node.obj)" class="md-table-selection">
                  <md-checkbox disabled></md-checkbox>
                </md-table-cell>

                <md-table-cell @click.native="getProp(node.meta, 'onclick', (n) => { })(node)">
                  <div class="no-line-break"
                    :class="{ strikethrough: node.obj.deleted, unavailable: !node.obj.location }">
                    <md-icon v-if="node.meta.tags && node.meta.tags.includes('archive')">folder_special</md-icon>
                    {{ node.obj.name | magic_truncate }}
                  </div>
                </md-table-cell>
                <md-table-cell v-if="!hideActions && !node.obj.deleted"
                  @click.native="getProp(node.meta, 'onclick', (n) => { })(node)" md-numeric>
                  <md-spinner v-if="actionRunning[node.obj.id]" :md-size="20" class="push-right"
                    md-indeterminate></md-spinner>
                  <md-button v-else-if="getDefaultViewMethod(node.obj) && node.obj.location"
                    class="md-icon-button push-right" @click="getDefaultViewMethod(node.obj).method(node.obj)">
                    <md-tooltip md-direction="top">{{ getDefaultViewMethod(node.obj).text }}</md-tooltip>
                    <md-icon>{{ getDefaultViewMethod(node.obj).icon }}</md-icon>
                  </md-button>
                  <md-button v-else-if="!node.obj.location" class="md-icon-button push-right">
                    <md-tooltip md-direction="left">File has no recorded location. This may be a temporary situtation,
                      or an error.</md-tooltip>
                    <md-icon>not_listed_location</md-icon>
                  </md-button>
                  <md-button v-else :disabled="true" class="md-icon-button">
                    <!-- empty placeholder button to preserve layout -->
                    <md-icon></md-icon>
                  </md-button>
                  <md-menu v-if="!actionRunning[node.obj.id]" md-size="4">
                    <md-button class="md-icon-button push-right" md-menu-trigger>
                      <md-icon>arrow_drop_down</md-icon>
                    </md-button>

                    <md-menu-content>
                      <i class="md-caption" style="padding-left: 16px">{{ node.obj.id }}</i>
                      <!--  -->
                      <template v-if="node.obj.location">
                        <md-menu-item v-for="view in getViewMethodsForTags(node.obj.type_tags)" :key="view.text"
                          @click="view.method(node.obj)">
                          <md-icon>{{ view.icon }}</md-icon>
                          <span>{{ view.text }}</span>
                        </md-menu-item>
                      </template>
                      <template v-else>
                        <md-menu-item>
                          <md-icon>not_listed_location</md-icon>
                          <span><i>Not available</i></span>
                        </md-menu-item>
                      </template>
                    </md-menu-content>
                  </md-menu>
                </md-table-cell>
                <md-table-cell v-else-if="node.obj.deleted === true">
                  <md-button class="md-icon-button push-right">
                    <md-tooltip md-direction="left">File has expired and is no longer available.</md-tooltip>
                    <md-icon style="color: #bdbdbd;">info</md-icon>
                  </md-button>
                </md-table-cell>
                <md-table-cell v-else></md-table-cell>
              </template>
              <template v-else-if="node.meta.type === 'directory'">
                <!-- it's a directory, not a file -->
                <md-table-cell class="md-table-selection"
                  @click.native="getProp(node.meta, 'onclick', enterDirectory)(node)">
                  <md-icon>folder</md-icon>
                </md-table-cell>
                <md-table-cell @click.native="getProp(node.meta, 'onclick', enterDirectory)(node)">
                  <div class="no-line-break">{{ node.name | magic_truncate }}</div>
                </md-table-cell>
                <md-table-cell md-numeric @click.native="getProp(node.meta, 'onclick', enterDirectory)(node)">
                  <md-button class="md-icon-button push-right" :disabled="true">
                    <!-- <md-icon>subdirectory_arrow_right</md-icon> -->
                    <!-- empty placeholder button to preserve layout -->
                    <md-icon></md-icon>
                  </md-button>
                </md-table-cell>
              </template>
            </md-table-row>
            <md-table-row v-if="currentLevel.children.length === 0">
              <md-table-cell>No files</md-table-cell>
            </md-table-row>
          </md-table-body>
        </md-table>
      </md-layout>
    </transition>
  </div>
</template>

<script lang="ts">
import filter from "lodash-es/filter";
import map from "lodash-es/map";
import lodashGet from "lodash-es/get";
import head from "lodash-es/head";
import sortBy from "lodash-es/sortBy";
// import flatten from "lodash-es/flatten";
// import flatMapDeep from "lodash-es/flatMapDeep";

import { Memoize, Debounce } from "lodash-decorators";
// import Memoize from "lodash-decorators/Memoize";
// import Debounce from "lodash-decorators/Debounce";

import "es6-promise";

import axios, { AxiosResponse } from "axios";
import Vue, { ComponentOptions } from "vue";
import Component from "vue-class-component";
import {
  Emit,
  Inject,
  Model,
  Prop,
  Provide,
  Watch,
} from "vue-property-decorator";

import { State, Getter, Action, Mutation, namespace } from "vuex-class";

import { ComputeJob, LaxyFile } from "../model";
import { WebAPI } from "../web-api";
import { FETCH_FILESET } from "../store";
import { strToRegex } from "../util";
import {
  hasSharedTagOrEmpty,
  hasIntersection,
  filterByTag,
  excludeByTag,
  filterByRegex,
  filterByFullPath,
  viewFile,
  downloadFile,
  fileListToTree,
  flattenTree,
  TreeNode,
  findPair,
} from "../file-tree-util";

import { DummyFileSet as _dummyFileSet } from "../test-data";
import { Snackbar } from "../snackbar";
import { ViewMethod } from "../types";

@Component({
  filters: {},
})
export default class NestedFileList extends Vue {
  _DEBUG: boolean = false;

  @Prop()
  public fileTree: TreeNode<LaxyFile>; // TreeNode<any>; ?

  @Prop({ type: String, default: "" })
  public rootPathName: string;

  @Prop(String)
  public title: string;

  @Prop({
    type: Array,
    default: () => {
      return [];
    },
  })
  public regexFilters: string[];

  @Prop({
    type: Array,
    default: () => {
      return [];
    },
  })
  public tagFilters: string[];

  @Prop({
    type: Array,
    default: () => {
      return [];
    },
  })
  public excludeTags: string[];

  @Prop({ default: () => ["file"], type: Array })
  public selectableTypes: string[];

  @Prop({ default: false, type: Boolean })
  public singleSelect: boolean;

  @Prop({ default: true, type: Boolean })
  public hideSearch: boolean;

  @Prop({ default: false, type: Boolean })
  public hideActions: boolean;

  @Prop({ default: false, type: Boolean })
  public showBackArrow: boolean;

  @Prop({ default: true, type: Boolean })
  public autoSelectPair: boolean;

  @Prop({ default: 2, type: Number })
  public minQueryLength: number;

  @Prop(String)
  public jobId: string | null;

  @Prop({ default: "Search", type: String })
  public searchBoxPlaceholder: string;

  public searchQuery: string = "";
  public searching: boolean = false;

  public actionRunning: any = {};

  // for templates
  getProp = lodashGet;

  get selectedFiles(): LaxyFile[] {
    return (this.$refs["file-table"] as MdTable).selectedRows as LaxyFile[];
  }

  @Watch("fileTree")
  initCurrentLevel(new_val: TreeNode<LaxyFile>, old_value: TreeNode<LaxyFile>) {
    this.currentLevel = this.fileTree;
  }

  public currentLevel: TreeNode<LaxyFile> | null = null;

  @Debounce(600)
  get searchFilteredNodes(): Array<TreeNode<LaxyFile>> {
    this.searching = true;
    const nodes = flattenTree(this.fileTree.children);

    if (!this.searchQuery || this.searchQuery.trim().length === 0) return nodes;
    const query = this.searchQuery.trim().toLowerCase();

    const hits: Array<TreeNode<LaxyFile>> = filter(
      nodes,
      (node: TreeNode<LaxyFile>) => {
        if (node.obj) {
          return `${node.obj.name}/${node.obj.name}`
            .toLowerCase()
            .includes(query);
          // TODO: Make globbing work, or look at vuex-search
          // return minimatch(`${node.obj.name}/${node.obj.name}`, query);
        } else {
          return node.name.toLowerCase().includes(query);
          // TODO: Make globbing work, or look at vuex-search
          // return minimatch(node.name, query);
        }
      }
    );
    this.searching = false;
    return hits;
  }

  get currentLevelNodes(): Array<TreeNode<LaxyFile>> {
    if (this.currentLevel) {
      let nodes = this.currentLevel.children;
      const query = this.searchQuery.trim();
      if (query.length >= this.minQueryLength) {
        nodes = this.searchFilteredNodes;
      }
      return sortBy(nodes, [
        (n: TreeNode<LaxyFile>) => n.obj != null,
        "meta.type",
        "name",
      ]);
    }
    return [];
  }

  get pathToRoot(): TreeNode<LaxyFile>[] {
    if (this.currentLevel) {
      let parent = this.currentLevel.parent;
      let nodes: TreeNode<LaxyFile>[] = [this.currentLevel];
      while (parent != null) {
        if (parent.name) nodes.push(parent);
        parent = parent.parent;
      }
      nodes.reverse();
      return nodes;
    }
    return [];
  }

  /*
  get fileTree(): TreeNode<LaxyFile> {
      if (this.files) {
          return fileListToTree(this.files);
      } else {
          return this._emptyTreeRoot;
      }
  }
  */

  get currentLevelFiles(): (LaxyFile | null)[] {
    if (this.currentLevel) {
      return map(
        sortBy(this.currentLevel.children, ["name"]),
        (node) => node.obj
      );
    }
    return [];
  }

  upDirectory(): TreeNode<LaxyFile> | null {
    if (this.currentLevel && this.currentLevel.parent) {
      this.currentLevel = this.currentLevel.parent;
    }
    this.searchQuery = "";
    return this.currentLevel;
  }

  enterDirectory(node: TreeNode<LaxyFile>) {
    this.searchQuery = "";
    this.currentLevel = node;
  }

  onSelect(rows: any) {
    this.$emit("select", rows);
    // console.dir(rows);
  }

  // checks / unchecks the mdTableRow checkbox, based on finding the
  // rows associated (file) object
  _setRowsCheckboxState(files: LaxyFile[], state: boolean): void {
    const table = this.$refs["file-table"] as MdTable;
    // skip header row(s)
    const rows = filter(table.$children, (r) => !r.headRow);
    for (let file of files) {
      const row = rows[table.data.indexOf(file)];
      table.setRowSelection(state, file);
      row.checkbox = state;
    }

    // we need to re-emit the md-table @select event since we've auto-selected rows
    // (MdTable.setRowSelection doesn't do this itself)
    this.$emit("select", table.selectedRows);
  }

  onSelectedRow(file: LaxyFile) {
    if (this.singleSelect && this.currentLevelFiles != null) {
      this._setRowsCheckboxState(this.currentLevelFiles as LaxyFile[], false);
      this._setRowsCheckboxState([file], true);
    }

    if (this.autoSelectPair && this.files && file) {
      const pair = findPair(file, this.files);
      if (pair != null) {
        this._setRowsCheckboxState([pair], true);
      }
      // console.log([file, pair]);
    }

    this.$emit("selected", file);
  }

  onDeselectedRow(file: LaxyFile) {
    if (this.autoSelectPair && this.files && file) {
      const pair = findPair(file, this.files);
      if (pair != null) {
        this._setRowsCheckboxState([pair], false);
      }
      // console.log([file, pair]);
    }
    this.$emit("deselected", file);
  }

  public isInCart(file: LaxyFile) {
    for (let sample of this.$store.state.samples.items) {
      if (sample.files.includes(file)) return true;
    }
    return false;
  }

  public shouldDisableCheckbox(file: LaxyFile) {
    return this.isInCart(file) || file.deleted === true;
  }

  private viewMethods: ViewMethod[] = [
    {
      text: "Open in new tab",
      icon: "open_in_new",
      tags: [],
      method: (file: LaxyFile) => {
        viewFile(file, null, this.jobId);
      },
    },
    {
      text: "Download file",
      icon: "cloud_download",
      tags: [],
      method: (file: LaxyFile) => {
        downloadFile(file, null, this.jobId);
      },
    },
    {
      text: "View report",
      icon: "remove_red_eye",
      tags: ["html", "report"],
      method: (file: LaxyFile) => {
        viewFile(file, null, this.jobId);
      },
    },
    {
      text: "Open in Degust",
      icon: "dashboard",
      tags: ["counts", "degust"],
      method: async (file: LaxyFile) => {
        window.open(
          WebAPI.getExternalAppRedirectUrl("degust", file.id),
          "_blank"
        );
      },
    },
  ];

  public refreshing: boolean = false;

  mounted() {
    // this.fileList = _dummyFileSet.files;
    // this.filesetId = _dummyFileSet.id;
    //this.currentLevel = this.fileTree[4];
    this.currentLevel = this.fileTree;
  }

  // we need this wrapped in a method otherwise the viewMethod.method
  // doesn't have the correct 'this' context to $emit events.
  emitActionError(msg: string) {
    this.$emit("action-error", msg);
  }

  getViewMethodsForTags(tags: string[]) {
    return filter(this.viewMethods, (vm) => hasSharedTagOrEmpty(vm.tags, tags));
  }

  @Memoize((file: LaxyFile) => file.id)
  getDefaultViewMethod(file: LaxyFile) {
    return head(
      filter(this.viewMethods, (vm) => hasIntersection(vm.tags, file.type_tags))
    );
  }

  get files(): LaxyFile[] {
    const nodelist = flattenTree(this.fileTree.children);
    let filtered: LaxyFile[] = map(nodelist, (n) => n.obj as LaxyFile);
    filtered = filterByTag(filtered, this.tagFilters);
    filtered = filterByRegex(filtered, strToRegex(this.regexFilters));
    filtered = excludeByTag(filtered, this.excludeTags)
    return filtered;
  }

  get titleText(): string {
    return this.title;
  }
}
</script>

<style scoped>
/*.md-table-card {*/
/*width: 100%;*/
/*}*/

.strikethrough {
  text-decoration-line: line-through;
}

.unavailable {
  font-style: italic;
  color: #7d7d7d;
}
</style>
