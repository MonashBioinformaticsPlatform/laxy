// import * as _ from 'lodash';
import some from 'lodash-es/some';
import first from 'lodash-es/first';
import filter from 'lodash-es/filter';
import forEach from 'lodash-es/forEach';
import find from 'lodash-es/find';
import flatten from 'lodash-es/flatten';

import {Store as store} from './store';

import {WebAPI} from './web-api';
import {LaxyFile} from './model';

export interface TreeNode<T> {
    id: string;
    name: string;
    obj: T | null;
    meta: any;  // optional extra data like icon names, onclick callbacks
    parent: TreeNode<T> | null;
    children: Array<TreeNode<T>>;
}

export interface FileListItem {
    name: string;
    type: 'file' | 'directory';
    tags: string[];
    location: string;
}

export const EMPTY_TREE_ROOT: TreeNode<any> = {
    id: '__root__',
    name: '/',
    obj: null,
    meta: {},
    parent: null,
    children: [],
} as TreeNode<any>;

export function is_archive_url(url: string): boolean {
    const tar_suffixes = ['.tar', '.tar.gz', '.tar.bz2'];
    return some(tar_suffixes, (v) => url.endsWith(v));
}

export function hasIntersection(a: any[] | null, b: any[] | null): boolean {
    if (a == null || b == null ||
        a.length === 0 || b.length === 0) return false;

    return some(a, i => b.includes(i));
}

export function hasSharedTagOrEmpty(viewMethodTags: any[], file_type_tags: any[]) {
    return viewMethodTags.length === 0 ||
        hasIntersection(viewMethodTags, file_type_tags);
}

export function filterByTag(files: LaxyFile[], tags: string[] | null): LaxyFile[] {
    if (tags == null || tags.length === 0) {
        return files;
    }
    const tag_filtered: LaxyFile[] = [];
    for (const file of files) {
        for (const tag of tags) {
            if (file.type_tags.includes(tag) &&
                !tag_filtered.includes(file)) {
                tag_filtered.push(file);
            }
        }
    }

    return tag_filtered;
}

export function filterByRegex(files: LaxyFile[], patterns: RegExp[] | null): LaxyFile[] {
    if (patterns == null || patterns.length === 0) {
        return files;
    }
    const regex_filtered: LaxyFile[] = [];
    for (const file of files) {
        for (const regex of patterns) {
            if (regex.test(file.name) &&
                !regex_filtered.includes(file)) {
                regex_filtered.push(file);
            }
        }
    }

    return regex_filtered;
}

export function filterBy(files: LaxyFile[],
                         query: string | null,
                         map_fn: Function): LaxyFile[] {
    if (query == null || query.length === 0) {
        return files;
    }
    const query_filtered: LaxyFile[] = [];
    for (const file of files) {
        const subject = map_fn(file);
        if (subject.includes(query) &&
            !query_filtered.includes(file)) {
            query_filtered.push(file);
        }
    }
    return query_filtered;
}

export function filterByFullPath(files: LaxyFile[], query: string | null): LaxyFile[] {
    return filterBy(files, query, (f: LaxyFile) => `${f.path}/${f.name}`);
}

export function filterByFilename(files: LaxyFile[], query: string | null): LaxyFile[] {
    return filterBy(files, query, (f: LaxyFile) => f.name);
}

export function viewFile(file_id: string | LaxyFile, fileset: LaxyFileSet | null, job_id: string | null) {
    let file: LaxyFile | undefined;
    if (file_id instanceof String) {
        file = store.getters.fileById(file_id, fileset);
    } else {
        file = file_id as LaxyFile;
    }
    if (file) {
        if (job_id) {
            const filepath = `${file.path}/${file.name}`;
            window.open(WebAPI.viewJobFileByPathUrl(job_id, filepath));
        } else {
            // window.open(WebAPI.viewFileByIdUrl(file.id, file.name), '_blank');
            window.open(WebAPI.viewFileByIdUrl(file.id, file.name));
        }
    } else {
        console.error(`Invalid file_id: ${file_id}`);
    }
}

export function downloadFile(file_id: string | LaxyFile, fileset: LaxyFileSet | null, job_id: string | null) {
    let file: LaxyFile | undefined;
    if (file_id instanceof String) {
        file = store.getters.fileById(file_id, fileset);
    } else {
        file = file_id as LaxyFile;
    }
    if (file) {
        if (job_id) {
            const filepath = `${file.path}/${file.name}`;
            window.open(WebAPI.downloadJobFileByPathUrl(job_id, filepath));
        } else {
            window.open(WebAPI.downloadFileByIdUrl(file.id, file.name));
        }
    } else {
        console.error(`Invalid file_id: ${file_id}`);
    }
}

/* Turn a XXXBLAFOO_R1.fastq.gz filename into XXXBLAFOO_R1 */
export function truncateFastqFilename(filename: string): string {
    let fn = filename.replace('_001.fastq.gz', ''); // default Illumina
    fn = fn.replace('.fastq.gz', '');  // ENA/SRA
    fn = fn.replace('.fasta.gz', '');  // occasionally we get FASTA format reads
    return fn;
}

/* Given a typical FASTQ filename, XXXBLAFOO_R1.fastq.gz, return something like
   the 'sample name' XXXBLAFOO.
 */
export function simplifyFastqName(filename: string): string {
    let fn = truncateFastqFilename(filename);
    fn = fn.replace(/_1$|_2$|_R1$|_R2$/, '');
    return fn;
}

/*
 Given a file and a list of
 */
export function findPair(file: any, files: any[], getName: Function | null = null): any | null {
    if (getName == null) {
        getName = (f: any) => f.name;
    }
    const fn = truncateFastqFilename(getName(file));
    for (const f of files) {
        const other = truncateFastqFilename(getName(f));
        if (fn.slice(0, -1) === other.slice(0, -1) &&
            (parseInt(fn.slice(-1), 10) + parseInt(other.slice(-1), 10)) === 3) {
            return f;
        }
    }
    return null;
}

export function fileListToTree(files: LaxyFile[]): TreeNode<LaxyFile> {
    return objListToTree<LaxyFile>(files,
        (f: LaxyFile) => {
            const parts = `${f.path}/${f.name}`.split('/');
            parts.shift();
            return parts;
        },
        (f: LaxyFile) => {
            return f.id;
        });
}

export function objListToTree<T>(objs: T[],
                                 getPathParts: Function,
                                 getId: Function): TreeNode<T> {
    const tree: TreeNode<T> = {
        id: '__root__',
        name: '/',
        obj: null,
        meta: {},
        parent: null,
        children: [],
    } as TreeNode<T>;

    let id_counter = 0;  // alternative ID used when there is no File UUID

    for (const obj of objs) {
        // const pathPartStrings = `${file.path}/${file.name}`.split('/');
        const pathPartStrings: string[] = getPathParts(obj);
        // pathPartStrings.shift(); // Remove first blank element from the parts array.
        const pathParts: Array<TreeNode<T>> = [];
        // Turn each/part/of/the/path into a TreeNode
        for (const partName of pathPartStrings) {
            pathParts.push({
                id: id_counter.toString(),
                name: partName,
                obj: null,
                meta: {},
                parent: null,
                children: [] as Array<TreeNode<T>>
            });
            id_counter++;
        }

        // The last element in full path is the file (no such thing as empty directories)
        const lastpart = pathParts[pathParts.length - 1];
        lastpart.obj = obj;
        lastpart.id = getId(obj);
        lastpart.meta.type = 'file';
        for (let i = 0; i < pathParts.length - 1; i++) {
            pathParts[i].meta.type = 'directory';
        }

        let currentLevel: TreeNode<T> = tree;  // initialize currentLevel to the root of the tree

        // walk up the path. for each subdirectory, determine if it is already
        // represented as a node in the tree else add it
        forEach(pathParts, (part => {
            const existingPath: TreeNode<T> = find(currentLevel.children, {name: part.name}) as any;

            if (existingPath) {
                // The path to this item was already in the tree, so don't add it again.
                // Set the current level to this path's children
                currentLevel = existingPath;
            } else {
                const newPart = {
                    id: part.id,
                    name: part.name,
                    obj: part.obj,
                    meta: part.meta,
                    parent: currentLevel,
                    children: [] as Array<TreeNode<T>>,
                } as TreeNode<T>;

                currentLevel.children.push(newPart);
                currentLevel = newPart;
            }
        }));
    }
    return tree;
}

export function flattenTree<T>(nodes: Array<TreeNode<T>>): Array<TreeNode<T>> {
    if (!nodes || nodes.length === 0) return [];
    return nodes.concat(
        flattenTree(
            flatten(nodes.map((n: TreeNode<T>) => n.children))
        )
    );
}
