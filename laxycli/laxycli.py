#!/usr/bin/env python3

# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "requests",
#   "pyjwt",
# ]
# ///

from typing import List, Mapping, Optional, Tuple
import os
import re
import sys
import time
import logging
import json
import requests
from urllib.parse import urlparse, parse_qs
from argparse import ArgumentParser, Namespace

logger = logging.getLogger(__name__)


def get_auth_headers(filepath=".private_request_headers") -> Mapping:
    if os.path.exists(filepath):
        with open(filepath, "r") as fh:
            headers_lines = fh.read().splitlines()

        headers = [
            tuple([part.strip() for part in l.split(":")]) for l in headers_lines
        ]
        headers = dict(headers)
    else:
        token = os.environ.get("LAXY_API_KEY", None) or os.environ.get(
            "LAXY_API_TOKEN", None
        )
        if token is None:
            raise Exception(
                f"No authentication token in {filepath}, LAXY_API_KEY or LAXY_API_TOKEN environment variable."
            )

        headers = {"Authorization": f"Bearer {token}"}

    return headers



def get_token_from_headers(headers: dict) -> str:
    """
    Extracts the JWT token from the Authorization header.

    :param headers: A dictionary containing the headers.
    :returns: The extracted token.
    :raises ValueError: If the Authorization header is missing or the format is incorrect.
    """
    auth_header = headers.get("Authorization")
    if not auth_header:
        raise ValueError("No Authorization header found.")

    parts = auth_header.split()
    if parts[0].lower() != "bearer" or len(parts) == 1:
        raise ValueError("Invalid Authorization header format.")

    return parts[1]


def decode_jwt(token: str) -> Mapping:
    try:
        import jwt
    except:
        raise ImportError(
            "Using this function requires the PyJWT package (pip install pyjwt)"
        )

    # Attempt to decode the JWT. Without the secret, we can't verify the signature, so we ignore it.
    # Never use this in production for any security-related processes!
    try:
        # Decode the JWT without verification (which is not secure).
        # You should pass the secret key if you have it to verify the token's signature.
        decoded = jwt.decode(token, options={"verify_signature": False})
    except jwt.DecodeError:
        raise ValueError("Token is invalid, cannot be decoded.")
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")

    return decoded


def filename_from_url(url: str) -> str:
    """Return the final path segment of a URL (the filename)."""
    return urlparse(url).path.split("/")[-1]


def rettype_from_query(url: str) -> Optional[str]:
    """Return the ``rettype``/``retmode`` query param (e.g. NCBI eutils ``efetch.fcgi?...&rettype=gff3``)."""
    qs = parse_qs(urlparse(url).query)
    for key in ("rettype", "retmode"):
        values = qs.get(key)
        if values:
            return values[0].lower()
    return None


def parse_urls_file(file_path: str) -> list:
    """
    Parses a file containing URLs, one per line, and returns a list of dictionaries with filename and URL.

    :param file_path: Path to the file containing URLs.
    :return: List of dictionaries with 'name' and 'location' keys.
    """
    urls_list = []
    with open(file_path, "r") as file:
        for line in file:
            url = line.strip()
            if url:  # Only process non-empty lines
                urls_list.append({"name": filename_from_url(url), "location": url})
    return urls_list


# Patterns used to detect the read-pair member (R1/R2) from a FASTQ filename.
# Tried in order; the first match wins. Covers the common Illumina-ish
# conventions plus the synthetic naming used by our test fixtures
# (``_R1``/``_R2``, ``_ss_1``/``_ss_2``, and a trailing ``_1``/``_2``).
_READ_PAIR_RES = [
    re.compile(r"_R([12])(?=[._])"),
    re.compile(r"_ss_([12])(?=[._])"),
    re.compile(r"_([12])(?=\.f(?:ast)?q(?:\.gz)?$)", re.IGNORECASE),
]

_FASTQ_EXTS = (".fastq.gz", ".fq.gz", ".fastq", ".fq", ".gz")


def _strip_fastq_ext(name: str) -> str:
    lower = name.lower()
    for ext in _FASTQ_EXTS:
        if lower.endswith(ext):
            return name[: -len(ext)]
    return name


def classify_read(filename: str) -> Tuple[Optional[str], str]:
    """Determine the read-pair member and sample base name for a FASTQ filename.

    :return: ``(pair, sample_name)`` where ``pair`` is ``"R1"``/``"R2"`` (or
        ``None`` when no pair token is found, i.e. single-end) and
        ``sample_name`` is the filename with the pair token and FASTQ
        extension removed.
    """
    for rx in _READ_PAIR_RES:
        m = rx.search(filename)
        if m:
            without_token = filename[: m.start()] + filename[m.end():]
            base = _strip_fastq_ext(without_token).rstrip("_.")
            return f"R{m.group(1)}", (base or filename)
    base = _strip_fastq_ext(filename).rstrip("_.")
    return None, (base or filename)


def create_samplecart(file_list: List[dict]) -> dict:
    """
    Build a SampleCart structure from a list of read files, grouping R1/R2
    members into samples by their shared base name.

    Single-end files (no detectable R1/R2 token) become single-file samples.

    :param file_list: A list of dictionaries, each containing 'name' and 'location' keys for a file.
    :return: A dict representing the SampleCart structure.
    """
    grouped: "dict[str, dict]" = {}
    order: List[str] = []
    for f in file_list:
        pair, sample_name = classify_read(f["name"])
        if sample_name not in grouped:
            grouped[sample_name] = {}
            order.append(sample_name)
        # Single-end reads with no pair token are treated as R1.
        grouped[sample_name][pair or "R1"] = f

    samples = []
    for sample_name in order:
        members = grouped[sample_name]
        files_entry = {}
        for pair in ("R1", "R2"):
            if pair in members:
                files_entry[pair] = members[pair]
        samples.append(
            {"name": sample_name, "files": [files_entry], "metadata": {"condition": ""}}
        )

    return {"samples": samples}


def build_fetch_files(
    read_files: List[dict],
    fasta_url: Optional[str] = None,
    annotation_url: Optional[str] = None,
) -> List[dict]:
    """Build the ``fetch_files`` list the backend downloads as job input.

    When a custom reference genome is supplied (``fasta_url`` + ``annotation_url``)
    the genome and annotation are prepended with the type tags the pipeline
    expects, mirroring the web frontend's ``generateFetchFilesList``. Read files
    are tagged ``ngs_reads``/``fastq`` and annotated with their ``read_pair``.
    """
    fetch_files: List[dict] = []

    if fasta_url and annotation_url:
        annot_rettype = rettype_from_query(annotation_url)
        if ".gff" in annotation_url.lower() or annot_rettype == "gff3":
            annot_type = "gff"
            annot_ext = "gff3"
        elif ".gtf" in annotation_url.lower() or annot_rettype == "gtf":
            annot_type = "gtf"
            annot_ext = "gtf"
        else:
            annot_type = "unknown_annotation_type"
            annot_ext = "download"

        fasta_name = filename_from_url(fasta_url)
        annotation_name = filename_from_url(annotation_url)
        if fasta_name == annotation_name:
            # e.g. NCBI eutils efetch.fcgi?...&rettype=fasta vs ...&rettype=gff3 -
            # both have the same URL basename, so the fetched files would collide
            # once downloaded to the same local directory. Disambiguate using the
            # detected type/extension instead.
            fasta_rettype = rettype_from_query(fasta_url)
            fasta_name = f"genome.{fasta_rettype or 'fasta'}"
            annotation_name = f"annotation.{annot_ext}"

        fetch_files.append(
            {
                "name": fasta_name,
                "location": fasta_url.strip(),
                "type_tags": ["reference_genome", "genome_sequence", "fasta"],
            }
        )
        fetch_files.append(
            {
                "name": annotation_name,
                "location": annotation_url.strip(),
                "type_tags": ["reference_genome", "genome_annotation", annot_type],
            }
        )

    for f in read_files:
        pair, _ = classify_read(f["name"])
        entry = {
            "name": f["name"],
            "location": f["location"],
            "type_tags": ["ngs_reads", "fastq"],
        }
        if pair:
            entry["metadata"] = {"read_pair": pair}
        fetch_files.append(entry)

    return fetch_files


def load_json_arg(value: str) -> dict:
    """Load JSON from an inline string or, if prefixed with ``@``, a file path."""
    if value.startswith("@"):
        with open(value[1:], "r") as fh:
            return json.load(fh)
    return json.loads(value)


def poll_job(
    api_base_url: str,
    job_id: str,
    headers: Mapping,
    interval: int = 10,
    timeout: int = 7200,
) -> str:
    """Poll a job until it reaches a terminal status (or times out)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{api_base_url}/job/{job_id}/", headers=headers, timeout=30
            )
            status = resp.json().get("status")
        except requests.RequestException as e:
            logger.warning(f"poll error for {job_id}: {e}")
            time.sleep(interval)
            continue
        if status != last:
            logger.info(f"job {job_id}: {status}")
            last = status
        if status in ("complete", "failed", "cancelled"):
            return status
        time.sleep(interval)
    logger.warning(f"job {job_id}: timed out after {timeout}s (last status={last})")
    return last or "unknown"


def create_job(args: Namespace) -> Optional[str]:
    read_files = parse_urls_file(args.urls_file)
    headers = get_auth_headers()

    use_custom_genome = bool(args.genome_fasta_url and args.genome_annotation_url)
    if bool(args.genome_fasta_url) != bool(args.genome_annotation_url):
        sys.exit(
            "Both --genome_fasta_url and --genome_annotation_url must be given together "
            "to use a custom reference genome."
        )

    samplecart = create_samplecart(read_files)
    response = requests.post(
        f"{args.api_base_url}/samplecart/", json=samplecart, headers=headers
    )
    response.raise_for_status()
    samplecart_id = response.json().get("id")

    params = {
        "pipeline_version": args.pipeline_version,
        "description": args.job_description,
        "fetch_files": build_fetch_files(
            read_files,
            args.genome_fasta_url if use_custom_genome else None,
            args.genome_annotation_url if use_custom_genome else None,
        ),
    }
    if use_custom_genome:
        params["genome"] = None
        params["user_genome"] = {
            "fasta_url": args.genome_fasta_url.strip(),
            "annotation_url": args.genome_annotation_url.strip(),
        }
    else:
        params["genome"] = args.reference_genome_id

    if args.pipeline_params_json:
        params.update(load_json_arg(args.pipeline_params_json))

    pipeline_run_data = {
        "pipeline": args.pipeline_name,
        "sample_cart": samplecart_id,
        "params": params,
        # PipelineRun.description is a dedicated model field, distinct from
        # params["description"] - the frontend job list reads it back via
        # job.params.description (copied from here by _set_request_params_from_pipelinerun).
        "description": args.job_description,
    }

    logger.debug(json.dumps(pipeline_run_data))
    pipeline_run_resp = requests.post(
        f"{args.api_base_url}/pipelinerun/", json=pipeline_run_data, headers=headers
    )
    pipeline_run_resp.raise_for_status()
    pipelinerun_id = pipeline_run_resp.json().get("id", None)

    if pipelinerun_id is None:
        logger.error("Failed to create pipelinerun")
        sys.exit(1)

    job_create_body = {}
    if getattr(args, "compute_resource_id", None):
        # Explicit compute_resource bypasses the backend's auto-selection
        # (highest-priority online ComputeResource matching the owner's email
        # domain rule), which on environments with multiple registered compute
        # resources (e.g. real HPC clusters alongside a local fake-cluster for
        # testing) could otherwise route a job somewhere unintended.
        job_create_body["compute_resource"] = args.compute_resource_id

    job_resp = requests.post(
        f"{args.api_base_url}/job/?pipeline_run_id={pipelinerun_id}",
        json=job_create_body,
        headers=headers,
    )
    try:
        job_resp_blob = job_resp.json()
    except ValueError:
        job_resp_blob = {}
    logger.debug(job_resp_blob)

    job_id = job_resp_blob.get("id", None)
    if job_id is None:
        # The job may have been created even when the response serialisation
        # fails; surface the HTTP status so the caller can investigate.
        logger.error(
            f"Job creation response did not contain an id (HTTP {job_resp.status_code}): "
            f"{str(job_resp.text)[:500]}"
        )
        sys.exit(1)

    # job_id is printed to stdout (everything else goes to the logger/stderr)
    # so it can be captured by a calling script.
    print(job_id)

    if not args.wait:
        return job_id

    status = poll_job(args.api_base_url, job_id, headers)
    logger.info(f"job {job_id} final status: {status}")
    return job_id


def job_status(args: Namespace) -> None:
    headers = get_auth_headers()
    if args.watch:
        status = poll_job(args.api_base_url, args.job_id, headers)
        print(status)
        return
    resp = requests.get(
        f"{args.api_base_url}/job/{args.job_id}/", headers=headers, timeout=30
    )
    resp.raise_for_status()
    print(resp.json().get("status"))


def download_job(api_base_url: str, job_id: str, headers: Mapping) -> None:
    """
    Downloads the job tarball from the API.

    :param api_base_url: The base URL for the API.
    :param job_id: The ID of the job to download.
    :param headers: A dictionary containing any headers needed for the request.
    """
    download_url = f"{api_base_url}/job/{job_id}/download/"
    response = requests.get(download_url, headers=headers, stream=True)

    # Check if the request was successful
    response.raise_for_status()

    # Set the output filename
    output_filename = f"{job_id}.tar.gz"

    # Stream the download to the file
    with open(output_filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=16384):
            f.write(chunk)

    logger.info(f"Downloaded job {job_id} to {output_filename}.")


def download_file(
    api_base_url: str, job_id: str, file_path: str, headers: Mapping
) -> None:
    """
    Downloads a specific file from a job using the Laxy API.

    :param api_base_url: URL of the Laxy API.
    :param job_id: ID of the job.
    :param file_path: Path of the file to download.
    :param headers: Headers for the API request.
    """
    file_download_url = f"{api_base_url}/job/{job_id}/files/{file_path}?download"

    response = requests.get(file_download_url, headers=headers, stream=True)
    response.raise_for_status()

    filename = file_path.split("/")[-1]
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=16384):
            f.write(chunk)

    logger.info(f"Downloaded file {filename} from job {job_id}.")


def main():
    default_api_base_url = os.environ.get("LAXY_API_URL", "https://api.laxy.io/api/v1")

    parser = ArgumentParser(description="Interact with the Laxy API.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Subcommands (use {command} -h for details)",
    )

    # Parent parser for common arguments
    parent_parser = ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--api_base_url",
        type=str,
        default=default_api_base_url,
        help="Base URL for the Laxy API.",
    )

    # Subparser for the 'job' command
    job_parser = subparsers.add_parser("job", help="Job related commands")
    job_subparsers = job_parser.add_subparsers(
        title="subcommands", dest="subcommand", help="Job actions"
    )

    # Subparser for the 'job create' command
    job_create_parser = job_subparsers.add_parser(
        "create", parents=[parent_parser], help="Create a new job"
    )
    job_create_parser.add_argument(
        "--pipeline_name",
        type=str,
        required=True,
        help="Name of the pipeline to run.",
    )
    job_create_parser.add_argument(
        "--pipeline_version",
        type=str,
        required=True,
        help="Version of the pipeline to run.",
    )
    job_create_parser.add_argument(
        "--job_description",
        type=str,
        default="laxycli job",
        help="Description of the job.",
    )
    job_create_parser.add_argument(
        "--reference_genome_id",
        type=str,
        default="Homo_sapiens/Ensembl/GRCh38",
        help="ID of a built-in (iGenomes) reference genome. Ignored when "
        "--genome_fasta_url/--genome_annotation_url are given.",
    )
    job_create_parser.add_argument(
        "--genome_fasta_url",
        type=str,
        default=None,
        help="URL of a custom reference genome FASTA. Use together with "
        "--genome_annotation_url to run against a custom reference.",
    )
    job_create_parser.add_argument(
        "--genome_annotation_url",
        type=str,
        default=None,
        help="URL of a custom reference annotation (GTF/GFF3).",
    )
    job_create_parser.add_argument(
        "--pipeline_params_json",
        type=str,
        default=None,
        help="Extra pipeline params as a JSON object, merged into the "
        "pipelinerun params (e.g. '{\"nf-core-rnaseq\": {...}}'). "
        "Prefix with @ to read from a file.",
    )
    job_create_parser.add_argument(
        "--urls_file",
        type=str,
        required=True,
        help="File containing URLs of input read files, one per line.",
    )
    job_create_parser.add_argument(
        "--compute_resource_id",
        type=str,
        default=None,
        help="Explicit ComputeResource id to run the job on, bypassing the "
        "backend's auto-selection (highest-priority online resource "
        "matching the owner's email domain rule). Use this on environments "
        "with multiple registered compute resources to avoid accidentally "
        "targeting a real HPC cluster instead of a local test resource.",
    )
    job_create_parser.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="Submit the job and print its id without polling to completion.",
    )
    job_create_parser.set_defaults(wait=True)
    job_create_parser.set_defaults(func=create_job)

    # Subparser for the 'job status' command
    job_status_parser = job_subparsers.add_parser(
        "status", parents=[parent_parser], help="Get (or watch) a job's status"
    )
    job_status_parser.add_argument(
        "job_id", type=str, help="The ID of the job to check."
    )
    job_status_parser.add_argument(
        "--watch",
        action="store_true",
        help="Poll until the job reaches a terminal status.",
    )
    job_status_parser.set_defaults(func=job_status)

    job_download_parser = job_subparsers.add_parser(
        "download", parents=[parent_parser], help="Download a job tarball"
    )
    job_download_parser.add_argument(
        "job_id", type=str, help="The ID of the job to download."
    )
    job_download_parser.set_defaults(
        func=lambda args: download_job(
            args.api_base_url, args.job_id, get_auth_headers()
        )
    )

    # Subparser for the 'file download' command
    file_download_parser = subparsers.add_parser(
        "file", parents=[parent_parser], help="File related commands"
    )
    file_download_subparsers = file_download_parser.add_subparsers(
        title="subcommands", dest="subcommand", help="File actions"
    )

    file_download_cmd_parser = file_download_subparsers.add_parser(
        "download", parents=[parent_parser], help="Download a specific file from a job"
    )
    file_download_cmd_parser.add_argument(
        "job_id", type=str, help="The ID of the job containing the file."
    )
    file_download_cmd_parser.add_argument(
        "path", type=str, help="The path of the file to download."
    )
    file_download_cmd_parser.set_defaults(
        func=lambda args: download_file(
            args.api_base_url, args.job_id, args.path, get_auth_headers()
        )
    )

    # Parse the arguments
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    # Call the function associated with the chosen subcommand
    if hasattr(args, "func"):
        args.func(args)
    else:
        # No subcommand was provided
        parser.print_help()


if __name__ == "__main__":
    main()
