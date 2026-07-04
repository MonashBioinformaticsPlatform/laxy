#!/usr/bin/env python3
"""Remove whole gene groups matching a biotype drop-list from a GTF/GFF3.

Exists to work around a real nf-core/rnaseq failure: with
``--gtf_group_features Parent`` (or any grouping attribute), Salmon
quantifies a transcript for every group regardless of biotype. Real NCBI
RefSeq annotations commonly give non-coding RNA genes (tRNA, rRNA, ...) an
``ID=rna-<NAME>`` with no ``transcript_id``-equivalent attribute; nf-core's
tximport/SummarizedExperiment step (``QUANTIFY_STAR_SALMON`` /
``QUANTIFY_PSEUDO_ALIGNMENT`` - the *same* subworkflow under two names) then
can't find a metadata column containing those ids and the whole run dies
with "No column contains all vector entries ...". See
ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7.

Confirmed against real Laxy prod with the genuine NCBI human (NC_012920.1)
and mouse (NC_005089.1) mitochondrial RefSeq annotations, and reproduced
locally in the synthetic corpus as ``E5_eukaryote_ncrna_ids``.

Only called (from ``run_job.sh``) when ``detect_annotation_style.py`` finds
non-coding RNA biotypes *alongside* at least one other biotype - if the
whole annotation is non-coding RNA there's nothing else to quantify anyway,
so this is left alone.

GFF3 input: biotype lives on the ``gene`` row; child rows (mRNA/tRNA/rRNA,
exon, CDS, ...) are matched by walking ``Parent=`` chains, since dropping
just the gene row would leave orphaned children for gffread/STAR/Salmon to
choke on. GTF input: each row usually carries its own ``gene_biotype``
attribute directly (Ensembl/GENCODE convention), so rows are dropped
individually with no parent-chain walk needed.

Uses Python 3.9+ standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import sys
from pathlib import Path
from typing import IO, Dict, List, Optional, Set, cast

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

_BIOTYPE_ATTR_CANDIDATES = ("gene_biotype", "gene_type", "biotype")


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


def parse_gff3_attrs(col9: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in col9.strip().split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        if k and k not in out:
            out[k] = v.strip()
    return out


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


def biotype_value(attrs: Dict[str, str]) -> Optional[str]:
    for cand in _BIOTYPE_ATTR_CANDIDATES:
        v = attrs.get(cand)
        if v:
            return v
    return None


def find_drop_ids_gff3(path: Path, drop_biotypes: Set[str]) -> Set[str]:
    """Return the set of GFF3 row IDs to drop: biotype-matched rows plus
    every descendant reached by walking ``Parent=`` chains."""
    id_biotype: Dict[str, str] = {}
    id_parents: Dict[str, List[str]] = {}

    with open_text_read(path) as fp:
        in_fasta = False
        for raw in fp:
            if raw.startswith("##FASTA"):
                in_fasta = True
                continue
            if in_fasta or raw.startswith("#") or not raw.strip():
                continue
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9:
                continue
            attrs = parse_gff3_attrs(parts[8])
            row_id = attrs.get("ID")
            if not row_id:
                continue
            bt = biotype_value(attrs)
            if bt:
                id_biotype[row_id] = bt
            parent = attrs.get("Parent")
            if parent:
                id_parents[row_id] = [p.strip() for p in parent.split(",") if p.strip()]

    drop_ids: Set[str] = {rid for rid, bt in id_biotype.items() if bt in drop_biotypes}
    changed = True
    while changed:
        changed = False
        for rid, parents in id_parents.items():
            if rid in drop_ids:
                continue
            if any(p in drop_ids for p in parents):
                drop_ids.add(rid)
                changed = True
    return drop_ids


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True,
                   help="Input annotation (GTF or GFF3, plain or .gz).")
    p.add_argument("--output", type=Path, required=True,
                   help="Output path (same format as input).")
    p.add_argument("--format", required=True, choices=("gtf", "gff3"),
                   help="Matches detect_annotation_style.py ANN_FORMAT.")
    p.add_argument("--drop-biotypes", default="",
                   help="Comma-separated gene_biotype/gene_type/biotype "
                        "values to remove (matches ANN_DROP_BIOTYPES).")
    args = p.parse_args()

    if not args.input.is_file():
        log.error("Input does not exist or is not a file: %s", args.input)
        return 1

    drop_biotypes = {b.strip() for b in args.drop_biotypes.split(",") if b.strip()}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if not drop_biotypes:
        log.info("annotation_drop_biotype: no drop_biotypes given, passing through unchanged")
        with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
            for line in fin:
                fout.write(line)
        return 0

    is_gff3 = args.format == "gff3"
    drop_ids = find_drop_ids_gff3(args.input, drop_biotypes) if is_gff3 else set()

    input_rows = 0
    kept_rows = 0
    dropped_rows = 0

    with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
        in_fasta = False
        for raw in fin:
            if raw.startswith("##FASTA"):
                in_fasta = True
                fout.write(raw)
                continue
            if in_fasta or raw.startswith("#") or not raw.strip():
                fout.write(raw)
                continue

            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9:
                fout.write(raw)
                continue

            input_rows += 1
            attrs = parse_gff3_attrs(parts[8]) if is_gff3 else parse_gtf_attrs(parts[8])

            if is_gff3:
                row_id = attrs.get("ID")
                drop = bool(row_id) and row_id in drop_ids
            else:
                drop = biotype_value(attrs) in drop_biotypes

            if drop:
                dropped_rows += 1
                continue

            fout.write(raw)
            kept_rows += 1

    log.info(
        "annotation_drop_biotype: format=%s drop_biotypes=%s "
        "input_rows=%d kept_rows=%d dropped_rows=%d dropped_ids=%d",
        args.format, ",".join(sorted(drop_biotypes)),
        input_rows, kept_rows, dropped_rows, len(drop_ids),
    )

    if kept_rows == 0:
        log.error(
            "Dropping biotypes %s left no annotation rows in %s.",
            ",".join(sorted(drop_biotypes)), args.input,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
