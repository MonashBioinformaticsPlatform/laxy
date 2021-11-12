#!/usr/bin/env python3

from typing import Sequence, Union

import sys
import os
from pathlib import Path
import json
import re

import string
import unicodedata

# from text_unidecode import unidecode

from urllib.parse import unquote

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

archive_extensions = [".tar.gz", ".tar", ".zip"]


def is_valid_reads_extension(fn) -> bool:
    return any([fn.endswith(ext) for ext in extensions])


def read_extension(fn) -> Union[None, str]:
    for ext in extensions:
        if fn.endswith(ext):
            return ext
    return None


# NOTE: This is duplicated code from laxy_backend/util.py since e'd like this script
# to be standalone without unusual dependencies. The unicode_to_ascii option is disabled
# for this reason, since it required the third-party library text_unidecode.
# If in the future we end up with a shared compute-side library, it should be moved there.
def sanitize_filename(
    filename: str,
    valid_filename_chars: str = None,
    replace: dict = None,
    max_length: int = 255,
    # unicode_to_ascii=False,
    unquote_urlencoding=True,
) -> str:
    """
    Adapted from: https://gist.github.com/wassname/1393c4a57cfcbf03641dbc31886123b8

    Replaces or removes characters that aren't filename safe on most platforms (or often
    cause issues in shell commmands when left unescaped), spaces to underscores, 
    truncates the filename length and replaces a subset of Unicode characters with 
    US-ASCII transliterations (eg à -> a, 蛇 -> She).
    """
    if valid_filename_chars is None:
        # valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        # Brackets often cause issue with improperly escaped shell commands, so we disallow those too ..
        valid_filename_chars = "-_. %s%s" % (string.ascii_letters, string.digits)

    if replace is None:
        replace = {" ": "_"}

    if unquote_urlencoding:
        filename = unquote(filename)

    # if unicode_to_ascii:
    #    filename = unidecode(filename)

    # replace spaces or other characters in the replacement dict
    for old, new in replace.items():
        filename = filename.replace(old, new)

    # keep only valid ascii chars
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )

    # keep only valid chars
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)

    return cleaned_filename[:max_length]


# NOTE: This is duplicated code from laxy_backend/util.py since e'd like this script
# to be standalone without unusual dependencies. If in the future we end up with a
# shared compute-side library, it should be moved there.
def truncate_fastq_to_pair_suffix(fn: str) -> str:
    """
    Turn a XXXBLAFOO_R1.fastq.gz filename into XXXBLAFOO_R1.
    """
    extensions = [
        r"_001\.fastq\.gz$",  # Default Illumina
        r"\.fastq\.gz$",  # ENA/SRA
        r"\.fasta\.gz$",  # occasionally we get FASTA format reads
        r"\.fq\.gz$",  # BGI does this, it seems
        r"\.fastq$",  # Occasionally we need to take uncompressed fastqs
        r"\.fasta$",  # why not
    ]

    # Try removing all of these extensions
    for ext in extensions:
        fn = re.sub(ext, "", fn, 1)

    return fn


# NOTE: This is duplicated code from laxy_backend/util.py since e'd like this script
# to be standalone without unusual dependencies. If in the future we end up with a
# shared compute-side library, it should be moved there.
def simplify_fastq_name(filename: str) -> str:
    """
    Given a FASTQ filename XXXBLAFOO_R1.fastq.gz, return something like
    the 'sample name' XXXBLAFOO. Should work with typical naming used by 
    Illumina instrument and SRA/ENA FASTQ files.
    """
    fn = truncate_fastq_to_pair_suffix(filename)
    # eg remove suffix _L002_R1 or L003_2 or _2, or just _R2
    fn = re.sub(r"_(R)?[1-2]$|_L[0-9][0-9][0-9]_(R)?[1-2]$", "", fn, 1)
    return fn


def get_expected_pair_filename(fn) -> Union[None, str]:
    """
    Detect the pair suffix + extension for a read file, and generate it's matching R1/R2 pair filename
    Return the filename for expected paired file.
    """
    pair_suffixes = [
        ("_R1_001", "_R2_001"),
        ("_R1", "_R2"),
        ("_1", "_2"),
    ]

    for suf in pair_suffixes:
        extn = read_extension(fn)
        r1 = f"{suf[0]}{extn}"
        r2 = f"{suf[1]}{extn}"
        if str(fn).endswith(f"{r1}"):
            return re.sub(f"{re.escape(r1)}$", f"{r2}", fn)
        if str(fn).endswith(f"{r2}"):
            return re.sub(f"{re.escape(r2)}$", f"{r1}", fn)

    return None


def get_name_for_readfile(fn) -> str:
    return simplify_fastq_name(sanitize_filename(fn))


def is_R1(fn) -> bool:
    r1_suffixes = [
        "_R1_001",
        "_R1",
        "_1",
    ]
    extn = read_extension(fn)
    if extn is None:
        return False
    return any([fn.endswith(f"{suf}{extn}") for suf in r1_suffixes])


def get_filelist_from_filesystem(path, strandedness="guess") -> Sequence[str]:
    """
    Recursively search a path for NGS read files and return nf-core
    samplesheet lines of pairs.
    """
    sheetlines = []
    seen_pairs = []
    for root, _d, fs in os.walk(path, followlinks=True):
        for f in fs:
            if is_valid_reads_extension(f) and f not in seen_pairs:
                name = get_name_for_readfile(f)
                f_path = Path(root, f)
                pair_name = get_expected_pair_filename(f)
                pair_path = None
                if pair_name is not None:
                    pair_path = Path(root, pair_name)
                if (
                    pair_path is not None
                    and pair_path.exists()
                    and not is_R1(pair_name)
                ):
                    sheetlines.append(
                        f"{name},{str(f_path)},{str(pair_path)},{strandedness}"
                    )
                    seen_pairs.extend([f_path, pair_path])
                else:
                    sheetlines.append(f"{name},{str(f_path)},,{strandedness}")
                    seen_pairs.extend([f_path])

    return sheetlines


infn = sys.argv[1]
input_reads_path = sys.argv[2]
strandedness = sys.argv[3]

with open(infn, "r") as fh:
    jblob = json.load(fh)

outlines = []
outlines.append("sample,fastq_1,fastq_2,strandedness")

# check if an input file is a tar archive - if so, we use the files
# on the filesystem to generate the samplesheet rather than the
# pipeline_config.json. tar archives should need to be pre-extracted
# before this script is run (eg via laxydl)
is_archive = False
for sample in jblob["sample_cart"].get("samples", []):
    if is_archive:
        break
    for f in sample["files"]:
        r1_fn = f.get("R1", {}).get("sanitized_filename", "")
        tags = f.get("R1", {}).get("tags", [])
        if "archive" in tags or any(
            [r1_fn.endswith(ext) for ext in archive_extensions]
        ):
            is_archive = True
            break

if is_archive:
    sheetlines = get_filelist_from_filesystem(
        input_reads_path, strandedness=strandedness
    )
    outlines.extend(sheetlines)
else:
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
