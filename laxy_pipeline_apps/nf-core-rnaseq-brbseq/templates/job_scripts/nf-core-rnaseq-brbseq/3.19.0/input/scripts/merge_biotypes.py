#!/usr/bin/env python3
"""
Merge a featureCounts table with gene_biotype (when present) and an nf-core/rnaseq Salmon counts
table, output a new version of the Salmon counts with biotypes.

Usage:

./merge_biotypes.py featureCounts_counts.tsv salmon_counts.tsv >salmon_counts.biotypes.tsv

"""

import sys

import pandas as pd

featurecounts_fn = sys.argv[1]
nfcore_counts_fn = sys.argv[2]

featurecounts = pd.read_table(featurecounts_fn)
base_cols = ["Geneid", "Chr"]
if "gene_biotype" in featurecounts.columns:
    base_cols.append("gene_biotype")
featurecounts = featurecounts[base_cols]
nfcore_counts = pd.read_table(nfcore_counts_fn)

df = nfcore_counts.merge(
    featurecounts, how="left", left_on="gene_id", right_on="Geneid"
)

df.drop(columns=["Geneid"], inplace=True)
df = df.rename(columns={"Chr": "chromosome"})

cols = df.columns.tolist()
if "gene_biotype" in cols:
    col_order = ["gene_id", "gene_name", "chromosome", "gene_biotype"]
else:
    col_order = ["gene_id", "gene_name", "chromosome"]
new_cols = col_order + [col for col in cols if col not in col_order]
df = df[new_cols]

df.to_csv(sys.stdout, index=False, sep="\t")
