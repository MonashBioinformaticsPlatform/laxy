#!/usr/bin/env python3
"""Copy a biotype attribute from GTF transcript rows onto their child rows.

Exists to work around a real nf-core/rnaseq limitation for GFF3-origin
input: nf-core's own ``PREPARE_GENOME`` converts ``--gff`` input to GTF via
``gffread`` internally, and ``gffread`` only carries attributes like
``gbkey``/``gene_biotype`` onto the ``transcript`` row - never onto the
``exon``/``CDS`` rows that ``featureCounts -t exon --extraAttributes gbkey``
(both nf-core's own internal ``SUBREAD_FEATURECOUNTS`` and Laxy's own
``featurecounts_postnfcore.nf``) actually counts and reads attributes from.
Without this, the biotype column comes back empty for every gene in GFF3
jobs even though the counts themselves are correct - not a crash, just
silently missing data. Confirmed against the synthetic annotation corpus's
``E3_eukaryote_refseq`` case: ``gbkey`` is present on ``transcript`` rows but
absent on ``exon``/``CDS`` rows of nf-core's own ``*.filtered.gtf``.

Only meaningful for GTF where child rows lack the biotype attribute (GFF3
inputs, once converted); a no-op pass-through for GTF that already repeats
the attribute on every row (Ensembl/GENCODE convention), since existing
values are never overwritten.

Uses Python 3.9+ standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import sys
from pathlib import Path
from typing import IO, Dict, cast

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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True,
                   help="Input GTF (plain or .gz).")
    p.add_argument("--output", type=Path, required=True,
                   help="Output GTF path (same compression as input).")
    p.add_argument("--biotype-attr", required=True,
                   help="Attribute name to propagate, e.g. gbkey or gene_biotype.")
    p.add_argument("--parent-feature-type", default="transcript",
                   help="Column-3 feature type carrying the source attribute.")
    args = p.parse_args()

    if not args.input.is_file():
        log.error("Input does not exist or is not a file: %s", args.input)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    transcript_biotype: Dict[str, str] = {}
    with open_text_read(args.input) as fin:
        for raw in fin:
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9 or parts[2] != args.parent_feature_type:
                continue
            attrs = parse_gtf_attrs(parts[8])
            value = attrs.get(args.biotype_attr)
            tid = attrs.get("transcript_id")
            if value and tid and tid not in transcript_biotype:
                transcript_biotype[tid] = value

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
            if args.biotype_attr not in attrs:
                value = transcript_biotype.get(attrs.get("transcript_id", ""))
                if value:
                    col9 = parts[8].rstrip()
                    if not col9.endswith(";"):
                        col9 += ";"
                    col9 += f' {args.biotype_attr} "{value}";'
                    parts[8] = col9
                    raw = "\t".join(parts) + "\n"
                    propagated_rows += 1
            fout.write(raw)

    log.info(
        "propagate_biotype_to_features: biotype_attr=%s parent_feature_type=%s "
        "transcripts_with_biotype=%d input_rows=%d propagated_rows=%d",
        args.biotype_attr, args.parent_feature_type,
        len(transcript_biotype), input_rows, propagated_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
