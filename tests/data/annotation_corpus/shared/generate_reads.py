#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Emit synthetic FASTQ from the shared genome at annotation feature coords.

Reads are extracted from the feature spans of the given annotation so they
always land on counted features (featureCounts/Salmon get real counts).
Strand-aware: for genes on the '-' strand R1/R2 are reverse-complemented so
pairs point inward like a real stranded library.

Used by the e2e tier (nf-core/rnaseq). Lower tiers (detect/filter/seqid) do
not need reads, so this only runs when the e2e fixture requests it. The test
harness caches output under ``cases/<id>/reads/``.

Deterministic: fixed --seed -> identical reads, so results are reproducible.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import random
import sys
from pathlib import Path

_COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def rc(s: str) -> str:
    return s.translate(_COMP)[::-1]


def parse_fasta(path: Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    name: str | None = None
    buf: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if name is not None:
                seqs[name] = "".join(buf)
            name = line[1:].split()[0]
            buf = []
        elif line.strip():
            buf.append(line.strip())
    if name is not None:
        seqs[name] = "".join(buf)
    return seqs


def features(ann: Path, ftype: str) -> list[tuple[str, int, int, str]]:
    """Return (seqid, start, end, strand) for rows whose col3 == ftype.

    Coordinates are 1-based inclusive (GTF/GFF convention). Mangled rows and
    the trailing GFF3 ##FASTA section are skipped. Handles gzip input.
    """
    opener = gzip.open if str(ann).endswith(".gz") else open
    text = opener(ann, "rt", encoding="utf-8", errors="replace").read()
    out: list[tuple[str, int, int, str]] = []
    in_fasta = False
    for line in text.splitlines():
        if line.startswith("##FASTA"):
            in_fasta = True
            continue
        if in_fasta or not line or line.startswith("#"):
            continue
        parts = line.rstrip("\r").split("\t")
        if len(parts) != 9 or parts[2] != ftype:
            continue
        try:
            out.append((parts[0], int(parts[3]), int(parts[4]), parts[6]))
        except ValueError:
            continue
    return out


def open_w(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8")
    return open(path, "wt", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--genome", type=Path, required=True)
    ap.add_argument("--annotation", type=Path, required=True)
    ap.add_argument("--feature-type", default="CDS",
                    help="Column-3 feature type to draw reads from.")
    ap.add_argument("-n", "--count", type=int, default=2000)
    ap.add_argument("-l", "--read-length", type=int, default=75)
    ap.add_argument("-f", "--fragment", type=int, default=200,
                    help="Median fragment (insert) size.")
    ap.add_argument("--mode", choices=["paired", "single"], default="paired")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-prefix", required=True,
                    help="Path prefix; .fastq.gz is appended.")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    genome = parse_fasta(args.genome)
    feats = features(args.annotation, args.feature_type)
    if not feats:
        sys.exit(f"no '{args.feature_type}' features in {args.annotation}")

    rl = args.read_length
    frag = max(args.fragment, rl)
    qual = "I" * rl

    r1_path = Path(f"{args.out_prefix}_R1.fastq.gz")
    r2_path = Path(f"{args.out_prefix}_R2.fastq.gz") if args.mode == "paired" else None

    emitted = 0
    with open_w(r1_path) as f1, (open_w(r2_path) if r2_path else contextlib.nullcontext()) as f2:
        while emitted < args.count:
            seqid, start, end, strand = rng.choice(feats)
            chrom = genome.get(seqid)
            if chrom is None or end - start + 1 < frag:
                continue
            f_start = rng.randint(start - 1, end - frag)  # 0-based slice start
            left = chrom[f_start:f_start + rl]
            right = chrom[f_start + frag - rl:f_start + frag]
            if strand == "-":
                # inward-oriented reverse-strand pair
                left, right = rc(right), rc(left)
            if len(left) < rl or len(right) < rl:
                continue
            emitted += 1
            f1.write(f"@read{emitted}/1\n{left}\n+\n{qual}\n")
            if f2 is not None:
                f2.write(f"@read{emitted}/2\n{right}\n+\n{qual}\n")

    print(f"wrote {emitted} {args.mode} reads -> {r1_path}"
          + (f" / {r2_path}" if r2_path else ""))


if __name__ == "__main__":
    main()
