#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["requests"]
# ///
"""Run the annotation corpus e2e cases as real Laxy jobs via ``laxycli``.

For every case whose manifest enables ``expected.e2e.run`` this:
  1. builds CDN URLs for the shared genome, the case's annotation and reads
     (served from the committed corpus on a GitHub branch via jsDelivr),
  2. warms the CDN cache (jsDelivr is flaky under concurrent cold fetches),
  3. submits the job through ``laxycli job create --no-wait`` with a custom
     reference genome, staggering submissions, and
  4. polls every submitted job to completion and prints a pass/fail summary.

Env:
  LAXY_API_URL    API base (default https://dev-api.laxy.io:8001/api/v1)
  LAXY_API_TOKEN  JWT (or LAXY_API_KEY) - passed through to laxycli
  LAXY_CORPUS_BRANCH         git branch the corpus is committed on
  LAXY_CORPUS_FILE_BASE      override the whole file base URL
  LAXY_CORPUS_PIPELINE_VERSION  nf-core-rnaseq version (default 3.18.0)
  LAXY_CORPUS_STAGGER_S      seconds between submissions (default 90)

Usage:
  ./run_corpus_via_laxycli.py                 # all e2e cases
  ./run_corpus_via_laxycli.py P1_prokaryote_minimal_gtf F7_crlf_bom
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
LAXYCLI = HERE.parent.parent.parent / "laxycli" / "laxycli.py"

API = os.environ.get("LAXY_API_URL", "https://dev-api.laxy.io:8001/api/v1").rstrip("/")
BRANCH = os.environ.get("LAXY_CORPUS_BRANCH", "feature/auto-annotation-features2")
FILE_BASE = os.environ.get(
    "LAXY_CORPUS_FILE_BASE",
    f"https://cdn.jsdelivr.net/gh/MonashBioinformaticsPlatform/laxy@{BRANCH}"
    f"/tests/data/annotation_corpus",
)
PIPELINE_VERSION = os.environ.get("LAXY_CORPUS_PIPELINE_VERSION", "3.18.0")
STAGGER_S = int(os.environ.get("LAXY_CORPUS_STAGGER_S", "90"))

# Mirrors the proven-working corpus job params (and the web UI defaults).
NFCORE_PARAMS = {
    "nf-core-rnaseq": {
        "has_umi": False,
        "trimmer": "fastp",
        "debug_mode": False,
        "strandedness": "auto",
        "skip_trimming": False,
        "skip_alignment": False,
        "min_mapped_reads": 5,
        "save_genome_index": False,
        "save_reference_genome": True,
    }
}


def auth_headers() -> dict:
    token = os.environ.get("LAXY_API_TOKEN") or os.environ.get("LAXY_API_KEY")
    if not token:
        sys.exit("Set LAXY_API_TOKEN (or LAXY_API_KEY).")
    return {"Authorization": f"Bearer {token}"}


def e2e_cases(selected: list) -> list:
    """Return [(case_id, annotation_filename), ...] for e2e-enabled cases."""
    out = []
    for manifest_path in sorted((HERE / "cases").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        if not manifest["expected"].get("e2e", {}).get("run"):
            continue
        case_id = manifest["id"]
        if selected and case_id not in selected:
            continue
        case_dir = manifest_path.parent
        ann = next(p.name for p in case_dir.iterdir() if p.name.startswith("annotation."))
        out.append((case_id, ann))
    return out


def case_urls(case_id: str, ann_name: str) -> dict:
    return {
        "genome": f"{FILE_BASE}/shared/genome.fa",
        "annotation": f"{FILE_BASE}/cases/{case_id}/{ann_name}",
        "r1": f"{FILE_BASE}/cases/{case_id}/reads/sample_R1.fastq.gz",
        "r2": f"{FILE_BASE}/cases/{case_id}/reads/sample_R2.fastq.gz",
    }


def warm_cache(urls: list) -> None:
    """GET each URL so jsDelivr caches it before the compute node fetches."""
    for u in urls:
        try:
            requests.get(u, timeout=60).close()
        except requests.RequestException as e:
            print(f"  warn: cache warm failed for {u}: {e}")


def submit(case_id: str, ann_name: str) -> str:
    urls = case_urls(case_id, ann_name)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as uf:
        uf.write(urls["r1"] + "\n" + urls["r2"] + "\n")
        urls_file = uf.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as pf:
        json.dump(NFCORE_PARAMS, pf)
        params_file = pf.name

    cmd = [
        sys.executable, str(LAXYCLI), "job", "create",
        "--api_base_url", API,
        "--pipeline_name", "nf-core-rnaseq",
        "--pipeline_version", PIPELINE_VERSION,
        "--job_description", f"E2E test: {case_id}",
        "--genome_fasta_url", urls["genome"],
        "--genome_annotation_url", urls["annotation"],
        "--urls_file", urls_file,
        "--pipeline_params_json", f"@{params_file}",
        "--no-wait",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(urls_file)
    os.unlink(params_file)
    job_id = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if proc.returncode != 0 or not job_id:
        print(f"  [{case_id}] submit FAILED (rc={proc.returncode}): {proc.stderr[-400:]}")
        return ""
    return job_id


def poll_all(jobs: dict, timeout: int = 5400) -> dict:
    headers = auth_headers()
    last: dict = {}
    deadline = time.time() + timeout
    terminal = {"complete", "failed", "cancelled"}
    while time.time() < deadline:
        pending = [c for c in jobs if last.get(c) not in terminal]
        if not pending:
            break
        for case_id in pending:
            try:
                r = requests.get(f"{API}/job/{jobs[case_id]}/", headers=headers, timeout=30)
                st = r.json().get("status", "?")
            except requests.RequestException:
                continue
            if st != last.get(case_id):
                print(f"  [{time.strftime('%H:%M:%S')}] {case_id} ({jobs[case_id]}): {st}")
                last[case_id] = st
        time.sleep(30)
    return last


def main() -> None:
    selected = sys.argv[1:]
    cases = e2e_cases(selected)
    if not cases:
        sys.exit("No matching e2e cases.")
    print(f"=== {len(cases)} e2e cases -> {API} (branch {BRANCH}, stagger {STAGGER_S}s) ===")

    submitted: dict = {}
    for i, (case_id, ann_name) in enumerate(cases):
        urls = case_urls(case_id, ann_name)
        print(f"[{i+1}/{len(cases)}] {case_id}: warming cache + submitting ...")
        warm_cache(list(urls.values()))
        job_id = submit(case_id, ann_name)
        if job_id:
            submitted[case_id] = job_id
            print(f"  -> job {job_id}")
        if i < len(cases) - 1:
            time.sleep(STAGGER_S)

    print(f"\n=== {len(submitted)}/{len(cases)} submitted; polling to completion ===")
    results = poll_all(submitted)

    print("\n=== SUMMARY ===")
    n_pass = 0
    for case_id, _ in cases:
        job_id = submitted.get(case_id, "-")
        st = results.get(case_id, "not submitted")
        mark = "[OK]  " if st == "complete" else "[FAIL]"
        if st == "complete":
            n_pass += 1
        print(f"{mark} {case_id:<28} {st:<10} {job_id}")
    print(f"\n{n_pass}/{len(cases)} complete")
    sys.exit(0 if n_pass == len(cases) else 1)


if __name__ == "__main__":
    main()
