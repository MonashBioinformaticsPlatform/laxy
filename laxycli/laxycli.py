#!/usr/bin/env python3

from typing import List
import os
import sys
import time
import logging
import json
import requests
from urllib.parse import urlparse
from argparse import ArgumentParser, Namespace

logger = logging.getLogger(__name__)


def get_auth_headers(filepath=".private_request_headers"):
    if os.path.exists(filepath):
        with open(filepath, "r") as fh:
            headers_lines = fh.read().splitlines()

        headers = [
            tuple([part.strip() for part in l.split(":")]) for l in headers_lines
        ]
        headers = dict(headers)
    else:
        token = os.environ.get("LAXY_API_TOKEN", None)
        if token is None:
            raise Exception(
                f"No authetication token in {filepath} or LAXY_API_TOKEN environment variable."
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


def decode_jwt(token: str) -> dict:
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
                filename = urlparse(url).path.split("/")[-1]
                urls_list.append({"name": filename, "location": url})
    return urls_list


def create_samplecart(file_list: List[dict]) -> dict:
    """
    Creates a SampleCart JSON structure based on the URLs provided in file_list.

    :param file_list: A list of dictionaries, each containing 'name' and 'location' keys for a file.
    :return: A JSON string representing the SampleCart structure.
    """
    # Initialize an empty list for the samples
    samples = []

    # Assume file_list is sorted such that R1 and R2 follow each other for each sample
    for i in range(0, len(file_list), 2):
        R1_file = file_list[i]
        R2_file = file_list[i + 1] if i + 1 < len(file_list) else None

        # Extract sample name by removing _ss_1.fastq.gz or _ss_2.fastq.gz from the R1 file name
        sample_name = R1_file["name"].replace("_ss_1.fastq.gz", "")

        # Construct the files structure for the sample
        files = [{"R1": R1_file}]
        if R2_file:
            files[0]["R2"] = R2_file

        # Append the sample structure to the samples list
        samples.append(
            {"name": sample_name, "files": files, "metadata": {"condition": ""}}
        )

    samples = {"samples": samples}

    return samples


def create_job(args: Namespace) -> None:
    file_list = parse_urls_file(args.urls_file)

    # We do this if we were getting a tarball with the input files
    # file_list = (
    #     [
    #         {
    #             "name": tar_filename,
    #             "location": args.url,
    #             "metadata": {},
    #             "type_tags": ["tar", "archive"],
    #         },
    #     ]
    #     if args.url
    #     else []
    # )
    headers = get_auth_headers()

    samplecart = create_samplecart(file_list)
    # print(json.dumps(samplecart, indent=2))
    response = requests.post(
        f"{args.api_base_url}/samplecart/", json=samplecart, headers=headers
    )

    # Check if the request was successful
    response.raise_for_status()
    response_json = response.json()
    samplecart_id = response_json.get("id")

    pipeline_run_data = {
        "pipeline": args.pipeline_name,
        "sample_cart": samplecart_id,
        "params": {
            "pipeline_version": args.pipeline_version,
            "description": args.job_description,
            "genome": args.reference_genome_id,
            "description": args.job_description,
            "fetch_files": file_list,
        },
    }

    logger.debug(pipeline_run_data)
    pipeline_run_resp = requests.post(
        f"{args.api_base_url}/pipelinerun/", json=pipeline_run_data, headers=headers
    )

    # print(pipeline_run_resp.json())
    pipeline_run_resp.raise_for_status()

    pipelinerun_id = pipeline_run_resp.json().get("id", None)

    if pipelinerun_id is None:
        logger.error("Failed to create pipelinerun")
        sys.exit(1)

    job_resp = requests.post(
        f"{args.api_base_url}/job/?pipeline_run_id={pipelinerun_id}", headers=headers
    )
    job_resp_blob = job_resp.json()
    logger.debug(job_resp_blob)
    job_resp.raise_for_status()

    job_id = job_resp_blob.get("id", None)

    job = requests.get(f"{args.api_base_url}/job/{job_id}/", headers=headers)
    job_blob = job.json()
    status = job_blob.get("status", None)

    # Poll job while running
    print(f"Job {job_id} status:", status)
    while status == "created" or status == "running":
        job = requests.get(f"{args.api_base_url}/job/{job_id}/", headers=headers)
        job_blob = job.json()
        status = job_blob.get("status", None)
        sys.stdout.write(".")
        time.sleep(10)

    print("")
    logger.info(job_blob)


def download_job(api_base_url: str, job_id: str, headers: dict) -> None:
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
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Downloaded job {job_id} to {output_filename}.")


def main():
    default_api_base_url = os.environ.get("LAXY_API_URL", "https://api.laxy.io/api/v1")

    parser = ArgumentParser(description="Interact with the Laxy API.")
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
        help="ID of the reference genome.",
    )
    job_create_parser.add_argument(
        "--urls_file",
        type=str,
        required=True,
        help="File containing URLs of input files, one per line.",
    )
    job_create_parser.set_defaults(func=create_job)

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

    # Parse the arguments
    args = parser.parse_args()

    # Call the function associated with the chosen subcommand
    if hasattr(args, "func"):
        args.func(args)
    else:
        # No subcommand was provided
        parser.print_help()


if __name__ == "__main__":
    main()
