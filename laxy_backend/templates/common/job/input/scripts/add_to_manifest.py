#!/usr/bin/env python3
import os
import sys
import stat
import subprocess
from fnmatch import fnmatch
import hashlib
import re
import json
import argparse

"""
Appends row to a manifest.csv file, with the columns: 
checksum,filepath,type_tags,metadata

Run like:
python3 add_to_manifest.py /path/to/job/manifest.csv '*.html' 'html,report' '{"foo": "bar"}'
"""

def lstrip_dotslash(path):
    return re.sub("^%s" % "./", "", path)

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


def md5sum(file_path: str, md5sum_executable: str="/usr/bin/md5sum"):
    """[summary]
    Uses the system md5sum binary to generate an MD5 checksum for a file.
    While using Python's internal hashlib.md5 implementation is more portable
    and reliable this function may be faster in some cases.

    Args:
        file_path (str): Path to the file.
        md5sum_executable (str, optional): Path to the md5sum binary Defaults to "/usr/bin/md5sum".

    Raises:
        ValueError: Raised if attempting to run md5sum appeared to fail.

    Returns:
        str: The MD5 checksum (typical hex encoded string).
    """
    out = subprocess.check_output([md5sum_executable, file_path])
    checksum = out.split()[0]
    if len(checksum) == 32:
        return checksum
    else:
        raise ValueError("md5sum failed: %s" % out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_file", default="manifest.csv", help="The path to the manifest.csv")
    parser.add_argument("glob_pattern", nargs='?', default="*", 
        help='A (quoted) glob pattern for filtering filenames (eg "*.bam")')
    parser.add_argument("tags", nargs='?', default='', help='A comma seperated list of tags (eg "html,report,multiqc")')
    parser.add_argument("metadata", nargs='?', default='{}', 
        help='A JSON blob of extra metadata (eg \'{"metadata":{"bla":"foo"}}\')')
    parser.add_argument("--location-base", default=None, 
        help='Register files as located with this URL prefix '
             '(eg a laxy+sftp://someComputeID/someJobID/output/somefile.txt). The Laxy backend will usually infer the'
             'location based on the job & known compute resource, however there are cases where you may need to'
             'explicitly specify this (eg if files were moved to an archive location manually rather than via '
             'a backend task)')
    args = parser.parse_args()

    manifest_file = args.manifest_file

    # exclude_files = [".private_request_headers", "manifest.csv", "job.pids", "slurm.jids"]

    base_path = "."
    glob_pattern = args.glob_pattern  # "*.bam"
    tags = args.tags  # "html,report,multiqc"
    metadata = args.metadata  # {"some_file": "extra_data"}
    location_base = args.location_base

    if metadata.strip() == '':
        metadata = '{}' 
    metadata = json.dumps(json.loads(metadata))

    existing_paths = []
    if os.path.exists(manifest_file):
        with open(manifest_file, "r") as fh:
            for l in fh:
                s = l.split(",")
                existing_paths.append(s[1].strip("\""))

    write_header = not os.path.exists(manifest_file)

    with open(manifest_file, "a") as fh:
        if write_header:
            if location_base:
                fh.write("checksum,filepath,location,type_tags,metadata\n")
            else:
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
            if location_base:
                fh.write(f"\"{checksum}\",\"{abspath}\",\"{location_base}/{abspath}\",\"{tags}\",{metadata}\n")
            else:
                fh.write(f"\"{checksum}\",\"{abspath}\",\"{tags}\",{metadata}\n")
            existing_paths.append(abspath)
