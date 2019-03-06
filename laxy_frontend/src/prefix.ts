// Adapted from: https://rosettacode.org/wiki/Longest_common_prefix#ES6

// GENERIC FUNCTIONS --------------------------------

// allSame :: [a] -> Bool
const allSame = (xs: any) =>
    0 === xs.length || (() => {
        const x = xs[0];
        return xs.every((y: any) => x === y);
    })();

// chars :: String -> [Char]
const chars = (s: string) => s.split('');

// concat :: [[a]] -> [a]
// concat :: [String] -> String
const concat = (xs: any) =>
    0 < xs.length ? (() => {
        const unit = 'string' !== typeof xs[0] ? (
            []
        ) : '';
        return unit.concat.apply(unit, xs);
    })() : [];

// cons :: a -> [a] -> [a]
const cons = (x: any, xs: any) => [x].concat(xs);

// head :: [a] -> a
const head = (xs: any) => xs.length ? xs[0] : undefined;

// isNull :: [a] -> Bool
// isNull :: String -> Bool
const isNull = (xs: any) =>
    Array.isArray(xs) || ('string' === typeof xs) ? (
        1 > xs.length
    ) : undefined;

// map :: (a -> b) -> [a] -> [b]
const map = (f: any, xs: any) =>
    (Array.isArray(xs) ? (
        xs
    ) : xs.split('')).map(f);

// show :: a -> String
const show = JSON.stringify;

// tail :: [a] -> [a]
const tail = (xs: any) => 0 < xs.length ? xs.slice(1) : [];

// takeWhile :: (a -> Bool) -> [a] -> [a]
// takeWhile :: (Char -> Bool) -> String -> String
const takeWhile = (p: any, xs: any) => {
    const lng = xs.length;
    return 0 < lng ? xs.slice(
        0,
        until(
            (i: any) => lng === i || !p(xs[i]),
            (i: number) => 1 + i,
            0
        )
    ) : [];
};

// unlines :: [String] -> String
const unlines = (xs: any) => xs.join('\n');

// until :: (a -> Bool) -> (a -> a) -> a -> a
const until = (p: any, f: any, x: any) => {
    let v = x;
    while (!p(v)) v = f(v);
    return v;
};

// lcp :: (Eq a) => [[a]] -> [a]
export function longestCommonPrefix(xxx: any) {
    const go = (xs: any): any => {
        return xs.some(isNull) ? (
            []
        ) : cons(
            map(head, xs),
            go(map(tail, xs))
        );
    };
    return concat(map(
        head,
        takeWhile(
            allSame,
            go(map(chars, xxx))
        )
    ));
}

// TEST ---------------------------------------------

// showPrefix :: [String] -> String
const showPrefix = (xs: any) =>
    concat([show(xs), '  --> ', show(longestCommonPrefix(xs))]);

// main :: IO ()
const main = () => {
    const strResults = unlines(map(
        showPrefix, [
            ['interspecies', 'interstellar', 'interstate'],
            ['throne', 'throne'],
            ['throne', 'dungeon'],
            ['cheese'],
            [''],
            ['prefix', 'suffix'],
            ['foo', 'foobar']
        ]
    ));
    return (
        // console.log(strResults),
        strResults
    );
};
