#!/usr/bin/env python3
"""Infer nf-core/rnaseq annotation flags from a GTF or GFF3 file.

Reads up to a capped number of feature lines, detects attribute conventions,
and emits a shell-sourceable env file for run_job.sh.

Uses Python 3.9+ standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import BinaryIO, Dict, Iterator, Literal, Optional, Set, Tuple, cast

MAX_FEATURE_LINES = 200_000

FormatKind = Literal["gtf", "gff3"]

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)


def open_maybe_gzip(path: Path) -> BinaryIO:
    """Open ``path`` for binary reading, decompressing if it really is gzipped.

    Trusts the file's magic bytes rather than its extension: many GFF/GTF files
    in the wild are named ``.gz`` but are actually plain text, and (less often)
    the reverse. We only fall back to the extension when we couldn't peek.
    """
    try:
        with path.open("rb") as fp:
            magic = fp.read(2)
    except OSError:
        magic = b""

    if magic == b"\x1f\x8b":
        return cast(BinaryIO, gzip.open(path, "rb"))

    if magic:
        return path.open("rb")

    if path.suffix == ".gz" or str(path).endswith(".gz"):
        return cast(BinaryIO, gzip.open(path, "rb"))
    return path.open("rb")


def iter_feature_lines(raw: BinaryIO) -> Iterator[str]:
    in_fasta = False
    for raw_line in raw:
        if len(raw_line) > 10 * 1024 * 1024:
            continue
        try:
            line = raw_line.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            line = raw_line.decode("latin-1", errors="replace")
        if in_fasta:
            continue
        if line.startswith("##FASTA"):
            in_fasta = True
            continue
        if line.startswith("#"):
            continue
        line = line.rstrip("\n\r")
        if not line.strip():
            continue
        yield line


def sniff_format(attr: str) -> Optional[FormatKind]:
    """Return gtf vs gff3 from the attributes column, or None if unclear."""
    s = attr.lstrip()
    # GFF3: starts with key=value
    if re.match(r'^\w[\w.:-]*=', s):
        return "gff3"
    # GTF: starts with key "value"
    if re.match(r'^\w[\w.:-]*\s+"', s):
        return "gtf"
    # Looser fallbacks
    if "=" in s and '"' not in s:
        return "gff3"
    if ';' in s and '"' in s:
        return "gtf"
    return None


def parse_gtf_attributes(attr: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    # Standard GTF: key "value"
    for m in re.finditer(r'([\w.:-]+)\s+"([^"]*)"', attr):
        out.setdefault(m.group(1), m.group(2))
    # Tolerant: also accept key="value" or key=value within the same column.
    for part in attr.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip()
        if k:
            out.setdefault(k, v)
    return out


def parse_gff3_attributes(attr: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in attr.strip().split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
            out.setdefault(key.strip(), val.strip().strip('"').strip())
    # Tolerant: also harvest GTF-style key "value" pairs.
    for m in re.finditer(r'([\w.:-]+)\s+"([^"]*)"', attr):
        out.setdefault(m.group(1), m.group(2))
    return out


def parse_attributes(attr: str, fmt: FormatKind) -> Dict[str, str]:
    if fmt == "gtf":
        return parse_gtf_attributes(attr)
    return parse_gff3_attributes(attr)


def first_present(keys: Set[str], candidates: Tuple[str, ...]) -> Optional[str]:
    for c in candidates:
        if c in keys:
            return c
    return None


_BIOTYPE_ATTR_CANDIDATES: Tuple[str, ...] = ("gene_biotype", "gene_type", "biotype")


def _biotype_value(attrs: Dict[str, str]) -> Optional[str]:
    for cand in _BIOTYPE_ATTR_CANDIDATES:
        v = attrs.get(cand)
        if v:
            return v
    return None


def scan_annotation(
    path: Path,
) -> Tuple[Dict[str, int], Dict[str, Set[str]], FormatKind, Set[str]]:
    ft_counts: Dict[str, int] = defaultdict(int)
    ft_keys: Dict[str, Set[str]] = defaultdict(set)
    biotype_values: Set[str] = set()

    fmt_resolved: Optional[FormatKind] = None
    n_lines = 0
    pending_attrs: list[Tuple[str, str]] = []

    def _record(ft: str, attrs: Dict[str, str]) -> None:
        ft_counts[ft] += 1
        ft_keys[ft].update(attrs.keys())
        bt = _biotype_value(attrs)
        if bt:
            biotype_values.add(bt)

    with open_maybe_gzip(path) as raw:
        for line in iter_feature_lines(raw):
            n_lines += 1
            if n_lines > MAX_FEATURE_LINES:
                break
            parts = line.split("\t")
            if len(parts) != 9:
                continue
            feature_type = parts[2]
            attr_col = parts[8]
            if fmt_resolved is None:
                fmt_resolved = sniff_format(attr_col)
                if fmt_resolved is None:
                    pending_attrs.append((feature_type, attr_col))
                    if len(pending_attrs) > 50:
                        raise ValueError(
                            "Could not detect GTF vs GFF3 from attributes column "
                            f"(first ambiguous line: {line[:200]!r}...)"
                        )
                    continue
                for ft, ac in pending_attrs:
                    _record(ft, parse_attributes(ac, fmt_resolved))
                pending_attrs = []
            _record(feature_type, parse_attributes(attr_col, fmt_resolved))

    if fmt_resolved is None:
        raise ValueError("No valid annotation feature rows found (empty file?)")

    return dict(ft_counts), {k: v for k, v in ft_keys.items()}, fmt_resolved, biotype_values


def build_extra_attributes(
    fmt: FormatKind, keys_on_features: Set[str], prokaryotic: bool = False
) -> str:
    """Comma-separated list for --gtf_extra_attributes / Salmon.

    For prokaryotic annotations, ``gene`` (the gene symbol in NCBI/Prokka/Bakta)
    is preferred over ``Name`` because on NCBI bacterial GFFs ``Name`` is
    often a protein accession rather than the gene symbol.
    """
    if prokaryotic:
        preferred = (
            "gene",
            "Name",
            "gene_name",
            "product",
            "protein_id",
            "locus_tag",
        )
    else:
        preferred = ("gene_name", "Name", "gene", "product", "protein_id")
    picked: list[str] = []
    for k in preferred:
        if k in keys_on_features and k not in picked:
            picked.append(k)
    return ",".join(picked)


def resolve_biotype_attr(keys_on_features: Set[str]) -> Optional[str]:
    for cand in ("gene_biotype", "gene_type", "biotype"):
        if cand in keys_on_features:
            return cand
    return None


# Feature-type priority. We pick the first feature in the list that has rows
# (and a usable grouping attribute). Eukaryotic data uses Ensembl-style `exon`
# at the top; prokaryotic-looking data flips this so `CDS` is preferred — this
# avoids being misled by the handful of tRNA/rRNA `exon` rows that show up in
# NCBI bacterial GFFs.
FEATURE_PRIORITY_EUK: Tuple[str, ...] = ("exon", "CDS", "gene", "transcript")
FEATURE_PRIORITY_PROK: Tuple[str, ...] = ("CDS", "gene", "exon", "transcript")

# Grouping-attribute priority, walked in order until one matches. Ordering
# follows the user-stated rule: Ensembl-style names first, `locus_tag` last.
# In practice for any well-formed annotation the first attribute we find is a
# reasonable choice for `--gtf_group_features` / featureCounts `-g`.
GROUP_ATTR_PRIORITY: Tuple[str, ...] = (
    "gene_id",       # Ensembl GTF canonical
    "geneID",        # case variant
    "GeneID",        # case variant
    "gene_name",     # Ensembl gene symbol (sometimes used as id)
    "Parent",        # GFF3 hierarchy: groups child rows by parent
    "Name",          # generic GFF3 name (gene symbol or accession)
    "gene",          # NCBI / Prokka / Bakta gene-symbol attribute
    "ID",            # GFF3 unique row id (last meaningful resort)
    "protein_id",    # NCBI protein accession
    "transcript_id", # GTF transcript id
    "locus_tag",     # bacterial canonical gene id (last resort)
)


def choose_counting_feature(
    ft_counts: Dict[str, int],
    ft_keys: Dict[str, Set[str]],
    is_prokaryotic: bool,
) -> str:
    """Walk feature priority and return the first one with rows and a usable group attr."""
    priority = FEATURE_PRIORITY_PROK if is_prokaryotic else FEATURE_PRIORITY_EUK

    for ft in priority:
        if ft_counts.get(ft, 0) > 0 and first_present(
            ft_keys.get(ft, set()), GROUP_ATTR_PRIORITY
        ):
            return ft

    # No feature has both rows and a usable grouping attribute. Pick whichever
    # has rows so choose_group_attr can raise a descriptive error listing the
    # actual attribute keys observed.
    for ft in priority:
        if ft_counts.get(ft, 0) > 0:
            return ft

    raise ValueError(
        "No supported feature types found "
        f"(expected one of {', '.join(priority)}; observed: {sorted(ft_counts)!r})"
    )


def choose_group_attr(feature_type: str, keys_on_ft: Set[str]) -> str:
    """Walk GROUP_ATTR_PRIORITY and return the first attribute present."""
    hit = first_present(keys_on_ft, GROUP_ATTR_PRIORITY)
    if hit:
        return hit
    raise ValueError(
        f"{feature_type} features lack any usable grouping attribute "
        f"({', '.join(GROUP_ATTR_PRIORITY)}); observed: {sorted(keys_on_ft)!r}"
    )


def _looks_prokaryotic(
    ft_counts: Dict[str, int], ft_keys: Dict[str, Set[str]]
) -> bool:
    """Heuristic for prokaryotic annotations.

    Prokaryotic GFFs typically have many CDS, no mRNA/transcript features,
    and either no exons or just a handful (tRNA/rRNA exons).
    """
    cds_n = ft_counts.get("CDS", 0)
    exon_n = ft_counts.get("exon", 0)
    mrna_n = ft_counts.get("mRNA", 0) + ft_counts.get("transcript", 0)
    if cds_n == 0:
        return False
    if mrna_n > 0:
        return False
    if exon_n == 0:
        return True
    if exon_n < max(cds_n // 5, 10):
        return True
    return False


def classify_profile(
    ft_counts: Dict[str, int],
    ft_keys: Dict[str, Set[str]],
    fmt: FormatKind,
    feature_type: str,
    keys_on_ft: Set[str],
) -> str:
    exon_n = ft_counts.get("exon", 0)
    cds_n = ft_counts.get("CDS", 0)
    all_keys: Set[str] = set()
    for s in ft_keys.values():
        all_keys |= s

    if fmt == "gff3" and exon_n > 10 and (
        ft_counts.get("mRNA", 0) + ft_counts.get("transcript", 0) > 0
    ):
        if "gene_biotype" in ft_keys.get("gene", set()) | ft_keys.get("exon", set()):
            return "refseq_gff3"

    if fmt == "gtf" and exon_n > 10:
        if "gene_biotype" in keys_on_ft or "gene_biotype" in ft_keys.get(
            "gene", set()
        ):
            return "refseq_gtf"

    if _looks_prokaryotic(ft_counts, ft_keys):
        if "Dbxref" in all_keys or "db_xref" in all_keys:
            # Bakta and NCBI both use Dbxref. Distinguish by Bakta-specific markers.
            cds_keys_all = ft_keys.get("CDS", set())
            if (
                "RefSeq" in cds_keys_all
                or any(k.startswith("So:") for k in cds_keys_all)
                or "EC_number" in cds_keys_all
            ):
                return "bakta"
            if "gbkey" in all_keys:
                return "ncbi_genbank"
            if "inference" in all_keys and "locus_tag" in (
                keys_on_ft | ft_keys.get("gene", set())
            ):
                return "prokka"
            return "ncbi_genbank"
        if "inference" in all_keys and "locus_tag" in (
            keys_on_ft | ft_keys.get("gene", set())
        ):
            return "prokka"
        if "gbkey" in all_keys:
            return "ncbi_genbank"
        return "generic_prokaryote"

    if feature_type == "CDS" and cds_n > 0 and exon_n > 0:
        if "Dbxref" in all_keys or "db_xref" in all_keys:
            return "bakta"
        if "inference" in all_keys and "locus_tag" in keys_on_ft:
            return "prokka"

    if feature_type == "CDS" and cds_n > 0:
        return "generic_prokaryote"

    if exon_n > 0 and resolve_biotype_attr(keys_on_ft):
        return "ensembl"

    return "generic_eukaryote"


# Non-coding RNA gene_biotype values that real annotations (NCBI RefSeq in
# particular) commonly tag with an ID like ``rna-<NAME>`` and no
# transcript_id-equivalent attribute. Salmon (via --aligner star_salmon's
# internal QUANTIFY_STAR_SALMON, and via --pseudo_aligner salmon - both are
# the *same* nf-core/rnaseq subworkflow) quantifies a transcript for every
# --gtf_group_features=Parent group regardless of biotype, but nf-core's
# tximport/SummarizedExperiment step then can't find a metadata column
# containing those ids and the whole run dies. See
# ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7.
NONCODING_RNA_BIOTYPES: frozenset[str] = frozenset((
    "tRNA", "rRNA", "ncRNA", "misc_RNA", "snRNA", "snoRNA", "scRNA",
    "guide_RNA", "RNase_P_RNA", "RNase_MRP_RNA", "SRP_RNA", "vault_RNA",
    "Y_RNA", "antisense_RNA", "telomerase_RNA", "ribozyme",
))


def decide(
    path: Path,
) -> Tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
]:
    ft_counts, ft_keys, fmt, biotype_values = scan_annotation(path)

    is_prokaryotic_hint = _looks_prokaryotic(ft_counts, ft_keys)
    feature_type = choose_counting_feature(ft_counts, ft_keys, is_prokaryotic_hint)
    keys_on_ft = ft_keys.get(feature_type, set())

    profile = classify_profile(ft_counts, ft_keys, fmt, feature_type, keys_on_ft)
    group_attr = choose_group_attr(feature_type, keys_on_ft)

    biotype_attr = resolve_biotype_attr(keys_on_ft)
    if biotype_attr is None and feature_type == "exon":
        gene_keys = ft_keys.get("gene", set())
        biotype_attr = resolve_biotype_attr(gene_keys)

    prokaryotic_profiles = {"prokka", "bakta", "ncbi_genbank", "generic_prokaryote"}
    is_prokaryotic = profile in prokaryotic_profiles

    extras = build_extra_attributes(fmt, keys_on_ft, prokaryotic=is_prokaryotic)

    def _drop_group(s: str) -> str:
        if not s:
            return ""
        items = [p.strip() for p in s.split(",") if p.strip()]
        return ",".join(p for p in items if p != group_attr)

    extras = _drop_group(extras)

    skip_flags: list[str] = []
    prokaryotic = "yes" if is_prokaryotic else "no"
    cds_only = feature_type == "CDS" and ft_counts.get("exon", 0) == 0

    if is_prokaryotic:
        skip_flags.append("--skip_dupradar")

    if cds_only:
        skip_flags.extend(
            [
                "--skip_rseqc",
                "--skip_qualimap",
                "--skip_bigwig",
                "--skip_dupradar",
            ]
        )

    if profile == "ensembl":
        if biotype_attr and "gene_name" in keys_on_ft:
            extras = "gene_name,gene_id"

    elif profile == "refseq_gtf":
        if "gene_name" not in keys_on_ft and "gene" in keys_on_ft:
            extras = "gene,gene_id"
        elif "gene_name" in keys_on_ft:
            extras = "gene_name,gene_id"

    elif profile == "refseq_gff3":
        extras = "Name,gene_id,gene"
        # Only set biotype if it's actually on the feature type we count.
        if biotype_attr is None and feature_type == "exon":
            gene_keys = ft_keys.get("gene", set())
            biotype_attr = resolve_biotype_attr(gene_keys | keys_on_ft)

    elif profile == "ncbi_genbank":
        # Bacterial GenBank-source GFFs typically have gene= (symbol),
        # Name= (often protein accession) and product= on CDS rows.
        prok_pref = ("gene", "Name", "product", "protein_id", "locus_tag")
        prok_picked: list[str] = []
        merged_keys = keys_on_ft | ft_keys.get("gene", set())
        for k in prok_pref:
            if k in merged_keys and k not in prok_picked:
                prok_picked.append(k)
        if prok_picked:
            extras = ",".join(prok_picked)

    extras = _drop_group(extras)

    # featureCounts can only see biotype on the feature type it counts. If the
    # attribute lives on parent rows (e.g. gene rows when we count CDS), skip
    # the biotype QC plot to avoid empty/misleading output.
    if biotype_attr is None:
        skip_flags.append("--skip_biotype_qc")

    skip_unique = []
    seen = set()
    for f in skip_flags:
        if f not in seen:
            seen.add(f)
            skip_unique.append(f)

    skip_str = " ".join(skip_unique)

    biotype_out = biotype_attr if biotype_attr else ""

    # Only drop non-coding RNA biotypes when there's a real protein-coding
    # (or other non-flagged) fallback to quantify - if the whole annotation
    # is e.g. tRNA/rRNA genes there's nothing else to align against anyway,
    # so leave it alone and let it fail as it does today.
    noncoding_present = sorted(biotype_values & NONCODING_RNA_BIOTYPES)
    other_biotypes_present = bool(biotype_values - NONCODING_RNA_BIOTYPES)
    drop_biotypes = ",".join(noncoding_present) if (noncoding_present and other_biotypes_present) else ""

    return (
        fmt,
        feature_type,
        group_attr,
        extras,
        biotype_out,
        prokaryotic,
        profile,
        skip_str,
        drop_biotypes,
    )


def shell_quote_single(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def emit_env(
    fp,
    fmt: str,
    feature_type: str,
    group_attr: str,
    extras: str,
    biotype: str,
    prokaryotic: str,
    profile: str,
    skip_flags: str,
    drop_biotypes: str,
) -> None:
    fp.write(f"ANN_FORMAT={shell_quote_single(fmt)}\n")
    fp.write(f"ANN_FEATURE_TYPE={shell_quote_single(feature_type)}\n")
    fp.write(f"ANN_GROUP_FEATURES={shell_quote_single(group_attr)}\n")
    fp.write(f"ANN_EXTRA_ATTRIBUTES={shell_quote_single(extras)}\n")
    fp.write(f"ANN_BIOTYPE_ATTR={shell_quote_single(biotype)}\n")
    fp.write(f"ANN_PROKARYOTIC={shell_quote_single(prokaryotic)}\n")
    fp.write(f"ANN_PROFILE={shell_quote_single(profile)}\n")
    fp.write(f"ANN_SKIP_FLAGS={shell_quote_single(skip_flags)}\n")
    fp.write(f"ANN_DROP_BIOTYPES={shell_quote_single(drop_biotypes)}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect annotation style for nf-core/rnaseq (emit shell env)."
    )
    parser.add_argument(
        "annotation",
        type=Path,
        help="Path to GTF/GFF/GFF3 (plain or .gz)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write env file here (default: stdout)",
    )
    args = parser.parse_args()

    path = args.annotation
    if not path.is_file():
        log.error("Annotation path does not exist or is not a file: %s", path)
        return 1

    try:
        (
            fmt,
            feature_type,
            group_attr,
            extras,
            biotype_out,
            prokaryotic,
            profile,
            skip_str,
            drop_biotypes,
        ) = decide(path)
    except ValueError as e:
        log.error("%s", e)
        return 1

    summary = (
        f"annotation_style: profile={profile} format={fmt} "
        f"feature={feature_type} group_by={group_attr} extras={extras!r} "
        f"biotype_attr={biotype_out!r} prokaryotic={prokaryotic} skip={skip_str!r} "
        f"drop_biotypes={drop_biotypes!r}"
    )
    log.info("%s", summary)

    out_fp = args.output.open("w", encoding="utf-8") if args.output else sys.stdout
    try:
        emit_env(
            out_fp,
            fmt,
            feature_type,
            group_attr,
            extras,
            biotype_out,
            prokaryotic,
            profile,
            skip_str,
            drop_biotypes,
        )
    finally:
        if args.output:
            out_fp.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
