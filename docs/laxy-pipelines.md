# Laxy pipeline wrappers

This document describes how Laxy's pipeline wrappers (Django `laxy_pipeline_apps/*`
+ the Jinja2-templated `run_job.sh`/scripts rendered into each job) drive the
underlying bioinformatics pipelines. It is a map to help you navigate the code,
not a specification.

> **Source of truth.** The version-specific upstream pipeline docs (e.g.
> `https://nf-co.re/rnaseq/<version>/docs`) and the actual scripts preserved in
> a completed job's own `input/scripts/` folder are the ultimate source of
> truth for what a given job actually did. Flags, defaults, and even directory
> layouts change between pipeline releases; this document describes the
> *current* `default`/`3.18.0`-era behaviour and the general shape of the
> wrapper, but a specific job's rendered `run_job.sh`, `pipeline_config.json`,
> `annotation_style.env`, and `nextflow.log` in its own `input`/`output`
> folders always win over what's written here.

## nf-core/rnaseq

Code: `laxy_pipeline_apps/nf-core-rnaseq/templates/`
(`common/` = shared scripts used by every pipeline version;
`job_scripts/nf-core-rnaseq/<version>/` = per-version `run_job.sh`, conda env,
and nextflow configs).

| Laxy `pipeline_version` | nf-core/rnaseq revision | nf-core/tools (CLI) |
|---|---|---|
| `3.10.1` | `3.10.1` | 2.10 |
| `3.12.0` | `3.12.0` | 2.10 |
| `3.18.0` | `3.18.0` | 3.3.1 |
| `default` | *(see caveat below)* | 2.10 |

**Caveat - `default` is currently broken for a fresh pipeline cache.**
`NFCORE_PIPELINE_RELEASE` is templated directly from the laxy
`pipeline_version` string, and for the `default` template folder that string
is the literal word `"default"` - not a real nf-core/rnaseq git tag. `nf-core
download` only succeeds today because most compute resources already have a
pre-cached `nf-core-rnaseq-default` pipeline directory from before this was
ever exercised fresh; on a compute resource that has never run it,
`cache_pipeline()` fails outright with `Not able to find revision / branch
'default' for nf-core/rnaseq` (confirmed this way on `laxy-compute-01` and
`m3-login2-rocky9`). Until `NFCORE_PIPELINE_RELEASE` is fixed for this
template (e.g. hardcode the intended real revision instead of the Jinja2
`{{ PIPELINE_VERSION }}` substitution), prefer an explicit numbered
`pipeline_version` for anything that might need a fresh pipeline cache.

### 1. Annotation pre-processing

Only runs when a custom reference (`user_genome.fasta_url` /
`annotation_url`, or an uploaded `fetch_files` genome+annotation pair) is
used - `USING_CUSTOM_REFERENCE=yes`. Built-in iGenomes references skip all of
this and go straight to nf-core/rnaseq with `--genome <ID>`.

Order of operations (`normalize_annotations()` in `run_job.sh`):

| Step | Script | What it does |
|---|---|---|
| 1 | `check_fasta_annotation_seqids` (`agat_normalize_annotation.sh`) | Fails fast if the FASTA and annotation share no sequence ids (would otherwise silently produce an empty GTF ~10 min into the nextflow run). |
| 2 | `detect_annotation_style.py` | Sniffs GTF vs GFF3, picks the feature type to count (`exon`/`CDS`), the grouping attribute, extra attributes, biotype attribute, prokaryote/eukaryote classification, and any `--skip_*` flags. Writes `annotation_style.env` (sourced into `ANN_*` shell vars). |
| 3 | `insert_missing_transcript()` (GFF3 only) | Repairs genes whose children (exon/CDS/UTRs) point `Parent=` directly at the gene with no transcript/mRNA/tRNA/... row in between (real single-exon "processed pseudogenes" in NCBI RefSeq). Synthesises the missing transcript row. Re-runs step 2 afterwards. |
| 4 | `drop_biotype_features()` | Drops whole gene groups whose biotype is in `ANN_DROP_BIOTYPES` - only set when non-coding RNA biotypes (tRNA/rRNA/ncRNA/...) are found *and* no transcript-level row anywhere in the file has a `transcript_id`-equivalent attribute (isolated organelle genomes). Re-runs step 2 afterwards. |
| 5 | `filter_annotation_features()` (prokaryotic only, `ANN_PROKARYOTIC=yes`) | Trims to a single feature type (usually `CDS`) and synthesises a `transcript`/`exon`/`<feature_type>` GTF hierarchy per row, always as GTF output. |

Steps 3-5 are individually gated (each is a no-op if its precondition isn't
met) and are safe to reason about independently, but they run in this order
because each can change what the *next* step's re-detection sees.

#### Which biotypes survive - by input shape

| Input shape | protein_coding | lncRNA / other ncRNA *with* `transcript_id` | tRNA/rRNA/ncRNA *without* `transcript_id` (isolated organelle genomes) | Pseudogenes (flat, no transcript row) | Overall |
|---|---|---|---|---|---|
| Ensembl/GENCODE **GTF** | preserved | preserved | n/a (GTF rows always carry their own id) | preserved (already has a transcript row) | Nothing dropped - GTF is passed through unmodified. |
| RefSeq-style **GFF3**, nuclear/whole-genome | preserved | preserved | preserved (each real gene usually has *some* row elsewhere in the file with `transcript_id`, so the file-wide check in step 4 doesn't fire) | preserved (repaired by step 3) | Verified against real whole-chromosome/whole-genome human & mouse RefSeq annotations - all biotype categories (protein_coding, lncRNA, pseudogene subtypes, snRNA, miRNA, IG genes, ...) show up with real counts. |
| RefSeq-style **GFF3**, isolated organelle genome (e.g. mitochondrial-only) | preserved | preserved (if it has `transcript_id`) | **dropped entirely** (step 4) | preserved (repaired by step 3) | Dropping is deliberate: without it, Salmon quantifies a transcript per group with no matching tx2gene entry and tximport dies for the *whole sample*, not just the ncRNA genes. |
| Prokaryotic (NCBI GenBank, Bakta, Prokka, generic, SnapGene) | preserved (if `ANN_FEATURE_TYPE` picked is `CDS`, which it almost always is) | **dropped** | **dropped** | n/a | `filter_annotation_features.py` keeps **only** rows matching the single detected feature type (`CDS` in practice). tRNA/rRNA/ncRNA gene rows are typically a distinct feature type in column 3 (`tRNA`, `rRNA`, ...) and are silently excluded - not counted, not reported anywhere. This is a real, current limitation of the prokaryotic path, not a bug per se (the path was built for CDS-focused bacterial RNA-seq), but it means non-coding bacterial RNA genes are invisible in the final counts regardless of how they're annotated upstream. |

**Practical implication:** for a prokaryotic sample where tRNA/rRNA
quantification actually matters (rare, but not unheard of - e.g. some
ncRNA-focused studies), the current pipeline wrapper will not report those
genes at all. There's no flag to opt out of this; it would need
`filter_annotation_features.py` to be extended to keep more than one feature
type.

### 2. nf-core/rnaseq invocation

`run_nextflow()` always runs (attempt 1, then a `-resume` retry on failure)
with this shape:

```
nextflow run <pipeline_path> \
  --input samplesheet.csv --outdir output/results \
  <GENOME_ARGS> <UMI_FLAGS> <MIN_MAPPED_READS_ARG> <EXTRA_FLAGS> <ANNOTATION_FLAGS> <TRIMMER_ARGS> \
  --aligner star_salmon --pseudo_aligner salmon \
  --save_reference --monochrome_logs \
  -with-trace -with-dag -name <job> \
  -c laxy_nextflow.config [-c <site nextflow.config>] \
  -profile apptainer
```

`--aligner star_salmon` and `--pseudo_aligner salmon` are always both passed -
note these share nf-core/rnaseq's *same* underlying quantification
subworkflow (`QUANTIFY_PSEUDO_ALIGNMENT`, aliased as `QUANTIFY_STAR_SALMON`),
so any annotation-shape issue that breaks one breaks both.

`<GENOME_ARGS>` is either `--genome <iGenomes ID>` (built-in reference) or
`--fasta ... --gtf .../--gff ...` (custom reference, `--gtf` vs `--gff`
decided by `ANN_FORMAT` after pre-processing).

#### Advanced options -> flags

These come from `pipeline_config.json`'s `params.nf-core-rnaseq.*` (set via
the frontend's "advanced options", defaults shown):

| Option (default) | Flag(s) added |
|---|---|
| `has_umi: false` | `--with_umi --skip_umi_extract --umitools_umi_separator :` (only when `true`) |
| `skip_trimming: false` | `--skip_trimming` (only when `true`) |
| `trimmer: "fastp"` | `fastp`: `--trimmer fastp --extra_fastp_args "--trim_poly_g --trim_poly_x"`. `trimgalore`: `--trimmer trimgalore`. Anything else: no trimmer flag added (nf-core's own default applies). |
| `min_mapped_reads: 5` | `--min_mapped_reads <N>` - always passed. **Caveat:** this gates nf-core/rnaseq's own per-sample QC skip (based on the auto-strandedness pseudo-alignment subsample, not the full read set). Too low a value doesn't guarantee the sample won't be skipped; too high a value on genuinely small/synthetic test data can trigger a skip. A "complete" job with a skipped sample still exits 0 and reports "Pipeline completed successfully with skipped sample(s)" in `nextflow.log` - **check for this string**, since none of the downstream `star_salmon`/`featureCounts` outputs exist in that case, and the job's own status alone doesn't tell you this happened. **This is not the only such gate** - see `min_trimmed_reads` below, a separate, independent skip applied right after trimming. |
| `min_trimmed_reads` (not exposed in the UI; nf-core default 10000) | `--min_trimmed_reads <N>` - passed whenever set in `pipeline_config.json`, otherwise omitted (nf-core's own default of 10000 applies unchanged). A **separate** skip-gate from `min_mapped_reads`, checked immediately after trimming and before alignment, against the *actual* trimmed-read count (not an auto-strandedness subsample). Synthetic/small test data easily falls under nf-core's default of 10000 total trimmed reads and gets silently filtered here even with `min_mapped_reads: 0`. |
| `strandedness: "auto"` | Not a nextflow flag - written into `samplesheet.csv` per-sample by `laxy2nfcore_samplesheet.py`. `auto` lets nf-core infer it from a Salmon pseudo-alignment subsample. |
| `debug_mode: false` | Not a pipeline flag - controls whether `output/work` and `.nextflow` are cleaned up after the job (kept when `true`). |
| `save_genome_index: false` | Not a pipeline flag - controls whether `output/results/genome/index` is kept after the job. |
| `save_reference_genome: true` | Not a pipeline flag - controls whether `output/results/genome` is kept after the job. Needed for the featureCounts post-processing step to find the filtered GTF as a fallback annotation source. |

Annotation-derived flags (`ANNOTATION_FLAGS`, see §1) are always added and
aren't user-configurable:
`--featurecounts_feature_type`, `--gtf_group_features`,
`--gtf_extra_attributes` (if any), `--featurecounts_group_type` (if a biotype
attribute was resolved), plus any `ANN_SKIP_FLAGS` (`--skip_biotype_qc`,
`--skip_rseqc --skip_qualimap --skip_bigwig --skip_dupradar` for CDS-only
prokaryotic input, `--skip_dupradar` alone for other prokaryotic input).

**GFF3-specific flag forcing.** nf-core/rnaseq's own `PREPARE_GENOME`
converts a `--gff` input to GTF via `gffread` internally. `gffread` always
synthesises `gene_id`/`transcript_id` from `ID=`/`Parent=`, and does **not**
preserve the original GFF3's `gene_biotype` attribute anywhere (`gbkey`, the
GenBank feature key, survives only on the `transcript`/`mRNA`-level row, not
on the `exon`/`CDS` rows nf-core's own internal biotype-QC featureCounts run
actually reads). Because of this:

- `--gtf_group_features` is forced to `gene_id` whenever `ANN_FORMAT=gff3`,
  regardless of what `detect_annotation_style.py` picked for our own
  pre-processing (e.g. `Parent`). Passing the raw detected value straight to
  nf-core here breaks `CUSTOM_TX2GENE`/Salmon tximport outright.
- `--featurecounts_group_type` is forced to `gbkey` whenever `ANN_FORMAT=gff3`
  and the detected biotype attribute was `gene_biotype`, **and**
  `--skip_biotype_qc` is added alongside it. Without the forcing, nf-core's
  own internal `SUBREAD_FEATURECOUNTS` biotype QC step fails outright with
  `failed to find the gene identifier attribute in the 9th column` (the raw
  `gene_biotype` attribute name isn't in the gffread-converted GTF at all).
  Forcing to `gbkey` alone isn't sufficient either, though: that step counts
  at the `exon`/`CDS` level, and `gbkey` isn't present there (see above), so
  it fails with the same error regardless - `--skip_biotype_qc` is required
  to avoid a hard pipeline failure. Confirmed via a corpus e2e run
  (`E3_eukaryote_refseq`) that failed with exactly this error before
  `--skip_biotype_qc` was added.

This means nf-core's *own* internal biotype QC plot (MultiQC "Biotype
Counts") is skipped entirely for GFF3 input - our own featureCounts
post-processing (§3 below) computes real biotypes independently and
tolerates a missing attribute gracefully (empty column, not a crash). For
GTF input (Ensembl/GENCODE),
`gene_biotype`/`gene_type` is repeated on every row including exon/CDS (GTF
convention), so no forcing is needed and the QC plot shows real biotypes.

### 3. Post-processing: featureCounts

After nf-core/rnaseq finishes, `post_nextflow_pipeline()` runs a second,
separate nextflow script (`featurecounts_postnfcore.nf`) that re-runs
featureCounts directly against the STAR BAMs, independent of nf-core's own
internal `SUBREAD_FEATURECOUNTS` step. This exists to attach the
Laxy-preferred set of extra columns/attributes and merge the result into the
Salmon-based gene counts table.

The annotation file used is whichever survived our own pre-processing
(`ANNOTATION_FILE` after steps 3-5 above), falling back to nf-core's
published `*.filtered.gtf(.gz)` if we don't have one. **This is a different
file, with a different grouping attribute, from what nf-core's own internal
quantification used** - see the bug below.

The actual `featureCounts` command (`FEATURECOUNTS` process):

```
featureCounts \
  -a "<annotation>" \
  -t <ANN_FEATURE_TYPE> \
  -g <ANN_GROUP_FEATURES> \
  [--extraAttributes <ANN_EXTRA_ATTRIBUTES>,<ANN_BIOTYPE_ATTR>] \
  -o "<sample>.counts.star_featureCounts.txt" \
  -T <cpus> [-p] -B -C -Q 10 \
  -s <strandedness inferred from Salmon meta_info.json> \
  <sample>.markdup.sorted.bam
```

`-s` (strandedness) is inferred per-run from the Salmon
`aux_info/meta_info.json` (`GET_SALMON_INFERRED_STRANDEDNESS`), not
re-derived independently. `--extraAttributes` only reports a value for an
attribute if it's present on the actual counted row (the `-t` feature type) -
see the bug below for why this matters.

Per-sample counts are merged (`merge_featurecounts.py`) into
`featureCounts/counts.star_featureCounts.tsv`, then merged into the Salmon
gene-count tables (`merge_biotypes.py`, `SALMON_COUNTS_ADD_BIOTYPES`) to
produce `salmon.merged.gene_counts{,_scaled,_length_scaled}.biotypes.tsv`
under both `results/salmon/` and `results/star_salmon/`.

#### Fixed: biotype merge was broken for GFF3 (RefSeq-style) input

Confirmed against a real whole-genome NCBI RefSeq mouse run
(`4KlXdBOO5hTDvvr99m2bIp`). Root cause was an **id-namespace mismatch**:

- nf-core's own Salmon quantification is forced to group by `gene_id` for
  GFF3 input (§2), so `salmon.merged.gene_counts.tsv`'s `gene_id` column
  holds gene-level ids like `gene-0610005C13Rik`.
- Our own `featurecounts_postnfcore.nf` grouped by the *originally detected*
  `ANN_GROUP_FEATURES` (typically `Parent` for RefSeq GFF3, **not** forced to
  `gene_id`), so its `Geneid` column held transcript/rna-level ids like
  `rna-XR_004936710.1`.
- `merge_biotypes.py` left-joins on `nfcore_counts.gene_id ==
  featurecounts.Geneid`. These two id sets never overlapped for GFF3 input,
  so every row's `gene_biotype` *and* `chromosome` column came back empty in
  the merged `.biotypes.tsv` output - even though the underlying gene-level
  counts themselves (`salmon.merged.gene_counts.tsv`, no `.biotypes` suffix)
  were completely unaffected and correct.
- Separately, `-t exon --extraAttributes gene_biotype` against a RefSeq GFF3
  also produced an empty column on its own merits (before the id mismatch
  even mattered): `gene_biotype` lives only on the `gene` row in RefSeq GFF3,
  never on the `exon`/`CDS` rows featureCounts actually reads. (For GTF input
  this is a non-issue since Ensembl/GENCODE GTF repeats `gene_biotype` on
  every row.)

**Fix (part 1 - id namespace)**: for GFF3 input, `post_nextflow_pipeline()` now runs
`featurecounts_postnfcore.nf`'s featureCounts against nf-core's own
gffread-converted `*.filtered.gtf` (published under `results/genome/`
whenever `save_reference` is set, which is always the case) instead of the
pre-conversion `ANNOTATION_FILE`, grouped by `gene_id` with `gene_name` as
the extra attribute and `gbkey` as the biotype attribute - matching the
namespace and attributes nf-core's own gffread conversion produces (see §2).
Applied identically across `3.10.1`, `3.12.0`, `3.18.0`/`default` and
`nf-core-rnaseq-brbseq/3.19.0`. GTF and prokaryotic paths are unaffected
(unchanged pre-fix behaviour).

This alone was **not sufficient** - confirmed via a live corpus e2e run
(`E3_eukaryote_refseq`), which surfaced two further, previously-undiscovered
bugs once the id-namespace fix let the pipeline actually reach this stage
for the first time (it had always previously died earlier, on the read-pair
orientation bug described in the testing-methodology caveat below):

**Fix (part 2 - nf-core's own internal biotype QC crashes outright)**:
nf-core's own `SUBREAD_FEATURECOUNTS` (its internal biotype-QC step, distinct
from Laxy's `featurecounts_postnfcore.nf`) counts at the `exon`/`CDS` level,
but `gbkey` (forced via `--featurecounts_group_type`, see §2) only survives
gffread's conversion on the `transcript` row - never on `exon`/`CDS` rows.
`featureCounts -g gbkey -t exon` then fails outright with `failed to find the
gene identifier attribute in the 9th column`, killing the *entire* pipeline
run (exit 255) rather than just producing an empty QC plot.
`normalize_annotations()` now adds `--skip_biotype_qc` whenever the GFF3
`gbkey` forcing applies (all four `run_job.sh` variants), which is why the
"nf-core's own internal biotype QC" column below now reads "skipped" for
GFF3 rather than a value.

**Fix (part 3 - the biotype column itself was silently empty)**: even after
part 2, `featurecounts_postnfcore.nf`'s *own* featureCounts run
(`--extraAttributes gene_name,gbkey`) had the identical problem: it also
counts at the `exon`/`CDS` level, so its `gbkey` column came back **empty**
for every gene, not merely absent from a crash. Confirmed directly against
`counts.star_featureCounts.tsv` from a completed GFF3 job. Two changes fix
this:
- A new script, `propagate_biotype_to_features.py` (in `templates/common`,
  symlinked into every version's `input/scripts/`), copies the biotype
  attribute value from each `transcript` row down onto its child rows before
  featureCounts runs, whenever the GFF3 `gbkey` forcing applies. Produces
  `genome.filtered.with_biotype.gtf` alongside the original.
- `merge_biotypes.py` previously hardcoded the column name `"gene_biotype"`
  when deciding whether to carry a biotype column through - for GFF3 the
  actual column is named `gbkey`, so the check silently dropped it even once
  populated. It now takes the real attribute name as an optional third
  argument (`featurecounts_postnfcore.nf` passes `params.biotype_attr`) and
  renames that column to `gene_biotype` in the merged output; GTF callers
  (no third argument, defaults to `"gene_biotype"`) are unaffected.

Confirmed end-to-end against a completed corpus e2e job
(`E3_eukaryote_refseq`, job `7mbz0c3OwY29msvjiMyhBW`):
`salmon.merged.gene_counts.biotypes.tsv` now has a real, populated
`gene_biotype` column (`mRNA`, from the source GFF3's `gbkey` value) for
every gene, alongside the correct `chromosome` column from the part 1 fix.

**Known follow-up gap (not addressed here):** the same job's `gene_name`
column is empty. `post_nextflow_pipeline()`'s comment claims gffread
synthesises a `gene_name` attribute in place of GFF3's `Name` - not observed
in practice against this gffread version's `*.filtered.gtf`, which carries
`Name` (uppercase), not `gene_name`. Cosmetic only (`gene_id` is always
present and unique), left for a future session.

#### Summary: what's usable per input shape

| Input shape | `salmon.merged.gene_counts.tsv` (Salmon/tximport) | `featureCounts/counts.star_featureCounts.tsv` (our own alignment-based counts) | `*.biotypes.tsv` (merged) | nf-core's own internal biotype QC (MultiQC) |
|---|---|---|---|---|
| Ensembl/GENCODE GTF | correct | correct | correct, real biotypes | correct, real biotypes |
| RefSeq GFF3 (eukaryotic) | correct | correct (grouping now matches the Salmon table for GFF3, see fix above) | fixed, confirmed via live corpus e2e run - real `gbkey` values populated, renamed to `gene_biotype` | skipped (`--skip_biotype_qc`) - forcing `gbkey` as the group attribute alone still crashed this step outright (see fix part 2) |
| Prokaryotic (any source) | correct (only the single retained feature type) | correct | correct - `filter_annotation_features.py` synthesises `gene_id` consistently on both sides | correct |

### Testing methodology caveat

The synthetic annotation corpus's e2e runners
(`tests/data/annotation_corpus/run_corpus_via_laxycli.py` and
`submit_corpus_job.py`) originally hard-coded `min_mapped_reads: 5`. On at
least one real run of the full corpus against laxy-dev, **every** case's
`nextflow.log` showed `Pipeline completed successfully with skipped
sample(s)` - meaning nf-core/rnaseq's own QC gate skipped the sample before
reaching `star_salmon`/featureCounts, and the runner's "17/17 complete"
result reflected the pipeline not crashing during pre-processing/startup,
not that alignment/quantification/featureCounts actually ran.

Root cause turned out to be a genuine bug in the corpus's synthetic read
generator (`tests/data/annotation_corpus/shared/generate_reads.py`), not the
gate itself: for `+`-strand features the read pair generator emitted two
same-orientation forward-strand reads (R2 was never reverse-complemented),
and for `-`-strand features it applied an erroneous extra reverse-complement.
Neither is a valid inward-facing ("FR") pair, which STAR cannot align - every
corpus sample mapped at 0% regardless of annotation format, correctly
tripping `min_mapped_reads` (and, when that gate was disabled to see further,
starving `SALMON_QUANT` of usable input and causing it to crash outright).
This was confirmed locally with nf-core/rnaseq's own STAR container: the
buggy reads gave 0.00% uniquely mapped / 100% "unmapped: too short"
regardless of `--genomeSAindexNbases`, while reads regenerated with the fixed
pairing logic gave 100.00% uniquely mapped, confirmed across eukaryotic GTF,
eukaryotic GFF3, and prokaryotic cases.

With `generate_reads.py` fixed and all 17 e2e cases' reads regenerated,
`min_mapped_reads` is back at the production/UI default of `5` in both
runners - real corpus samples now clear it comfortably, so the gate no
longer needs bypassing. `min_trimmed_reads: 0` remains as a deliberate
override (a separate gate, keyed on absolute trimmed-read count; the
corpus's small synthetic read sets are intentionally kept small for fast e2e
runs and fall under nf-core's default of 10000 on that basis alone).

The whole-chromosome/whole-genome real-data verification done separately
(real human chr21, mouse chr19, whole mouse genome NCBI/Ensembl jobs) remains
the stronger evidence for the biotype-preservation claims in this document,
but the corpus e2e suite now also exercises `star_salmon`/featureCounts
properly rather than being a pre-processing-only smoke test - confirmed with
live jobs against `dev-api.laxy.io` for `E1_eukaryote_ensembl` (GTF),
`P1_prokaryote_minimal_gtf` (prokaryotic) and `E3_eukaryote_refseq` (GFF3),
all three completing successfully with correct counts and (for the GFF3
case) populated biotypes, after the fixes described above.
