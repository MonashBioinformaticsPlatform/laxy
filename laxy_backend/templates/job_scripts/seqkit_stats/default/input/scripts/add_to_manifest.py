#!/usr/bin/env python3
import os
import sys
import stat
import subprocess
from fnmatch import fnmatch
import hashlib
import re
import json

"""
Appends row to a manifest.csv file, with the columns: 
checksum,filepath,type_tags,metadata

Run like:
python3 add_to_manifest.py /path/to/job/manifest.csv '*.html' 'html,report' '{"foo": "bar"}'
"""

manifest_file = sys.argv[1]

# exclude_files = [".private_request_headers", "manifest.csv", "job.pids", "slurm.jids"]

base_path = "."
glob_pattern = sys.argv[2]  # "*.bam"
tags = sys.argv[3]  # "html,report,multiqc"
if len(sys.argv) >= 4 and sys.argv[4].strip() != '':
    metadata = sys.argv[4]  # {"some_file": "extra_data"}
else:
    metadata = "{}"

metadata = json.dumps(json.loads(metadata))


def lstrip_dotslash(path):
    return re.sub("^%s" % "./", "", path)


existing_paths = []
if os.path.exists(manifest_file):
    with open(manifest_file, "r") as fh:
        for l in fh:
            s = l.split(",")
            existing_paths.append(s[1].strip("\""))


def find(base_path, f):
    for path in base_path:
        for root, dirs, files in os.walk(path):
            for fi in files:
                if f(os.path.join(root, fi)):
                    yield os.path.join(root, fi)
            for di in dirs:
                if f(os.path.join(root, di)):
                    yield os.path.join(root, fi)


def get_md5(file_path, blocksize=512):
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(blocksize)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def md5sum(file_path, md5sum_executable="/usr/bin/md5sum"):
    out = subprocess.check_output([md5sum_executable, file_path])
    checksum = out.split()[0]
    if len(checksum) == 32:
        return checksum
    else:
        raise ValueError("md5sum failed: %s", out)


write_header = not os.path.exists(manifest_file)

with open(manifest_file, "a") as fh:
    if write_header:
        fh.write("checksum,filepath,type_tags,metadata\n")

    for hit in find([base_path], lambda fn: fnmatch(fn, glob_pattern)):
        abspath = lstrip_dotslash(hit)
        # if abspath in exclude_files:
        #   continue
        # if not (abspath.startswith("output") or abspath.startswith("input")):
        #   continue
        if abspath in existing_paths:
            continue
        if not os.path.exists(abspath):
            continue
        checksum = f"md5:{get_md5(abspath)}"
        fh.write(f"\"{checksum}\",\"{abspath}\",\"{tags}\",{metadata}\n")
        existing_paths.append(abspath)
