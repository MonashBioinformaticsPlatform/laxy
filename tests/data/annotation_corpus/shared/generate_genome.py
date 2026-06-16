#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Regenerate the shared synthetic test genome (two chromosomes).

Bacterial-scale on purpose so STAR/Salmon/HISAT2 indices build in seconds.
Real ACGT (no N-runs) so reads extracted from it map uniquely.

Deterministic: same --seed -> identical bytes. Commit the output; CI never
regenerates unless invoked explicitly (see `just annotation-fixtures`).

Headers carry SnapGene-style trailing free text so the FASTA header parser
(first whitespace token = seqid) and the seqid-overlap pre-flight check are
both exercised. ``Accession:`` tokens (TEST_CHR1 / TEST_CHR2) are used by the
F3 (seqid_mismatch) fixture.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

_BASES = "ACGT"


def make_seq(n: int, rng: random.Random) -> str:
    """Random DNA with GC~50%, no homopolymer run longer than 4."""
    out: list[str] = []
    prev = ""
    run = 0
    for _ in range(n):
        b = rng.choice(_BASES)
        if b == prev and run >= 3:
            b = rng.choice([x for x in _BASES if x != b])
            run = 1
        else:
            run = run + 1 if b == prev else 1
        out.append(b)
        prev = b
    return "".join(out)


def wrap(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260614)
    ap.add_argument("--chr1", type=int, default=100_000)
    ap.add_argument("--chr2", type=int, default=50_000)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    chroms = [
        ("chr1", args.chr1, "synthetic test contig 1", "TEST_CHR1"),
        ("chr2", args.chr2, "synthetic test contig 2", "TEST_CHR2"),
    ]
    lines: list[str] = []
    for name, n, desc, acc in chroms:
        lines.append(f">{name} {desc} ({n} bp)   Accession: {acc}")
        lines.append(wrap(make_seq(n, rng)))
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
