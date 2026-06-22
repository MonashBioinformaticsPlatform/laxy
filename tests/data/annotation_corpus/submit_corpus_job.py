#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Submit annotation-corpus cases as real Laxy jobs on a remote server.

Reads from the raw-GitHub branch (feature/auto-annotation-features2) so no
upload is needed. Default mode submits as HOLD first (no compute) so the params
can be inspected; use --start to release a held job, or --run to submit+launch.

Env: LAXY_API_KEY_DEV (JWT), optional LAXY_API_BASE_URL (default dev.laxy.io:8001).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API = os.environ.get("LAXY_API_BASE_URL", "https://dev.laxy.io:8001").rstrip("/")
BRANCH = "feature/auto-annotation-features2"
# File host: jsDelivr CDN mirrors GitHub content and is often reachable from
# locked-down HPC nodes where raw.githubusercontent.com is blocked. Override
# with LAXY_CORPUS_FILE_BASE to use raw.githubusercontent.com or another host.
GH_RAW = os.environ.get(
    "LAXY_CORPUS_FILE_BASE",
    f"https://cdn.jsdelivr.net/gh/MonashBioinformaticsPlatform/laxy@"
    f"{BRANCH}/tests/data/annotation_corpus",
)
CORPUS = Path(__file__).resolve().parent


def md5_b64(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 16), b""):
            h.update(chunk)
    return f"md5:{h.hexdigest()}"


def case_paths(case_id: str) -> dict:
    d = CORPUS / "cases" / case_id
    ann = next(d.glob("annotation.*"))
    return {
        "genome": CORPUS / "shared" / "genome.fa",
        "annotation": ann,
        "r1": d / "reads" / "sample_R1.fastq.gz",
        "r2": d / "reads" / "sample_R2.fastq.gz",
        "manifest": d / "manifest.json",
    }


def gh_url(rel: str) -> str:
    return f"{GH_RAW}/{rel}"


def build_params(case_id: str) -> dict:
    p = case_paths(case_id)
    manifest = json.loads(p["manifest"].read_text())
    klass = manifest.get("class", "euk")
    ann_name = p["annotation"].name
    # annotation type-tag suffix: gtf vs gff
    ann_tag = "gtf" if ann_name.endswith(".gtf") or ann_name.endswith(".gtf.gz") else "gff"

    genome_url = gh_url("shared/genome.fa")
    annot_url = gh_url(f"cases/{case_id}/{ann_name}")
    r1_url = gh_url(f"cases/{case_id}/reads/sample_R1.fastq.gz")
    r2_url = gh_url(f"cases/{case_id}/reads/sample_R2.fastq.gz")

    blob = {
        "params": {
            "genome": None,
            "description": f"corpus e2e: {case_id} ({manifest.get('description','')})",
            "fetch_files": [
                {
                    "name": "genome.fa",
                    "location": genome_url,
                    "type_tags": ["reference_genome", "genome_sequence", "fasta"],
                },
                {
                    "name": ann_name,
                    "location": annot_url,
                    "type_tags": ["reference_genome", "genome_annotation", ann_tag],
                },
                {
                    "name": "sample_R1.fastq.gz",
                    "location": r1_url,
                    "metadata": {"read_pair": "R1"},
                    "type_tags": ["ngs_reads", "fastq"],
                },
                {
                    "name": "sample_R2.fastq.gz",
                    "location": r2_url,
                    "metadata": {"read_pair": "R2"},
                    "type_tags": ["ngs_reads", "fastq"],
                },
            ],
            "user_genome": {"fasta_url": genome_url, "annotation_url": annot_url},
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
            },
            "pipeline_version": "3.18.0",
        },
        "pipeline": "nf-core-rnaseq",
        "description": f"corpus e2e: {case_id}",
        "sample_cart": {
            "samples": [
                {
                    "name": "sample",
                    "sanitized_name": "sample",
                    "files": [
                        {
                            "R1": {"name": "sample_R1.fastq.gz",
                                   "location": r1_url,
                                   "sanitized_filename": "sample_R1.fastq.gz"},
                            "R2": {"name": "sample_R2.fastq.gz",
                                   "location": r2_url,
                                   "sanitized_filename": "sample_R2.fastq.gz"},
                        }
                    ],
                }
            ]
        },
    }
    return blob


def api_call(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    key = os.environ.get("LAXY_API_KEY_DEV", "")
    if not key:
        sys.exit("LAXY_API_KEY_DEV not set")
    url = f"{API}/api/v1/{path.lstrip('/')}"
    data = None
    headers = {"Authorization": f"Bearer {key}"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def submit(case_id: str, status: str = "hold") -> str:
    blob = build_params(case_id)
    tag = f"corpus-e2e-{case_id}-{int(time.time())}"
    blob["description"] = tag
    body = {
        "pipeline": "nf-core-rnaseq",
        "params": json.dumps(blob),  # params is a JSON string
        "description": tag,
        # compute_resource left unset -> auto-selected (default online resource).
    }
    if status:
        body["status"] = status
    code, resp = api_call("POST", "job/", body)
    if code == 200 and isinstance(resp, dict):
        job_id = resp.get("id")
        print(f"[{case_id}] submitted job {job_id} (status={status or 'launched'})")
        return job_id
    sys.exit(f"POST /job/ failed: HTTP {code}\n{str(resp)[:600]}")


def start(job_id: str) -> None:
    # PATCH status to empty/STARTING to release a held job
    code, resp = api_call("PATCH", f"job/{job_id}/", {"status": ""})
    print(f"[{job_id}] start -> HTTP {code}: {str(resp)[:200]}")


def get_job(job_id: str) -> dict:
    code, resp = api_call("GET", f"job/{job_id}/")
    if code != 200:
        sys.exit(f"GET job failed: HTTP {code}\n{resp}")
    return resp  # type: ignore[return-value]


def poll(job_id: str, timeout: int = 3600) -> str:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        j = get_job(job_id)
        st = j.get("status", "?")
        if st != last:
            print(f"[{job_id}] status: {st}")
            last = st
        if st in ("complete", "failed", "cancelled"):
            return st
        time.sleep(20)
    print(f"[{job_id}] TIMEOUT after {timeout}s (last={last})")
    return last


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case_id", help="e.g. E1_eukaryote_ensembl")
    ap.add_argument("--hold", action="store_true", help="submit as HOLD (no launch)")
    ap.add_argument("--start", metavar="JOB_ID", help="release a held job")
    ap.add_argument("--run", action="store_true", help="submit + launch immediately")
    ap.add_argument("--poll", metavar="JOB_ID", help="poll a job to completion")
    ap.add_argument("--show", metavar="JOB_ID", help="print a job's params")
    ap.add_argument("--delete", metavar="JOB_ID", help="delete a job")
    args = ap.parse_args()

    if args.show:
        j = get_job(args.show)
        print(json.dumps(j.get("params", {}), indent=2)[:3000])
        return
    if args.delete:
        code, resp = api_call("DELETE", f"job/{args.delete}/")
        print(f"delete {args.delete}: HTTP {code}")
        return
    if args.start:
        start(args.start)
        return
    if args.poll:
        result = poll(args.poll)
        print(f"final: {result}")
        return
    if args.hold:
        submit(args.case_id, status="hold")
        return
    if args.run:
        jid = submit(args.case_id, status="")
        print(f"watching {jid} ...")
        result = poll(jid)
        print(f"final: {result}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
