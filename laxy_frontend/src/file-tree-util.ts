// import * as _ from 'lodash';
import some from 'lodash-es/some';
import first from 'lodash-es/first';
import filter from 'lodash-es/filter';
import intersection from "lodash-es/intersection";
import forEach from 'lodash-es/forEach';
import find from 'lodash-es/find';
import flatten from 'lodash-es/flatten';

import { Store as store } from './store';

import { WebAPI } from './web-api';
import { LaxyFile } from './model';
import { LaxyFileSet } from './types';

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
    type?: 'file' | 'directory';
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
    if (tags == null || tags.length === 0 || files == null) {
        return files;
    }
    const tag_filtered: LaxyFile[] = [];
    for (const file of files) {
        if (file.type_tags == null) { continue };
        for (const tag of tags) {
            if (file.type_tags.includes(tag) &&
                !tag_filtered.includes(file)) {
                tag_filtered.push(file);
            }
        }
    }

    return tag_filtered;
}

export function excludeByTag(files: LaxyFile[], tags: string[] | null): LaxyFile[] {
    if (tags == null || tags.length === 0 || files == null) {
        return files;
    }

    return filter(files, (f: LaxyFile) => {
        return f.type_tags == null || !intersection(f.type_tags, tags).length;
    })
}

export function filterByRegex(files: LaxyFile[], patterns: RegExp[] | null): LaxyFile[] {
    if (patterns == null || patterns.length === 0 || files == null) {
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
    if (query == null || query.length === 0 || files == null) {
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

export function filterByFullPath(files: LaxyFile[], query: string | null, caseSensitive: boolean = true): LaxyFile[] {
    if (!query || query.length === 0 || files == null) {
        return files;
    }
    if (caseSensitive) {
        return filterBy(files, query, (f: LaxyFile) => `${f.path}/${f.name}`);
    } else {
        return filterBy(files, query.toLowerCase(), (f: LaxyFile) => `${f.path}/${f.name}`.toLowerCase());
    }
}

export function filterByFilename(files: LaxyFile[], query: string | null, caseSensitive: boolean = true): LaxyFile[] {
    if (!query || query.length === 0 || files == null) {
        return files;
    }
    if (caseSensitive) {
        return filterBy(files, query, (f: LaxyFile) => f.name);
    } else {
        return filterBy(files, query.toLowerCase(), (f: LaxyFile) => f.name.toLowerCase());
    }
}

export function viewFile(file_id: string | LaxyFile,
    fileset: LaxyFileSet | null,
    job_id: string | null) {
    let file: LaxyFile | undefined;
    if (file_id instanceof String) {
        file = store.getters.fileById(file_id, fileset);
    } else {
        file = file_id as LaxyFile;
    }
    const access_token = store.getters.jobAccessToken(job_id);
    if (file) {
        if (job_id) {
            const filepath = `${file.path}/${file.name}`;
            window.open(WebAPI.viewJobFileByPathUrl(job_id, filepath, access_token));
        } else {
            // window.open(WebAPI.viewFileByIdUrl(file.id, file.name, access_token), '_blank');
            window.open(WebAPI.viewFileByIdUrl(file.id, file.name, access_token));
        }
    } else {
        console.error(`Invalid file_id: ${file_id}`);
    }
}

export function downloadFile(file_id: string | LaxyFile,
    fileset: LaxyFileSet | null,
    job_id: string | null) {
    let file: LaxyFile | undefined;
    if (file_id instanceof String) {
        file = store.getters.fileById(file_id, fileset);
    } else {
        file = file_id as LaxyFile;
    }
    const access_token = store.getters.jobAccessToken(job_id);
    if (file) {
        if (job_id) {
            const filepath = `${file.path}/${file.name}`;
            window.open(WebAPI.downloadJobFileByPathUrl(job_id, filepath, access_token));
        } else {
            window.open(WebAPI.downloadFileByIdUrl(file.id, file.name, access_token));
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
    fn = fn.replace('.fq.gz', '');  // BGI does this, it seems
    fn = fn.replace('.fastq', '');  // Occasionally we need to take uncompressed fastqs
    return fn;
}

/**
 * Given a FASTQ filename XXXBLAFOO_L004_R1.fastq.gz, return something like the 
 *'sample name' XXXBLAFOO. Should work with typical naming used by Illumina 
 * instruments and SRA/ENA FASTQ files.
 * @param filename The filename
 */
export function simplifyFastqName(filename: string): string {
    let fn = truncateFastqFilename(filename);
    // eg remove suffix _L002_R1 or L003_2 or _2, or just _R2
    fn = fn.replace(/_(R)?[1-2]$|_L[0-9][0-9][0-9]_(R)?[1-2]$/, '');
    return fn;
}

/**
 * Determine if a file is R1 based on its filename.
 * Supports common R1 suffixes used by Illumina instruments and SRA/ENA.
 */
export function isR1File(filename: string): boolean {
    const r1_patterns = [
        /_R1_001\.(fastq|fq|fasta|fa)\.gz$/,  // Illumina instrument default
        /_r1_001\.(fastq|fq|fasta|fa)\.gz$/,  // Synapse bulk downloader renames to lowercase
        /_R1\.(fastq|fq|fasta|fa)\.gz$/,      // Generic R1
        /_1\.(fastq|fq|fasta|fa)\.gz$/,       // ENA/SRA
        /_R1\.(fastq|fq|fasta|fa)$/,          // Uncompressed variants
        /_1\.(fastq|fq|fasta|fa)$/,
    ];
    
    return r1_patterns.some(pattern => pattern.test(filename));
}

/**
 * Given a file object (eg _R1 or _R2) and a list of file objects (potential pair), 
 * return the corresponding R1 or R2 pair.
 * @param file A file with a ILaxyFile-like interface.
 * @param files A list of files with a ILaxyFile-like interface.
 * @param getName A function that returns the filenname from the file object 
 *                - defaults to grabbing the 'name' attribute.
 */
export function findPair(file: any, files: any[], getName: Function | null = null): any | null {
    const lastChar = (s: string) => s.slice(-1);
    const dropLast = (s: string) => s.slice(0, -1);

    if (getName == null) {
        getName = (f: any) => f.name;
    }
    const fn = truncateFastqFilename(getName(file));
    for (const f of files) {
        if (f === null) continue;
        const other = truncateFastqFilename(getName(f));
        if (dropLast(fn) === dropLast(other) &&
            (Number(lastChar(fn)) + Number(lastChar(other))) === 3) {
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
            const existingPath: TreeNode<T> = find(currentLevel.children, { name: part.name }) as any;

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
