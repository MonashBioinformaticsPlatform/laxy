#!/usr/bin/env python
from typing import List, Tuple
import sys
import os
import argparse
import json
import pandas as pd


def cleanup_featurecounts(df, check_chr_boundries=True):
    """
    Takes a DataFrame of typical featureCounts output an collapses all the ';' stuffed
    fields (Chr, Start, End, Strand) into single values. Start and End then represent
    the 5' and 3' ends of the first/last exon respectively.

    If `check_chr_boundries` is `True`, skips processing if any transcipt is split
    over chromosomes (eg drafty genome assembly).

    """
    all_same_chr = df["Chr"].apply(lambda x: len(set(x.split(";"))) == 1)

    if check_chr_boundries and not all(all_same_chr):
        return df

    # Split the "Chr" column by ';' and keep only the first value
    df["Chr"] = df["Chr"].str.split(";").str[0]

    # Split the "Start" column by ';' and keep only the first value
    df["Start"] = df["Start"].str.split(";").str[0]

    # Split the "End" column by ';' and keep only the last value
    df["End"] = df["End"].str.split(";").str[-1]

    # Split the "Strand" column by ';' and keep only the first value
    df["Strand"] = df["Strand"].str.split(";").str[0]

    return df


def merge_dataframes(sample_names: List[str], file_paths: List[str]) -> pd.DataFrame:
    df = pd.read_csv(file_paths[0], sep="\t", skiprows=1)
    df.rename(columns={df.columns[-1]: sample_names[0]}, inplace=True)

    for sample_name, file_path in zip(sample_names[1:], file_paths[1:]):
        temp_df = pd.read_csv(file_path, sep="\t", skiprows=1)
        temp_df.rename(columns={temp_df.columns[-1]: sample_name}, inplace=True)
        temp_df = temp_df.iloc[:, [0, -1]]
        df = pd.merge(df, temp_df, on="Geneid", how="left")

    return df


def parse_json_input(json_str: str) -> Tuple[List[str], List[str]]:
    try:
        counts_files = json.loads(json_str)
        if not all(isinstance(pair, list) and len(pair) == 2 for pair in counts_files):
            raise ValueError(
                "JSON input should be a list of [sample_name, file_path] pairs."
            )
        sample_names = [f[0] for f in counts_files]
        file_paths = [f[1] for f in counts_files]
        return sample_names, file_paths
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON input: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process featureCounts files, merges them and cleans up sample names. "
        "Writes merged TSV to stdout."
    )
    parser.add_argument(
        "file_paths",
        nargs="*",
        help="Optional paths to the featureCounts files to process.",
    )
    parser.add_argument(
        "--check-chr-boundries",
        action="store_true",
        help="Skip processing if any transcript is split over chromosomes",
    )
    parser.add_argument(
        "--json", help="A JSON string listing [[sample_name, counts.txt], ...] pairs"
    )
    args = parser.parse_args()

    # Groovy list as string to Python list
    # file_paths = "${counts_files}"[1:-1].replace(' ', '').split(',')

    # (we just pass in a JSON string prepared in Nextflow/Groovy via JsonOutput.toJson)
    if args.json:
        sample_names, file_paths = parse_json_input(args.json)
    elif args.file_paths:
        file_paths = args.file_paths
        sample_names = [os.path.basename(f.split(".", 1)[0]) for f in file_paths]
    else:
        parser.error(
            "No input files provided. Use either positional arguments or --json option."
        )

    df = merge_dataframes(sample_names, file_paths)
    df = cleanup_featurecounts(df, check_chr_boundries=args.check_chr_boundries)

    gene_info_cols = df.columns[:8]
    sorted_count_cols = sorted(df.columns[8:])
    new_col_order = list(gene_info_cols) + sorted_count_cols
    df = df[new_col_order]

    df.to_csv(sys.stdout, sep="\t", index=False)
