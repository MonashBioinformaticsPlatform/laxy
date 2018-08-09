// instead / supplement to @types/vue-material

declare interface MdDialog extends Element {
    open: Function;
    close: Function;
}

declare interface MdTable extends Element {
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
}
