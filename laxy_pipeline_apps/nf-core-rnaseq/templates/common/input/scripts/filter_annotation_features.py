#!/usr/bin/env python3
"""Trim a prokaryotic annotation to a single feature type and expand each
kept row into a small ``transcript`` / ``exon`` / ``<feature_type>`` hierarchy
in GTF format so the downstream nf-core/rnaseq tools (``gffread``, RSEM,
STAR, featureCounts, ``CUSTOM_TX2GENE``, ``gtf2bed``) all see a well-formed,
eukaryotic-shaped annotation regardless of how flat the original input was.

Why GTF output even when the input is GFF3?
    nf-core/rnaseq's ``PREPARE_GENOME`` only runs ``gffread`` when given
    ``--gff``. ``gffread`` synthesises an implicit ``transcript`` row per
    flat ``CDS`` but does NOT add ``exon`` rows nor propagate ``gene_id``
    onto child features, which breaks RSEM (``rsem-prepare-reference``)
    and ``featureCounts`` with ``-g gene_id``. Writing a hierarchical GTF
    here lets us pass ``--gtf`` instead and skip the lossy ``gffread``
    conversion entirely.

For ``--format gtf`` we just filter rows by feature type and pass them
through unchanged - the assumption is that the GTF already has
self-contained ``gene_id``/``transcript_id`` on every row (Ensembl, GENCODE,
RefSeq, etc.).

The filter is intended for prokaryotic / CDS-only inputs only; the bash
caller (``filter_annotation_features`` in ``agat_normalize_annotation.sh``)
gates it on ``ANN_PROKARYOTIC=yes`` because rewriting eukaryotic GFF3 like
this would clobber the multi-exon ``Parent=`` grouping RSEM/gffread rely on.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import re
import sys
from pathlib import Path
from typing import IO, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

# Very large attribute values that we don't want to copy into every output
# row (some SnapGene/NCBI GFF3 exports embed the full protein translation,
# which would inflate the GTF size by orders of magnitude).
_BIG_ATTRS = frozenset((
    "translation", "Translation",
    "sequence", "Sequence",
    "seq", "Seq",
))

# Attributes already represented by the synthesised gene_id/transcript_id/
# gene_name/gene_biotype columns, so skip them when emitting "extra"
# attributes on the transcript row.
_ATTRS_HANDLED = frozenset((
    "ID", "Parent", "gene", "Name",
    "gene_name", "gene_id", "transcript_id",
    "gene_biotype", "biotype",
))


def is_gzipped(path: Path) -> bool:
    try:
        with path.open("rb") as fp:
            return fp.read(2) == b"\x1f\x8b"
    except OSError:
        return path.suffix == ".gz"


def open_text_read(path: Path) -> IO[str]:
    if is_gzipped(path):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def open_text_write(path: Path) -> IO[str]:
    if path.suffix == ".gz" or str(path).endswith(".gz"):
        return gzip.open(path, "wt", encoding="utf-8")
    return open(path, "wt", encoding="utf-8")


def parse_gff3_attrs(col9: str) -> Dict[str, str]:
    """Parse a GFF3 column-9 string into a key->value dict (first wins)."""
    out: Dict[str, str] = {}
    for part in col9.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        v = v.strip()
        if k and k not in out:
            out[k] = v
    return out


_GTF_ESCAPE_RE = re.compile(r'(["\\])')


def gtf_quote(value: str) -> str:
    """Escape backslashes and double-quotes in a value for GTF attribute output."""
    return _GTF_ESCAPE_RE.sub(r"\\\1", value)


def build_gtf_attrs(pairs: List[Tuple[str, str]]) -> str:
    """Build a GTF column-9 string from ordered (key, value) pairs."""
    parts: List[str] = []
    for k, v in pairs:
        if v is None or v == "":
            continue
        parts.append(f'{k} "{gtf_quote(v)}"')
    if not parts:
        return ""
    return "; ".join(parts) + ";"


def pick_base_id(
    attrs: Dict[str, str],
    group_feature: str,
    fallback_prefix: str,
    auto_counter: List[int],
) -> Tuple[str, str]:
    """Choose a base ID for a row.

    Returns a (base_id, source) tuple where ``source`` is one of
    ``"id"``, ``"group"``, or ``"auto"``.
    """
    existing = attrs.get("ID")
    if existing:
        return existing, "id"
    if group_feature:
        candidate = attrs.get(group_feature)
        if candidate:
            return candidate, "group"
    auto_counter[0] += 1
    return f"{fallback_prefix}-{auto_counter[0]}", "auto"


def dedupe(base_id: str, assigned: set, counter_hits: List[int]) -> str:
    """Return a unique id derived from ``base_id``, suffixing _2/_3/... if needed."""
    candidate = base_id
    suffix = 1
    while candidate in assigned:
        suffix += 1
        candidate = f"{base_id}_{suffix}"
    if candidate != base_id:
        counter_hits[0] += 1
    assigned.add(candidate)
    return candidate


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True,
                   help="Input annotation (GTF or GFF3, plain or .gz).")
    p.add_argument("--output", type=Path, required=True,
                   help="Output path. For GFF3 input the output is GTF and "
                        "should typically end in .gtf or .gtf.gz.")
    p.add_argument("--feature-type", required=True,
                   help="Value to match in column 3 (e.g. CDS, exon).")
    p.add_argument("--format", required=True, choices=("gtf", "gff3"),
                   help="Input format (matches detect_annotation_style.py ANN_FORMAT).")
    p.add_argument("--group-feature", default="",
                   help="Attribute used to derive ID/gene_id when the row "
                        "has no ID= (e.g. 'gene', 'locus_tag').")
    p.add_argument("--biotype", default="protein_coding",
                   help="Default gene_biotype for synthesised rows.")
    p.add_argument("--source-tag", default="laxy_filter",
                   help="Fallback value for column 2 of synthesised GTF rows "
                        "when the input row has an empty source column.")
    args = p.parse_args()

    if not args.input.is_file():
        log.error("Input does not exist or is not a file: %s", args.input)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    is_gff_in = args.format == "gff3"
    feature_type = args.feature_type
    feature_type_lc = feature_type.lower()

    input_rows_kept = 0
    output_rows_written = 0
    dropped = 0
    in_fasta = False
    ids_kept_existing = 0
    ids_stamped_from_group = 0
    auto_counter = [0]
    dupe_counter = [0]
    assigned_ids: set = set()

    with open_text_read(args.input) as fin, open_text_write(args.output) as fout:
        for raw in fin:
            if in_fasta:
                # FASTA section: only keep for GTF passthrough; drop for
                # synthesised-GTF output (RSEM/featureCounts don't want it).
                if not is_gff_in:
                    fout.write(raw)
                continue
            if raw.startswith("##FASTA"):
                in_fasta = True
                continue
            if raw.startswith("#"):
                # Pass comments through for GTF input; drop them for the
                # synthesised GTF (cleaner, and avoids leaking GFF3 directives
                # like ##gff-version 3 into a GTF file).
                if not is_gff_in:
                    fout.write(raw)
                continue
            if not raw.strip():
                continue

            row = raw.rstrip("\r\n")
            parts = row.split("\t")
            if len(parts) != 9:
                dropped += 1
                continue
            if parts[2] != feature_type:
                dropped += 1
                continue

            if not is_gff_in:
                fout.write("\t".join(parts) + "\n")
                input_rows_kept += 1
                output_rows_written += 1
                continue

            attrs = parse_gff3_attrs(parts[8])
            base_id, source = pick_base_id(
                attrs, args.group_feature, feature_type_lc, auto_counter
            )
            if source == "id":
                ids_kept_existing += 1
            elif source == "group":
                ids_stamped_from_group += 1

            uid = dedupe(base_id, assigned_ids, dupe_counter)
            gene_id = uid
            tx_id = uid
            gene_name = (
                attrs.get("gene")
                or attrs.get("Name")
                or attrs.get("gene_name")
                or uid
            )
            biotype = (
                attrs.get("gene_biotype")
                or attrs.get("biotype")
                or args.biotype
            )

            extras: List[Tuple[str, str]] = []
            for k, v in attrs.items():
                if k in _ATTRS_HANDLED or k in _BIG_ATTRS:
                    continue
                extras.append((k, v))

            seqid = parts[0]
            src = parts[1] or args.source_tag
            start = parts[3]
            end = parts[4]
            score = parts[5]
            strand = parts[6]
            frame = parts[7]

            core_pairs: List[Tuple[str, str]] = [
                ("gene_id", gene_id),
                ("transcript_id", tx_id),
                ("gene_name", gene_name),
                ("gene_biotype", biotype),
            ]

            tx_pairs = core_pairs + extras
            fout.write("\t".join([
                seqid, src, "transcript", start, end, score, strand, ".",
                build_gtf_attrs(tx_pairs),
            ]) + "\n")
            output_rows_written += 1

            exon_pairs = core_pairs + [("exon_number", "1")]
            fout.write("\t".join([
                seqid, src, "exon", start, end, score, strand, ".",
                build_gtf_attrs(exon_pairs),
            ]) + "\n")
            output_rows_written += 1

            # The original feature type (typically CDS) - skipped if the user
            # already filtered to ``exon`` since we just wrote one above.
            if feature_type_lc != "exon":
                fout.write("\t".join([
                    seqid, src, feature_type, start, end, score, strand, frame,
                    build_gtf_attrs(core_pairs),
                ]) + "\n")
                output_rows_written += 1

            input_rows_kept += 1

    log.info(
        "annotation_filter: feature_type=%s input_format=%s "
        "input_rows_kept=%d output_rows=%d dropped=%d "
        "ids_kept=%d ids_from_%s=%d ids_synthesised=%d duplicates_suffixed=%d",
        feature_type, args.format,
        input_rows_kept, output_rows_written, dropped,
        ids_kept_existing,
        args.group_feature or "group_feature",
        ids_stamped_from_group,
        auto_counter[0],
        dupe_counter[0],
    )

    if input_rows_kept == 0:
        log.error(
            "After filtering to feature_type='%s', no rows remain in %s.",
            feature_type, args.input,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
