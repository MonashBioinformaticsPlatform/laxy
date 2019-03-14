import map from 'lodash-es/map';

/**
 * Truncates a string for display, including `frontLen` and `backLen` number
 * of characters from the start and end.
 *
 * Adapted from: https://github.com/kahwee/truncate-middle
 */
export function truncateString(str: string,
                               frontLen: number = 30,
                               backLen: number = 6,
                               truncateStr: string = '⋯'): string {
    if (str === null) {
        return '';
    }
    const strLen = str.length;
    frontLen = Math.round(frontLen);
    backLen = Math.round(backLen);
    if (frontLen === 0 && backLen === 0 || frontLen >= strLen || backLen >= strLen || (frontLen + backLen) >= strLen) {
        return str;
    } else if (backLen === 0) {
        return str.slice(0, frontLen) + truncateStr;
    } else {
        return str.slice(0, frontLen) + truncateStr + str.slice(strLen - backLen);
    }
}

/**
 * Takes a string, or an array of strings, and turns them into RexExp objects.
 */
export function strToRegex(patterns: string[] | string): RegExp[] {
    if (!patterns) return [];
    if (typeof patterns === 'string') patterns = [patterns];
    return map(patterns, (p) => {
        return new RegExp(p);
    });
}

export function browserLocale() {
    return navigator.languages
        ? navigator.languages[0]
        : (navigator.language || (navigator as any).userLanguage);
}

export function reverseString(str: string): string {
    return str.split('').reverse().join('');
}

// https://stackoverflow.com/a/3561711
export function escapeRegExp(str: string) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

export function basename(path: string): string | undefined {
    return path.split(/[\\/]/).pop();
}
