#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Batch-submit corpus cases to a remote Laxy server, staggering submissions
so the file CDN (jsDelivr) isn't overwhelmed by concurrent downloads.

Submits one case, waits for it to clear the download phase (status != created
and past ~90s), then submits the next. After all are submitted, polls to
completion and prints a summary.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_corpus_job import submit, build_params, api_call, get_job  # noqa: E402

GAP_S = 150  # gap between submissions (lets the CDN download complete)


def poll_batch(jobs: dict[str, str], timeout: int = 1200) -> dict[str, str]:
    api_key = os.environ["LAXY_API_KEY_DEV"]
    API = os.environ.get("LAXY_API_BASE_URL", "https://dev.laxy.io:8001").rstrip("/")
    last: dict[str, str] = {}
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = [n for n in jobs if last.get(n) not in ("complete", "failed", "cancelled")]
        if not pending:
            break
        for name in pending:
            try:
                req = urllib.request.Request(
                    f"{API}/api/v1/job/{jobs[name]}/",
                    headers={"Authorization": f"Bearer {api_key}"})
                st = json.loads(urllib.request.urlopen(req, timeout=20).read()).get("status", "?")
            except Exception:
                continue
            if st != last.get(name):
                print(f"  [{time.strftime('%H:%M:%S')}] {name}: {st}")
                last[name] = st
        time.sleep(30)
    return last


def main() -> None:
    cases = sys.argv[1:]
    if not cases:
        sys.exit("usage: batch_submit.py CASE [CASE ...]")
    submitted: dict[str, str] = {}
    for case in cases:
        try:
            jid = submit(case, status="")
            submitted[case] = jid
        except SystemExit as e:
            print(f"  [{case}] FAILED to submit: {e}")
            continue
        print(f"  waiting {GAP_S}s for download phase before next submit...")
        time.sleep(GAP_S)
    print(f"\n=== all {len(submitted)} submitted; polling to completion ===")
    results = poll_batch(submitted, timeout=1200)
    print("\n=== SUMMARY ===")
    passed = 0
    for case in cases:
        st = results.get(case, "?")
        mark = "✓" if st == "complete" else "✗"
        if st == "complete":
            passed += 1
        print(f"  {mark} {case}: {st}")
    print(f"\n{passed}/{len(cases)} complete")


if __name__ == "__main__":
    main()
