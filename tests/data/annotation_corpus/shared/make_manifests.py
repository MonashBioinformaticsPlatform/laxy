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
E2E_KNOWN_FAILURES: dict[str, str] = {
    "E5_eukaryote_ncrna_ids": (
        "nf-core/rnaseq QUANTIFY_PSEUDO_ALIGNMENT:SE_* (aliased as "
        "QUANTIFY_STAR_SALMON for --aligner star_salmon too - same "
        "subworkflow) fails with \"No column contains all vector entries "
        "...\" - Salmon quantifies a transcript for every "
        "--gtf_group_features=Parent group (including tRNA/rRNA), but the "
        "tximport/SummarizedExperiment metadata table has no column "
        "containing those non-coding RNA ids. Confirmed against real Laxy "
        "prod with genuine NCBI human (NC_012920.1) and mouse (NC_005089.1) "
        "mitochondrial RefSeq annotations. A fix (drop_biotype_features.py, "
        "wired into run_job.sh via ANN_DROP_BIOTYPES) now strips these gene "
        "groups before nf-core/rnaseq sees them - verified at the "
        "annotation-transformation level (this corpus's drop_biotype stage), "
        "but NOT yet re-verified against a real pipeline run: the fix lives "
        "in laxy_pipeline_apps templates and only takes effect once rebuilt "
        "into the laxy Docker image and redeployed. Leaving expect_success "
        "false until that redeploy + a real e2e rerun confirms it. See "
        "ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7."
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
