// import * as _ from 'lodash';
import some from 'lodash-es/some';
import first from 'lodash-es/first';
import filter from 'lodash-es/filter';
import forEach from 'lodash-es/forEach';
import find from 'lodash-es/find';

import {Store as store} from './store';

import {WebAPI} from './web-api';
import {LaxyFile} from './model';

export interface TreeNode {
    id: string;
    name: string;
    file: LaxyFile | null;
    parent: TreeNode | null;
    children: TreeNode[];
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

export function viewFile(file_id: string | LaxyFile, fileset: LaxyFileSet | null, job_id: string | null) {
    let file: LaxyFile | undefined;
    if (file_id instanceof LaxyFile) {
        file = file_id;
    } else {
        file = store.getters.fileById(file_id, fileset);
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
    if (file_id instanceof LaxyFile) {
        file = file_id;
    } else {
        file = store.getters.fileById(file_id, fileset);
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

export function fileListToTree(files: LaxyFile[]): TreeNode {
    const tree: TreeNode = {
        id: '__root__',
        name: '/',
        file: null,
        parent: null,
        children: [],
    } as TreeNode;

    let id_counter = 0;  // alternative ID used when there is no File UUID

    for (const file of files) {
        const pathPartStrings = `${file.path}/${file.name}`.split('/');
        pathPartStrings.shift(); // Remove first blank element from the parts array.
        const pathParts: TreeNode[] = [];
        // Turn each/part/of/the/path into a TreeNode
        for (const partName of pathPartStrings) {
            pathParts.push({
                id: id_counter.toString(),
                name: partName,
                file: null,
                parent: null,
                children: [] as TreeNode[]
            });
            id_counter++;
        }

        // The last element in full path is the file (no such thing as empty
        // directories)
        pathParts[pathParts.length - 1].file = file;
        pathParts[pathParts.length - 1].id = file.id;

        let currentLevel: TreeNode = tree; // initialize currentLevel to the root of the tree

        // walk up the path. for each subdirectory, determine if it is already
        // represented as a node in the tree else add it
        forEach(pathParts, (part => {
            const existingPath: TreeNode = find(currentLevel.children, {name: part.name}) as any;

            if (existingPath) {
                // The path to this item was already in the tree, so don't add it again.
                // Set the current level to this path's children
                currentLevel = existingPath;
            } else {
                const newPart = {
                    id: part.id,
                    name: part.name,
                    file: part.file,
                    parent: currentLevel,
                    children: [] as TreeNode[],
                } as TreeNode;

                currentLevel.children.push(newPart);
                currentLevel = newPart;
            }
        }));
    }
    return tree;
}
