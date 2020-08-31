#!/usr/bin/env python3

# This script should:
#  - read pipeline_config.json
#  - generate sampleSheet.txt with {filename: 'cart name'} mapping
#  - guess -pairIds setting (or generate pair mapping file, when supported)
#  - handle bds.config and sik.config copying and modifications (to keep run_job.sh less pipeline specific) ?

from typing import Sequence, Tuple, Union
import sys
import os
import argparse
import string
from collections import OrderedDict, Iterable
import itertools
import json
import re
from urllib.parse import unquote
import unicodedata

# Since this requires a dependency we don't use it at all
# try:
#     from text_unidecode import unidecode
# except ImportError:
#     # Monkey patch this to do nothing if we don't have the dependency,
#     # since it's nice but not essential.
#     def unidecode(s):
#         return s


def flatten_deep(items):
    """
    Yield items from any nested iterable, including dictionaries.
    Based on: https://stackoverflow.com/a/40857703
    """
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def flatten(list2d):
    return list(itertools.chain(*list2d))


def longest_common_prefix(string_list: Sequence[Sequence]):
    return os.path.commonprefix(string_list)


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
    #     filename = unidecode(filename)

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


def config_contains_tar(pipeline_config: dict, tags=None) -> bool:
    """
    Check if the input file list contains a `.tar` archive.
    """
    if tags is None:
        tags = ["archive", "inside_archive"]

    params = pipeline_config.get("params", {})
    ffiles = params.get("fetch_files", [])

    for ff in ffiles:
        # For tar archives, we don't attempt to make a samplesSheet
        ftags = ff.get("tags", [])
        if any([t in ftags for t in tags]):
            return True

    return False


def generate_samplesheet(
    pipeline_config: dict,
) -> Union[None, Sequence[Tuple[str, str]]]:
    """
    Given a pipeline_config.json dict, return lines for an RNAsik sampleSheet.txt (v1.5.4).

    The samplesheet should looke something like:

    old_prefix	         new_prefix
    sanitizedNameA_L001  sampleA
    sanitizedNameA_L002  sampleA
    sanitizedNameB_L001  sampleB
    sanitizedNameB_L001  sampleB

    _R1 / _R2 suffixes aren't included (these are detected seperately via -pairIds), and files
    mapped with identical names in new_prefix are considered technical replicates, such as samples 
    split across lanes, than can be merged (in a paired file aware way).
    """

    sample_cart = pipeline_config.get("sample_cart", {})
    samples = sample_cart.get("samples", [])

    samplesheet = []
    for sample in samples:
        # this is the sanitized user supplied sample name
        # (associated with both R1 and R2, maybe file that represents technical replicates)
        sane_name = sanitize_filename(sample.get("sanitized_name", sample["name"]))

        # We get all the sanitized_filenames for the sample, then
        # find the longest common prefix. This essentially mimicks what
        # RNAsik does when it automatically generates a samplesheet
        # print(sample["files"])
        sample_files = flatten([list(f.values()) for f in sample["files"]])

        file_name_prefixes = [
            simplify_fastq_name(
                f.get("sanitized_filename", sanitize_filename(f["name"]))
            )
            for f in sample_files
        ]

        sample_prefix = longest_common_prefix(file_name_prefixes)

        samplesheet.append((sample_prefix, sane_name))
        # TODO: If the user enters sample names like:
        #       sampleA_L003.fq.gz and sampleA_L004.fq.gz
        #       we actually need sample_prefix as new_prefix ....
        #       This is essentially user or frontend error in sample naming that results in a 'backward' sample sheet.
        #       We should automatically strip off any _L00{0-9}_R{1-2}.fastq.gz in step 2 sample table when automatically
        #       generating names.
        # samplesheet.append((sane_name, sample_prefix))

    return samplesheet


def to_tsv_line(row):
    return "%s\n" % "\t".join(row)


if __name__ == "__main__":

    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(help="sub-command help", dest="command")

    samplesheet_parser = subparsers.add_parser(
        "samplesheet",
        help="Generate an RNAsik samplesheet from the given pipeline_config.json",
    )

    samplesheet_parser.add_argument(
        "pipeline_config_fn",
        nargs="?",
        default="pipeline_config.json",
        help="Path the pipeline_config.json.",
    )

    pair_parser = subparsers.add_parser(
        "pairids",
        help=(
            "Return the RNAsik commandline args for -extn, -paired and -pairIds "
            "by recursively searching for FASTQ files in the given path."
        ),
    )

    pair_parser.add_argument(
        "fastq_path",
        nargs="?",
        default=".",
        help="Path to search recursively for FASTQ input files.",
    )

    args = argparser.parse_args()

    if args.command == "samplesheet":
        with open(args.pipeline_config_fn) as pc:
            pipeline_config = json.loads(pc.read())

        if not config_contains_tar(pipeline_config):
            samplesheet = generate_samplesheet(pipeline_config)

            # with open("sampleSheet.txt", "wt") as fh:
            with sys.stdout as fh:
                fh.write(to_tsv_line(["old_prefix", "new_prefix"]))
                for l in samplesheet:
                    fh.write(to_tsv_line(l))
        else:
            sys.stderr.write(
                "No samplesSheet.txt output generated - at least one input file is a tar archive.\n"
            )

    def _fastq_detect_extension(files: Sequence) -> Union[None, str]:
        """
        Returns the extension in use for FASTQ files, for the RNAsik -extn flag, or
        None if no FASTQs were detected.

        Raises an exception if there are more than one extension in use, so we can 
        fail fast.
        """
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

    def _detect_pairing_suffix(files: Sequence, extn: str) -> Union[None, Tuple[str]]:
        """
        Detect the pair suffix in use for matching R1/R2 pairs of FASTQ files.
        Returns the pairing suffix in use if detected.
        Returns None if not paired end (eg no R2 detected).

        If more than one scheme is detected, raise an exception.
        """
        pair_suffixes = [
            ("_R1_001", "_R2_001"),
            ("_R1", "_R2"),
            ("_1", "_2"),
        ]

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

    if args.command == "pairids":
        from pathlib import Path

        files = [f.name for f in Path(args.fastq_path).rglob("*") if f.is_file()]
        extn = _fastq_detect_extension(files)
        if extn is None:
            sys.stderr.write(
                f"No FASTQ files found recursively in path: {args.fastq_path}\n"
            )
            sys.exit(1)

        pair_suffix = _detect_pairing_suffix(files, extn)

        cmd_args = f" -extn {extn} "
        if pair_suffix is not None:
            cmd_args += f" -paired -pairIds {','.join(pair_suffix)} "

        sys.stdout.write(cmd_args)
