#!/usr/bin/env python3
from typing import Sequence, Tuple, Union
import sys
import os
import argparse
import string
from pathlib import Path
from collections import OrderedDict
import itertools
import json
import re
from urllib.parse import unquote
import unicodedata

if sys.version_info.major == 3 and sys.version_info.minor < 10:
    from collections import Iterable
else:
    from collections.abc import Iterable


extensions = [
    ".fastq.gz",  # Typical Illumina extension
    ".fq.gz",  # BGI currently uses .fq.gz. See, MGI isn't just a copy of Illumina tech !
    ".fastq",  # IonTorrent tarballs contain uncompressed fastqs
    ".fq",  # Someone will do this one day
    ".fasta.gz",  # Very occasionally, we get FASTA format reads
    ".fa.gz",  # ... and this
    ".fasta",
    ".fa",
]

pair_suffixes = [
    ("_R1_001", "_R2_001"),  # Illumina instrument default
    ("_r1_001", "_r2_001"),  # Synapse bulk downloader renames to lowercase ?
    ("_R1", "_R2"),
    ("_1", "_2"),  # ENA/SRA
]


def fastq_detect_extension(files: Sequence) -> Union[None, str]:
    """
    Returns the extension in use for FASTQ files, for the RNAsik -extn flag, or
    None if no FASTQs were detected.

    Raises an exception if there are more than one extension in use, so we can
    fail fast.
    """
    extns = set()
    for f in files:
        for ext in extensions:
            if str(f).endswith(ext):
                extns.add(ext)

    if len(extns) > 1:
        raise Exception(f"More than one FASTQ extension in use: {', '.join(extns)}")
    if len(extns) == 0:
        return None

    return list(extns)[0]


def detect_pairing_suffix(files: Sequence, extn: str) -> Union[None, Tuple[str]]:
    """
    Detect the pair suffix in use for matching R1/R2 pairs of FASTQ files.
    Returns the pairing suffix in use if detected.
    Returns None if not paired end (eg no R2 detected).

    If more than one scheme is detected, raise an exception.
    """

    ps = set()
    for f in files:
        for suf in pair_suffixes:
            r2 = suf[1]
            if str(f).endswith(f"{r2}{extn}"):
                ps.add(suf)
    if len(ps) > 1:
        raise Exception(
            f"More than one pairing suffix in use: {'; '.join(','.join(ps))}"
        )
    if len(ps) == 0:
        return None

    return list(ps)[0]


if __name__ == "__main__":
    fastq_path = sys.argv[1]

    files = [f.name for f in Path(fastq_path).rglob("*") if f.is_file()]
    extn = fastq_detect_extension(files)
    if extn is None:
        sys.stderr.write(f"No FASTQ files found recursively in path: {fastq_path}\n")
        sys.exit(1)

    pair_suffix = detect_pairing_suffix(files, extn)

    try:
        if pair_suffix is not None and len(pair_suffix) == 2:
            sys.stdout.write("paired")
        else:
            sys.stdout.write("single")
    except:
        sys.stdout.write("unknown")
