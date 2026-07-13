#!/usr/bin/env python3
"""Copy attributes from GTF transcript rows onto their child rows.

Exists to work around a real nf-core/rnaseq limitation for GFF3-origin
input: nf-core's own ``PREPARE_GENOME`` converts ``--gff`` input to GTF via
``gffread`` internally, and ``gffread`` only carries attributes like
``gbkey``/``gene_biotype``/``Name`` onto the ``transcript`` row - never onto
the ``exon``/``CDS`` rows that ``featureCounts -t exon --extraAttributes
...`` (both nf-core's own internal ``SUBREAD_FEATURECOUNTS`` and Laxy's own
``featurecounts_postnfcore.nf``) actually counts and reads attributes from.
Without this, the biotype/gene-name columns come back empty for every gene
in GFF3 jobs even though the counts themselves are correct - not a crash,
just silently missing data. Confirmed against the synthetic annotation
corpus's ``E3_eukaryote_refseq`` case: ``gbkey``/``Name`` are present on
``transcript`` rows but absent on ``exon``/``CDS`` rows of nf-core's own
``*.filtered.gtf``.

Each ``--attr`` propagates one attribute from the parent row down onto
child rows missing it, optionally renaming it (``SRC:DST``) - needed
because gffread's GFF3->GTF conversion writes the gene-name-equivalent
attribute as ``Name`` (uppercase), not the ``gene_name`` that featureCounts
is asked to report via ``--extraAttributes``.

Only meaningful for GTF where child rows lack the attribute (GFF3 inputs,
once converted); a no-op pass-through for GTF that already repeats the
attribute on every row (Ensembl/GENCODE convention), since existing values
are never overwritten.

Uses Python 3.9+ standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import sys
from pathlib import Path
from typing import IO, Dict, Tuple, cast

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)


def is_gzipped(path: Path) -> bool:
    try:
        with path.open("rb") as fp:
            return fp.read(2) == b"\x1f\x8b"
    except OSError:
        return path.suffix == ".gz"


def open_text_read(path: Path) -> IO[str]:
    if is_gzipped(path):
        return cast(IO[str], gzip.open(path, "rt", encoding="utf-8", errors="replace"))
    return open(path, "rt", encoding="utf-8", errors="replace")


def open_text_write(path: Path) -> IO[str]:
    if path.suffix == ".gz" or str(path).endswith(".gz"):
        return cast(IO[str], gzip.open(path, "wt", encoding="utf-8"))
    return open(path, "wt", encoding="utf-8")


def parse_gtf_attrs(col9: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in col9.split(";"):
        part = part.strip()
        if not part or " " not in part:
            continue
        k, _, v = part.partition(" ")
        k = k.strip()
        v = v.strip().strip('"')
        if k and k not in out:
            out[k] = v
    return out


def parse_attr_rule(raw: str) -> Tuple[str, str]:
    src, _, dst = raw.partition(":")
    src = src.strip()
    dst = dst.strip() or src
    return src, dst


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True,
                   help="Input GTF (plain or .gz).")
    p.add_argument("--output", type=Path, required=True,
                   help="Output GTF path (same compression as input).")
    p.add_argument("--attr", dest="attrs", action="append", default=[],
                   help="SRC or SRC:DST attribute to propagate, e.g. gbkey or "
                        "Name:gene_name. Repeatable.")
    p.add_argument("--biotype-attr",
                   help="Deprecated alias for --attr (no rename).")
    p.add_argument("--parent-feature-type", default="transcript",
                   help="Column-3 feature type carrying the source attribute.")
    args = p.parse_args()

    rules: list[Tuple[str, str]] = [parse_attr_rule(a) for a in args.attrs]
    if args.biotype_attr:
        rules.append((args.biotype_attr, args.biotype_attr))
    if not rules:
        log.error("At least one --attr (or --biotype-attr) is required.")
        return 1

    if not args.input.is_file():
        log.error("Input does not exist or is not a file: %s", args.input)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # transcript_id -> {dst_attr: value}
    transcript_values: Dict[str, Dict[str, str]] = {}
    with open_text_read(args.input) as fin:
        for raw in fin:
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9 or parts[2] != args.parent_feature_type:
                continue
            attrs = parse_gtf_attrs(parts[8])
            tid = attrs.get("transcript_id")
            if not tid:
                continue
            for src, dst in rules:
                value = attrs.get(src)
                if value:
                    transcript_values.setdefault(tid, {}).setdefault(dst, value)

    input_rows = 0
    propagated_rows = 0
    with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
        for raw in fin:
            if not raw.strip() or raw.startswith("#"):
                fout.write(raw)
                continue
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9:
                fout.write(raw)
                continue

            input_rows += 1
            attrs = parse_gtf_attrs(parts[8])
            tid = attrs.get("transcript_id", "")
            values = transcript_values.get(tid, {})
            additions = [
                (dst, value) for dst, value in values.items() if dst not in attrs
            ]
            if additions:
                col9 = parts[8].rstrip()
                if not col9.endswith(";"):
                    col9 += ";"
                for dst, value in additions:
                    col9 += f' {dst} "{value}";'
                parts[8] = col9
                raw = "\t".join(parts) + "\n"
                propagated_rows += 1
            fout.write(raw)

    log.info(
        "propagate_biotype_to_features: rules=%s parent_feature_type=%s "
        "transcripts_with_values=%d input_rows=%d propagated_rows=%d",
        rules, args.parent_feature_type,
        len(transcript_values), input_rows, propagated_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
