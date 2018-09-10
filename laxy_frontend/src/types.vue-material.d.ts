// instead / supplement to @types/vue-material
// import {Vue} from 'vue/types/vue';

declare interface MdDialog extends Element {
    open: Function;
    close: Function;
}

declare interface MdTable extends Element {
    // vue
    readonly $children: any[];
    readonly data: any;
    // data
    selectedRows: any[];
    hasRowSelection: boolean;
    sortBy: any;
    sortType: any;

    // computed
    numberOfRows: number;
    numberOfSelected: number;
    themeClass: string;
    mdEffectiveTheme: string;

    // props
    mdSort: string;
    mdSortType: string;
    mdTheme: string;

    // methods
    setRowSelection(selected: boolean, row: any): void;
}

// declare module 'vue2-collapse' {
//     const VueCollapse: any;
//     export = VueCollapse;
// }
