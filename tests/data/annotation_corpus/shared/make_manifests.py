#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Generate cases/*/manifest.json from actual detector/filter behaviour.

Snapshot-style: locks current (correct) behaviour so the test suite catches
regressions, while known-bad cases are marked ``xfail`` so a fix turns them
into an xpass failure (an explicit "the bug is gone" alert).

Re-run after editing fixtures (see ``just annotation-fixtures`` / ``just
annotation-manifests``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus_lib as cl  # noqa: E402

# tier, description, class (euk/prok/None), aligner extra flags
META: dict[str, tuple[str, str, str | None, list[str]]] = {
    "E1_eukaryote_ensembl":      ("happy",      "Eukaryote, Ensembl-style GTF (gene_biotype)", "euk", []),
    "E2_eukaryote_gencode":      ("happy",      "Eukaryote, GENCODE-style GTF (gene_type)", "euk", []),
    "E3_eukaryote_refseq":       ("happy",      "Eukaryote, RefSeq GFF3 (gene/mRNA/exon/CDS hierarchy)", "euk", []),
    "E4_eukaryote_no_biotype":   ("happy",      "Eukaryote, exon GTF missing biotype -> skip_biotype_qc", "euk", []),
    "E5_eukaryote_ncrna_ids":    ("happy",      "Eukaryote, RefSeq GFF3 mixing protein-coding + tRNA/rRNA genes (NCBI ID=rna-*/gene-* convention)", "euk", []),
    "E6_eukaryote_ncrna_cds_only": ("happy",    "Eukaryote, RefSeq GFF3 with CDS-only protein-coding genes (no mRNA/exon) mixed with exon-bearing tRNA/rRNA - real mitochondrial genome shape", "euk", []),
    "E7_eukaryote_flat_pseudogene": ("happy",   "Eukaryote, RefSeq GFF3 with flat single/multi-exon pseudogenes (exon Parent= points directly at gene, no transcript row)", "euk", []),
    "P1_prokaryote_minimal_gtf": ("happy",      "Prokaryote, minimal CDS-only GTF (self-contained gene_id)", "prok", ["--skip_rsem"]),
    "P2_prokaryote_ncbi":        ("happy",      "Prokaryote, NCBI GenBank GFF3 (gene+CDS, gbkey/Dbxref/locus_tag)", "prok", ["--skip_rsem"]),
    "P3_prokaryote_bakta":       ("happy",      "Prokaryote, Bakta GFF3 (flat CDS, ID=locus_tag)", "prok", ["--skip_rsem"]),
    "P3gz_prokaryote_bakta_gz":  ("happy",      "Prokaryote, Bakta GFF3 gzip-compressed (tests auto-decompress)", "prok", ["--skip_rsem"]),
    "P4_prokaryote_prokka":      ("happy",      "Prokaryote, Prokka GFF3 (flat CDS, eC_number)", "prok", ["--skip_rsem"]),
    "F9_mixed_chromosomes":      ("happy",      "Multi-contig eukaryotic GTF (chr1 + chr2 genes)", "euk", []),
    "F1_flat_snapgene":          ("repairable", "SnapGene flat GFF3: no ID/Parent; filter stamps gene_id from Name", "prok", ["--skip_rsem"]),
    "F2_snapgene_variation":     ("repairable", "SnapGene GFF3 with a stray 'variation' feature row mixed in", "prok", ["--skip_rsem"]),
    "F6_embedded_fasta":         ("repairable", "Prokaryote GFF3 with a trailing ##FASTA section (must be skipped)", "prok", ["--skip_rsem"]),
    "F7_crlf_bom":               ("repairable", "Prokaryote GTF with UTF-8 BOM + CRLF line endings", "prok", ["--skip_rsem"]),
    "F3_seqid_mismatch":         ("failfast",   "Prokaryote GFF3 whose seqids share no overlap with the FASTA", "prok", []),
    "F5_eight_columns":          ("failfast",   "GFF3 with only 8-column rows (no attributes column)", None, []),
    "F10_empty":                 ("failfast",   "Empty annotation file", None, []),
    "F4_seqid_mismatch_partial": ("detect_only", "GFF3 with partial seqid overlap (some contigs match, some don't)", "prok", []),
    "F11_mixed_format":          ("detect_only", "Eukaryotic GTF with format edge (no biotype)", "euk", []),
    "F8_agat_converted":         ("xfail",      "AGAT-converted prok GFF3: synthetic mRNA/exon fools detector (doc §6.1)", "prok", []),
}

# Correct behaviour the detector SHOULD produce for the xfail case once fixed.
XFAIL_CORRECT_DETECT = {
    "exit": 0,
    "env": {
        "ANN_FORMAT": "gff3",
        "ANN_FEATURE_TYPE": "CDS",
        "ANN_PROKARYOTIC": "yes",
        "ANN_PROFILE": "generic_prokaryote",
        "ANN_BIOTYPE_ATTR": "",
    },
    "xfail_reason": (
        "doc ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6.1: AGAT-converted "
        "prokaryote GFF3 gains synthetic mRNA/exon rows, so _looks_prokaryotic "
        "returns False and the detector misclassifies it as generic_eukaryote. "
        "When the detector is fixed, this xpasses -> flip to a happy case."
    ),
}

PROK_SKIP_FULL = "--skip_dupradar --skip_rseqc --skip_qualimap --skip_bigwig --skip_biotype_qc"

# Cases whose detect/filter/seqid stages are all correct ("happy"), but whose
# real e2e run is a *known* failure downstream in nf-core/rnaseq itself (not
# in Laxy's own annotation pre-processing). Recorded here rather than folded
# into the generic "happy" path so `expected.e2e` stays a snapshot of actual
# behaviour, same as every other field build_manifest() writes.
#
# E5/E6 (non-coding RNA lacking transcript_id -> drop_biotype_features.py)
# are NOT here: verified end to end against real Laxy prod (genuine NCBI
# human/mouse mitochondrial jobs completed with real gene counts) - see
# ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7.
E2E_KNOWN_FAILURES: dict[str, str] = {
    "E7_eukaryote_flat_pseudogene": (
        "nf-core/rnaseq's own GFF3->GTF conversion (used to build the "
        "transcript FASTA via rsem-prepare-reference, regardless of "
        "--aligner choice) can't resolve gene_id for flat single/multi-exon "
        "pseudogenes whose exon rows point Parent= directly at the gene "
        "(no transcript/mRNA row) - dies with \"Cannot find gene_id!\", "
        "aborting the whole pipeline. Confirmed in both human (chr21, gene "
        "RPL8P2) and mouse (chr19, gene Gm36006) RefSeq annotations. A fix "
        "(insert_missing_transcript.py, wired into run_job.sh as the first "
        "normalisation step) synthesises the missing transcript wrapper - "
        "verified at the annotation-transformation level (this corpus's "
        "insert_transcript stage), but NOT yet re-verified against a real "
        "pipeline run pending redeploy. See "
        "ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 8."
    ),
}


def build_manifest(case_dir: Path) -> dict:
    name = case_dir.name
    tier, desc, klass, extra_flags = META[name]
    ann = cl.annotation_path(case_dir)
    assert ann is not None, f"no annotation.* in {case_dir}"

    det = cl.run_detect(ann)
    manifest: dict = {
        "id": name,
        "description": desc,
        "annotation": ann.name,
        "class": klass,
        "tier": tier,
        "xfail_reason": None,
        "expected": {},
    }

    # --- detect stage ---
    if tier == "xfail":
        manifest["expected"]["detect"] = XFAIL_CORRECT_DETECT
        manifest["xfail_reason"] = XFAIL_CORRECT_DETECT["xfail_reason"]
    elif det["rc"] == 0:
        manifest["expected"]["detect"] = {"exit": 0, "env": det["env"]}
    else:
        manifest["expected"]["detect"] = {
            "exit": det["rc"],
            "stderr_contains": det["stderr"].splitlines()[0] if det["stderr"] else "",
        }

    # --- insert-missing-transcript stage (real annotation.gff3/gtf, before
    # drop_biotype_features/filter_annotation_features - mirrors run_job.sh's
    # insert_missing_transcript bash function, which runs first) ---
    if det["rc"] == 0 and tier in {"happy", "repairable", "detect_only"}:
        env = det["env"]
        ins = cl.run_insert_transcript(ann, env["ANN_FORMAT"])
        manifest["expected"]["insert_transcript"] = {
            "exit": ins["rc"],
            "counts": ins["counts"],
        }
    else:
        manifest["expected"]["insert_transcript"] = None

    # --- filter stage (only when detect succeeds and tier exercises it) ---
    if det["rc"] == 0 and tier in {"happy", "repairable", "detect_only"}:
        env = det["env"]
        flt = cl.run_filter(
            ann, env["ANN_FORMAT"], env["ANN_FEATURE_TYPE"],
            env.get("ANN_GROUP_FEATURES", ""),
            env.get("ANN_PROKARYOTIC", "no"),
        )
        manifest["expected"]["filter"] = {
            "exit": 0,
            "counts": flt["counts"],
        }
    else:
        manifest["expected"]["filter"] = None

    # --- drop-biotype stage (real annotation.gff3/gtf, before any
    # prokaryotic-only synthesis by filter_annotation_features) ---
    if det["rc"] == 0 and tier in {"happy", "repairable", "detect_only"}:
        env = det["env"]
        drp = cl.run_drop_biotype(ann, env["ANN_FORMAT"], env.get("ANN_DROP_BIOTYPES", ""))
        manifest["expected"]["drop_biotype"] = {
            "exit": drp["rc"],
            "counts": drp["counts"],
        }
    else:
        manifest["expected"]["drop_biotype"] = None

    # --- post-drop re-detect + filter chain (mirrors run_job.sh's
    # drop_biotype_features calling detect_annotation_style.py a second time
    # on the stripped annotation, then filter_annotation_features using
    # that fresh env). Only meaningful when a drop would actually happen -
    # e.g. real mitochondrial RefSeq annotations have CDS-only protein-coding
    # genes, so stripping the exon-bearing tRNA/rRNA genes leaves zero exon
    # rows, and the pipeline must reclassify the remainder as CDS-only /
    # prokaryotic-shaped rather than handing STAR a GTF with no exon lines.
    if det["rc"] == 0 and det["env"].get("ANN_DROP_BIOTYPES"):
        chain = cl.run_post_drop_chain(ann, det["env"]["ANN_FORMAT"], det["env"]["ANN_DROP_BIOTYPES"])
        manifest["expected"]["post_drop"] = {
            "redetect_env": chain["redetect"]["env"] if chain["redetect"] else None,
            "filter_counts": chain["filter"]["counts"] if chain["filter"] else None,
        }
    else:
        manifest["expected"]["post_drop"] = None

    # --- seqid-overlap pre-flight (mirrors check_fasta_annotation_seqids) ---
    fa_ids, an_ids, overlap = cl.seqid_overlap(cl.GENOME, ann)
    manifest["expected"]["seqid"] = {
        "fasta_ids_sample": sorted(fa_ids)[:5],
        "ann_ids_sample": sorted(an_ids)[:5],
        # Snapshot of reality: the bash comm -12 overlap is non-empty iff the
        # pre-flight would pass. Empty annotations and mismatched seqids both
        # fail (empty ann_ids, or zero shared ids).
        "expect_overlap": bool(overlap),
    }

    # --- reads + e2e (only fast tiers) ---
    if tier in {"happy", "repairable"}:
        manifest["reads"] = {
            "mode": "paired",
            "count": 2000,
            "read_length": 75,
            "fragment_size": 200,
            "seed": 42,
        }
        known_failure = E2E_KNOWN_FAILURES.get(name)
        manifest["expected"]["e2e"] = {
            "run": True,
            "aligner": "star_salmon",
            "extra_flags": extra_flags,
            "expect_success": known_failure is None,
        }
        if known_failure is not None:
            manifest["expected"]["e2e"]["known_failure_reason"] = known_failure
    else:
        manifest["reads"] = None
        manifest["expected"]["e2e"] = {"run": False}

    return manifest


def main() -> None:
    for case_dir in cl.discover_cases():
        if case_dir.name not in META:
            print(f"  SKIP {case_dir.name}: not in META table")
            continue
        manifest = build_manifest(case_dir)
        (case_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=False) + "\n"
        )
        print(f"  wrote {case_dir.name}/manifest.json  tier={manifest['tier']}")


if __name__ == "__main__":
    main()
