#!/usr/bin/env python3
"""
Merge a featureCounts table with gene_biotype (when present) and an nf-core/rnaseq Salmon counts
table, output a new version of the Salmon counts with biotypes.

Usage:

./merge_biotypes.py featureCounts_counts.tsv salmon_counts.tsv [biotype_attr] >salmon_counts.biotypes.tsv

``biotype_attr`` names the featureCounts extraAttributes column actually holding
the biotype (eg "gbkey" for GFF3-origin input, where featureCounts is invoked
with ``--biotype_attr gbkey`` rather than the GTF-convention "gene_biotype" -
see run_job.sh's post_nextflow_pipeline()). Defaults to "gene_biotype" so
existing GTF-input callers are unaffected. The output column is always named
"gene_biotype" regardless of the source attribute name.
"""

import sys

import pandas as pd

featurecounts_fn = sys.argv[1]
nfcore_counts_fn = sys.argv[2]
biotype_attr = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else "gene_biotype"

featurecounts = pd.read_table(featurecounts_fn)
base_cols = ["Geneid", "Chr"]
if biotype_attr in featurecounts.columns:
    if biotype_attr != "gene_biotype":
        featurecounts = featurecounts.rename(columns={biotype_attr: "gene_biotype"})
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
