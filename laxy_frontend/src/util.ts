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

/*
* This function truncates a string based on the window width. It's a bit of a fudge since
* the pixel length of the text will vary based on the font and the character composition
* for non-fixed fonts, however it tends to work well enough in the case where you want to
* ensure a string will never be wider that the window and be truncated appropriately.
*
* There might be a nice way to do this in CSS, including internal ellipsis so we can see the
* file extension of truncated filenames, but I haven't found it.
*/
export function widthAwareStringTruncate(str: string, factor: number = 0.085) {
    const charWidth = Math.round(window.innerWidth * factor);
    return truncateString(str, charWidth);
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

export function filenameFromUrl(url: string): string | undefined {
    return basename((new URL(url)).pathname);
}

export function isValidUrl(str: string, schemes: string[] = []) {
    let url;

    try {
        url = new URL(str);
    } catch (_) {
        return false;
    }

    if (schemes) {
        for (let scheme of schemes) {
            if (url.protocol === `${scheme}:`) {
                return true;
            }
        }
        return false;
    }

    return true;
}