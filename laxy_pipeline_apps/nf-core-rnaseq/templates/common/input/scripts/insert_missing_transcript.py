#!/usr/bin/env python3
"""Insert a missing transcript-level row for GFF3 genes whose children
(exon/CDS/...) point ``Parent=`` directly at the gene, skipping the usual
mRNA/tRNA/rRNA/ncRNA transcript level.

Real NCBI RefSeq annotations do this for single-exon "processed
pseudogenes" (no introns, so no felt need for an explicit transcript row),
e.g.::

    gene    263349  263882  ID=gene-RPL8P2;gene_biotype=pseudogene
    exon    263349  263882  ID=id-RPL8P2;Parent=gene-RPL8P2

Downstream tools expect a well-formed gene -> transcript -> exon/CDS
hierarchy: nf-core/rnaseq's own GFF3->GTF conversion (used to build the
transcript FASTA via ``rsem-prepare-reference`` regardless of aligner
choice) synthesises ``transcript_id`` from the immediate Parent but then
fails to resolve ``gene_id`` for these flat rows, dying with "Cannot find
gene_id!" and aborting the whole run. Confirmed against real Laxy prod
with genuine NCBI human (chr21, gene RPL8P2) and mouse (chr19, gene
Gm36006) RefSeq annotations.

For each gene with such flat children, this inserts one synthetic
transcript row (spanning all of that gene's flat children) and repoints
those children's Parent at it - a well-formed hierarchy nf-core/rnaseq
(and our own filter_annotation_features.py / drop_biotype_features.py)
already know how to handle.

GTF input isn't affected: GTF rows carry gene_id/transcript_id directly
per row (no Parent= hierarchy to walk), so this is a GFF3-only concern.

Uses Python 3.9+ standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import sys
from pathlib import Path
from typing import IO, Dict, List, Tuple, cast

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

# Only these are ever expected to sit directly under a transcript-level row.
# Everything else (mRNA, tRNA, rRNA, ncRNA, transcript, miRNA, snoRNA, ...)
# is itself a valid transcript unit, and its own Parent=<gene> is normal.
_LEAF_FEATURE_TYPES: frozenset[str] = frozenset((
    "exon", "CDS", "five_prime_UTR", "three_prime_UTR",
    "start_codon", "stop_codon",
))


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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True,
                   help="Input annotation (GTF or GFF3, plain or .gz).")
    p.add_argument("--output", type=Path, required=True,
                   help="Output path (same format as input).")
    p.add_argument("--format", required=True, choices=("gtf", "gff3"),
                   help="Matches detect_annotation_style.py ANN_FORMAT.")
    args = p.parse_args()

    if not args.input.is_file():
        log.error("Input does not exist or is not a file: %s", args.input)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.format != "gff3":
        log.info("insert_missing_transcript: format=%s, nothing to do (GTF has no Parent= hierarchy)", args.format)
        with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
            for line in fin:
                fout.write(line)
        return 0

    # Pass 1: find gene IDs and every row whose Parent points directly at one.
    gene_ids: set = set()
    rows: List[Tuple[int, List[str], Dict[str, str]]] = []
    with open_text_read(args.input) as fin:
        in_fasta = False
        for i, raw in enumerate(fin):
            if raw.startswith("##FASTA"):
                in_fasta = True
            if in_fasta or raw.startswith("#") or not raw.strip():
                rows.append((i, [raw], {}))
                continue
            parts = raw.rstrip("\r\n").split("\t")
            if len(parts) != 9:
                rows.append((i, parts if len(parts) == 9 else [raw], {}))
                continue
            attrs = parse_gff3_attrs(parts[8])
            rows.append((i, parts, attrs))
            # Top-level gene-ish rows never carry their own Parent=, and NCBI
            # uses several column-3 types for them (gene, pseudogene, ...).
            if attrs.get("ID") and not attrs.get("Parent") and parts[2] != "region":
                gene_ids.add(attrs["ID"])

    flat_children_by_gene: Dict[str, List[int]] = {}
    for idx, parts, attrs in rows:
        if not attrs or len(parts) != 9:
            continue
        # Only true leaf features (exon/CDS/UTRs/codons) are ever expected
        # to sit directly under a transcript-level row. Anything else
        # (mRNA, tRNA, rRNA, ncRNA, transcript, miRNA, snoRNA, ...) is
        # itself a valid transcript unit, and its Parent=<gene> is normal.
        if parts[2] not in _LEAF_FEATURE_TYPES:
            continue
        parent = attrs.get("Parent", "")
        parents = [p.strip() for p in parent.split(",") if p.strip()]
        if len(parents) == 1 and parents[0] in gene_ids:
            flat_children_by_gene.setdefault(parents[0], []).append(idx)

    if not flat_children_by_gene:
        log.info("insert_missing_transcript: no flat gene->feature rows found, passing through unchanged")
        with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
            for line in fin:
                fout.write(line)
        return 0

    existing_ids = {attrs["ID"] for _, _, attrs in rows if attrs.get("ID")}

    def synth_id(gene_id: str) -> str:
        base = f"rna-{gene_id[5:]}" if gene_id.startswith("gene-") else f"rna-{gene_id}"
        candidate = base
        suffix = 1
        while candidate in existing_ids:
            suffix += 1
            candidate = f"{base}_{suffix}"
        existing_ids.add(candidate)
        return candidate

    # For each affected gene, build the synthetic transcript row (spanning
    # all of its flat children) and remember the repointed Parent.
    synthetic_by_first_child_idx: Dict[int, List[str]] = {}
    repoint: Dict[int, str] = {}
    for gene_id, child_idxs in flat_children_by_gene.items():
        gene_row = next(parts for i, parts, attrs in rows if attrs.get("ID") == gene_id)
        seqid, source, _, _, _, score, strand, _, _ = gene_row
        starts = []
        ends = []
        for idx in child_idxs:
            child_parts = rows[idx][1]
            starts.append(int(child_parts[3]))
            ends.append(int(child_parts[4]))
        new_id = synth_id(gene_id)
        new_row = [
            seqid, source, "transcript", str(min(starts)), str(max(ends)),
            score, strand, ".", f"ID={new_id};Parent={gene_id}",
        ]
        first_idx = min(child_idxs)
        synthetic_by_first_child_idx[first_idx] = new_row
        for idx in child_idxs:
            repoint[idx] = new_id

    output_lines = 0
    genes_fixed = len(flat_children_by_gene)
    with open_text_write(args.output) as fout:
        for i, parts, attrs in rows:
            if i in synthetic_by_first_child_idx:
                fout.write("\t".join(synthetic_by_first_child_idx[i]) + "\n")
                output_lines += 1
            if not attrs or len(parts) != 9:
                fout.write(parts[0] if len(parts) == 1 else "\t".join(parts) + "\n")
                output_lines += 1
                continue
            if i in repoint:
                new_attrs = f"ID={attrs['ID']};Parent={repoint[i]}" if attrs.get("ID") else f"Parent={repoint[i]}"
                extra = ";".join(
                    f"{k}={v}" for k, v in attrs.items() if k not in ("ID", "Parent")
                )
                if extra:
                    new_attrs += ";" + extra
                parts = parts[:8] + [new_attrs]
            fout.write("\t".join(parts) + "\n")
            output_lines += 1

    log.info(
        "insert_missing_transcript: genes_fixed=%d synthetic_rows=%d output_rows=%d",
        genes_fixed, len(synthetic_by_first_child_idx), output_lines,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
