import * as lodash from 'lodash';

export class TreeNode {
    id: string;
    type: 'project'|'folder'|'file';
    name: string;
    parent: TreeNode;
    children: Array<TreeNode> = [];
    selected: boolean;

    public isContainer(): boolean {
        return (this.children != null && this.children.length > 0)
    };
}

export class DataFile extends TreeNode {
    readonly type: 'file' = 'file';
    children: Array<TreeNode> = [];
    pair?: DataFile;

    constructor(fields?: object) {
        super();
        if (fields) {
            (Object as any).assign(this, fields);
        }
    }

    public isContainer(): boolean {
        return false;
    }
}

export class FileSet extends TreeNode {
    type: 'project'|'folder';
    // files: Array<DataFile>;

    children: Array<TreeNode> = [];

    constructor(id: string, type: 'project'|'folder', name: string, files?: Array<DataFile>) {
        super();
        this.id = id;
        this.type = type;
        this.name = name;
        if (files != null) {
            this.children = files;
        }
    }

    public isContainer(): boolean {
        return (this.type === 'project' || this.type === 'folder');
    }

    get files(): Array<DataFile> {
        return lodash.map(this.children, f => {return f as DataFile});
    }

    set files(v: Array<DataFile>) {
        this.children.concat(v);
        this.children = lodash.uniq(this.children);
    }
}
