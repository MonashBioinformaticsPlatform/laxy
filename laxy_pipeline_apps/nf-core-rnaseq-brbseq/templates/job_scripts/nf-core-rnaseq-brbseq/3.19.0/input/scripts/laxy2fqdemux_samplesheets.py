#!/usr/bin/env python3

import sys
import os
from pathlib import Path
import json
import re
import argparse

# Attempt to import unidecode, but provide a fallback if not available
try:
    from text_unidecode import unidecode
except ImportError:
    sys.stderr.write(
        "WARNING: text_unidecode not installed, skipping unicode to ascii conversion for sample IDs.\n"
    )

    def unidecode(txt: str) -> str:
        return txt

def sanitize_identifier(identifier: str) -> str:
    """
    Sanitizes an identifier to be used as a sample_id.
    Replaces spaces and special characters with underscores, converts to lowercase.
    Uses unidecode for basic transliteration of unicode characters to ASCII.
    """
    identifier = unidecode(identifier)  # Transliterate unicode
    identifier = re.sub(r'[^a-zA-Z0-9_.-]', '_', identifier) # Replace non-alphanumeric (excluding _, ., -) with _
    identifier = re.sub(r'_+', '_', identifier) # Replace multiple underscores with single
    identifier = identifier.strip('_') # Remove leading/trailing underscores
    return identifier

def main():
    parser = argparse.ArgumentParser(
        description="Generate fqdemux samplesheets from Laxy pipeline config."
    )
    parser.add_argument("pipeline_config_json", help="Path to pipeline_config.json")
    parser.add_argument("input_reads_path", help="Path to the input reads directory")
    parser.add_argument("output_barcodes_tsv", help="Path for the output barcodes.tsv")
    parser.add_argument(
        "output_readstructures_tsv", help="Path for the output readstructures.tsv"
    )
    parser.add_argument(
        "--single-ended",
        choices=["R1", "R2"],
        default="R1",
        help="Specify the main read (R1 or R2) to be listed first in the read structures sheet. Defaults to R1.",
    )
    args = parser.parse_args()

    pipeline_config_json_path = args.pipeline_config_json
    input_reads_path = args.input_reads_path
    output_barcodes_tsv_path = args.output_barcodes_tsv
    output_readstructures_tsv_path = args.output_readstructures_tsv

    with open(pipeline_config_json_path, "r") as fh:
        jblob = json.load(fh)

    # --- Generate Barcodes Samplesheet (fqdemux_samplesheet.tsv) ---
    barcodes_data = []
    # Ensure nf-core-rnaseq-brbseq parameters exist
    pipeline_params_key = "nf-core-rnaseq-brbseq" # Default key
    if pipeline_params_key not in jblob.get("params", {}):
        # Fallback for general pipeline name if specific one not found
        pipeline_params_key = jblob.get("pipeline", "nf-core-rnaseq-brbseq")

    brbseq_params = jblob.get("params", {}).get(pipeline_params_key, {})
    barcode_entries = brbseq_params.get("barcode_samplesheet", [])

    if not barcode_entries:
        sys.stderr.write(f"WARNING: No 'barcode_samplesheet' found in {pipeline_params_key} params.\n")
    
    for entry in barcode_entries:
        sample_id_raw = ""
        sample_id_columns = ["*title", "title", "sample_id"]
        for key in sample_id_columns:
            sample_id_raw = entry.get(key, "")
            if sample_id_raw:
                break
        barcode = entry.get("barcode", "")
        if sample_id_raw and barcode:
            # Sanitize sample_id, make it a valid identifier
            sample_id = sanitize_identifier(sample_id_raw)
            barcodes_data.append(f"{sample_id}\t{barcode}")
        else:
            sys.stderr.write(f"WARNING: Skipping barcode entry due to missing '{'/'.join(sample_id_columns)}' or 'barcode': {entry}\n")

    with open(output_barcodes_tsv_path, "w") as fh:
        fh.write("sample_id\tbarcode\n")
        for line in barcodes_data:
            fh.write(line + "\n")
    sys.stderr.write(f"Generated barcode samplesheet: {output_barcodes_tsv_path}\n")


    # --- Generate Read Structures Samplesheet (fqdemux_readstructures.tsv) ---
    r1_reads = []
    r2_reads = []
    read_structures_map = brbseq_params.get("readstructure", {})

    if not read_structures_map:
        sys.stderr.write(f"WARNING: No 'readstructure' map found in {pipeline_params_key} params.\n")

    # Use fetch_files as the source of truth for actual file names and R1/R2 designation
    fetch_files = jblob.get("params", {}).get("fetch_files", [])
    if not fetch_files:
         sys.stderr.write("WARNING: No 'fetch_files' found in params. Read structure sheet might be empty or incomplete.\n")

    for file_info in fetch_files:
        file_name_only = file_info.get("name")
        # Ensure type_tags indicate it's an ngs_reads file before processing
        if "ngs_reads" not in file_info.get("type_tags", []):
            continue

        if not file_name_only:
            sys.stderr.write(f"WARNING: Skipping file_info due to missing 'name': {file_info}\n")
            continue

        full_file_path = os.path.join(input_reads_path, file_name_only)
        
        read_pair_type = file_info.get("metadata", {}).get("read_pair") # Should be "R1" or "R2"
        
        if not read_pair_type:
            # Try to infer from filename if metadata is missing (less reliable)
            if "_R1" in file_name_only or "_1" in file_name_only:
                read_pair_type = "R1"
            elif "_R2" in file_name_only or "_2" in file_name_only:
                read_pair_type = "R2"
            else:
                sys.stderr.write(f"WARNING: Skipping file '{file_name_only}' as 'read_pair' metadata is missing and cannot be inferred.\n")
                continue
        
        current_read_structure = read_structures_map.get(read_pair_type)

        if current_read_structure:
            line = f"{full_file_path}\t{current_read_structure}"
            if read_pair_type == "R1":
                r1_reads.append(line)
            elif read_pair_type == "R2":
                r2_reads.append(line)
        else:
            sys.stderr.write(f"WARNING: No read structure found for read type '{read_pair_type}' (file: {file_name_only}).\n")
            
    # Sort reads to ensure deterministic order before combining
    r1_reads.sort()
    r2_reads.sort()

    if args.single_ended == "R1":
        readstructures_data = r1_reads + r2_reads
    else: # main read is R2
        readstructures_data = r2_reads + r1_reads
        
    with open(output_readstructures_tsv_path, "w") as fh:
        fh.write("filename\tread_structure\n")
        for line in readstructures_data:
            fh.write(line + "\n")
    sys.stderr.write(f"Generated readstructure samplesheet: {output_readstructures_tsv_path}\n")

if __name__ == "__main__":
    main() 