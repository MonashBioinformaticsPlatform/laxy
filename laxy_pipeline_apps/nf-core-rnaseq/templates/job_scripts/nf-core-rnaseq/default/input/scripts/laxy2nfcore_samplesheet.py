#!/usr/bin/env python3

import sys
from pathlib import Path
import json

infn = sys.argv[1]
input_reads_path = sys.argv[2]
strandedness = sys.argv[3]

with open(infn, "r") as fh:
    jblob = json.load(fh)

outlines = []
outlines.append("sample,fastq_1,fastq_2,strandedness")

for sample in jblob["sample_cart"].get("samples", []):
    name = sample["name"]
    for f in sample["files"]:
        r1_fn = f.get("R1", {}).get("sanitized_filename", "")
        r2_fn = f.get("R2", {}).get("sanitized_filename", "")
        if r1_fn:
            r1_fn = Path(input_reads_path, r1_fn)
        if r2_fn:
            r2_fn = Path(input_reads_path, r2_fn)

    outlines.append(f"{name},{r1_fn},{r2_fn},{strandedness}")

print("\n".join(outlines))
