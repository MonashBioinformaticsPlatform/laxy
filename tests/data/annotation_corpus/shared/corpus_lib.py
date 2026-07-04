"""Shared helpers for the annotation corpus (manifest generation + test runs).

Kept stdlib-only so the test harness and the manifest generator can import it
without a virtualenv. The detector/filter scripts are invoked as subprocesses
exactly as the pipeline invokes them, so the corpus exercises real behaviour.
"""

from __future__ import annotations

import ast
import gzip
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Resolve script paths relative to this file so imports work from anywhere.
_HERE = Path(__file__).resolve().parent
_CORPUS_ROOT = _HERE.parent
_SCRIPTS = (
    _CORPUS_ROOT.parents[2]
    / "laxy_pipeline_apps"
    / "nf-core-rnaseq"
    / "templates"
    / "common"
    / "input"
    / "scripts"
)
DETECT = _SCRIPTS / "detect_annotation_style.py"
FILTER = _SCRIPTS / "filter_annotation_features.py"
DROP_BIOTYPE = _SCRIPTS / "drop_biotype_features.py"
CASES = _CORPUS_ROOT / "cases"
SHARED = _HERE
GENOME = SHARED / "genome.fa"
GENOME_GZ = SHARED / "genome.fa.gz"
GEN_READS = SHARED / "generate_reads.py"


def is_gzipped(path: Path) -> bool:
    try:
        with path.open("rb") as fp:
            return fp.read(2) == b"\x1f\x8b"
    except OSError:
        return path.suffix == ".gz"


def open_text(path: Path):
    if is_gzipped(path):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def annotation_path(case_dir: Path) -> Optional[Path]:
    """The single annotation file inside a case dir (annotation.*)."""
    hits = sorted(case_dir.glob("annotation.*"))
    # Prefer non-sidecar: annotation.gtf / .gff3 / .gtf.gz / .gff3.gz
    hits = [h for h in hits if not h.name.endswith((".fai", ".bai"))]
    return hits[0] if hits else None


def parse_env(env_path: Path) -> dict[str, str]:
    """Parse a detector env file (KEY='value' lines) into a plain dict.

    Values are single-quoted in the file; we strip the quotes via ast.literal_eval
    so embedded quotes survive correctly.
    """
    out: dict[str, str] = {}
    if not env_path.is_file():
        return out
    for line in env_path.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if v and v[0] in "\"'" and v[-1] == v[0]:
            try:
                v = ast.literal_eval(v)
            except (SyntaxError, ValueError):
                v = v[1:-1]
        out[k.strip()] = v
    return out


# Canonical env keys emitted by detect_annotation_style.py (order-stable).
ENV_KEYS = (
    "ANN_FORMAT",
    "ANN_FEATURE_TYPE",
    "ANN_GROUP_FEATURES",
    "ANN_EXTRA_ATTRIBUTES",
    "ANN_BIOTYPE_ATTR",
    "ANN_PROKARYOTIC",
    "ANN_PROFILE",
    "ANN_SKIP_FLAGS",
)


def run_detect(ann: Path) -> dict:
    """Run detect_annotation_style.py on ``ann``; return rc/env/stderr."""
    proc = subprocess.run(
        [sys.executable, str(DETECT), str(ann), "-o", "/dev/stdout"],
        capture_output=True, text=True,
    )
    env: dict[str, str] = {}
    if proc.returncode == 0:
        env = parse_env_env_text(proc.stdout)
    return {"rc": proc.returncode, "env": env, "stderr": proc.stderr.strip()}


def parse_env_env_text(text: str) -> dict[str, str]:
    """Detector can write to /dev/stdout; parse those KEY='v' lines."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if v and v[0] in "\"'" and v[-1] == v[0]:
            try:
                v = ast.literal_eval(v)
            except (SyntaxError, ValueError):
                v = v[1:-1]
        out[k.strip()] = v
    return out


def run_filter(
    ann: Path, fmt: str, feature_type: str, group_feature: str = "",
    prokaryotic: str = "no",
) -> dict:
    """Run filter_annotation_features.py; return rc + parsed log counters."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".gtf", delete=False) as tf:
        out_path = Path(tf.name)
    proc = subprocess.run(
        [sys.executable, str(FILTER),
         "--input", str(ann),
         "--output", str(out_path),
         "--feature-type", feature_type,
         "--format", fmt,
         "--prokaryotic", prokaryotic,
         "--group-feature", group_feature],
        capture_output=True, text=True,
    )
    counts = {"input_rows_kept": 0, "output_rows": 0, "dropped": 0}
    for tok in ("input_rows_kept=", "output_rows=", "dropped="):
        pass
    log = proc.stderr + proc.stdout
    for key in counts:
        marker = key + "="
        i = log.find(marker)
        if i >= 0:
            tail = log[i + len(marker):]
            num = ""
            for ch in tail:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num:
                counts[key] = int(num)
    out_path.unlink(missing_ok=True)
    return {"rc": proc.returncode, "counts": counts, "stderr": proc.stderr.strip()}


def run_drop_biotype(ann: Path, fmt: str, drop_biotypes: str = "") -> dict:
    """Run drop_biotype_features.py; return rc + parsed log counters."""
    import tempfile
    suffix = ".gff3" if fmt == "gff3" else ".gtf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        out_path = Path(tf.name)
    proc = subprocess.run(
        [sys.executable, str(DROP_BIOTYPE),
         "--input", str(ann),
         "--output", str(out_path),
         "--format", fmt,
         "--drop-biotypes", drop_biotypes],
        capture_output=True, text=True,
    )
    counts = {"input_rows": 0, "kept_rows": 0, "dropped_rows": 0, "dropped_ids": 0}
    log = proc.stderr + proc.stdout
    for key in counts:
        marker = key + "="
        i = log.find(marker)
        if i >= 0:
            tail = log[i + len(marker):]
            num = ""
            for ch in tail:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num:
                counts[key] = int(num)
    out_path.unlink(missing_ok=True)
    return {"rc": proc.returncode, "counts": counts, "stderr": proc.stderr.strip()}


def fasta_seqids(fasta: Path) -> set[str]:
    """First whitespace token of every '>' header (mirrors check_fasta_annotation_seqids awk)."""
    ids: set[str] = set()
    with open_text(fasta) as fp:
        for line in fp:
            if line.startswith(">"):
                tok = line[1:].split()[0] if len(line) > 1 else ""
                if tok:
                    ids.add(tok)
    return ids


def annotation_seqids(ann: Path) -> set[str]:
    """Col-1 seqids of feature rows, skipping comments + ##FASTA section (mirrors the awk)."""
    ids: set[str] = set()
    in_fasta = False
    with open_text(ann) as fp:
        for line in fp:
            if line.startswith("##FASTA"):
                in_fasta = True
                continue
            if in_fasta or not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) >= 8 and parts[0].strip():
                ids.add(parts[0])
    return ids


def seqid_overlap(fasta: Path, ann: Path) -> tuple[set[str], set[str], set[str]]:
    """Return (fasta_ids, ann_ids, overlap) mirroring the bash comm -12 check."""
    fa = fasta_seqids(fasta)
    an = annotation_seqids(ann)
    return fa, an, fa & an


def generate_reads(case_dir: Path, manifest: dict) -> None:
    """Write cases/<id>/reads/<prefix>_R{1,2}.fastq.gz if missing."""
    reads = manifest.get("reads")
    if not reads:
        return
    ann = annotation_path(case_dir)
    assert ann is not None, case_dir
    reads_dir = case_dir / "reads"
    reads_dir.mkdir(exist_ok=True)
    prefix = reads_dir / "sample"
    r1 = Path(str(prefix) + "_R1.fastq.gz")
    if r1.is_file() and reads.get("count", 2000) > 0:
        return  # cached
    feature_type = manifest["expected"]["detect"].get(
        "feature_type", manifest["expected"]["detect"].get("env", {}).get("ANN_FEATURE_TYPE", "CDS")
    )
    cmd = [sys.executable, str(GEN_READS),
           "--genome", str(GENOME),
           "--annotation", str(ann),
           "--feature-type", feature_type,
           "-n", str(reads.get("count", 2000)),
           "-l", str(reads.get("read_length", 75)),
           "-f", str(reads.get("fragment_size", 200)),
           "--mode", reads.get("mode", "paired"),
           "--seed", str(reads.get("seed", 42)),
           "--out-prefix", str(prefix)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def load_manifest(case_dir: Path) -> dict:
    return json.loads((case_dir / "manifest.json").read_text())


def discover_cases() -> list[Path]:
    return sorted(d for d in CASES.iterdir() if d.is_dir())
