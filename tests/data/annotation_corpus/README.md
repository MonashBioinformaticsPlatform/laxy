# Synthetic annotation corpus

A small, deterministic set of synthetic **FASTA + GTF/GFF3 + FASTQ** fixtures for
real end-to-end testing of Laxy's annotation handling: detection
(`detect_annotation_style.py`), filtering (`filter_annotation_features.py`),
the FASTA/annotation seqid pre-flight, and (optionally) a full `nf-core/rnaseq`
run.

Each fixture is **bacterial-scale** (two chromosomes, ~150 kb total) so STAR /
Salmon / HISAT2 indices build in seconds, with synthetic reads drawn from the
annotation's own feature coordinates so featureCounts and Salmon get real
counts. The corpus is designed to cover the variation seen in real-world
annotations (Ensembl, GENCODE, RefSeq, NCBI, Bakta, Prokka, SnapGene, AGAT,
broken inputs) and to make adding a new example a three-step operation.

## Layout

```
annotation_corpus/
  README.md                     this file
  conftest.py                   auto-collects cases/* -> parametrized tests
  test_annotation_detect.py     tier 1: detect_annotation_style.py
  test_annotation_filter.py     tier 2: filter_annotation_features.py
  test_annotation_seqid.py      tier 3: FASTA/annotation seqid overlap
  test_annotation_e2e.py        tier 4: nf-core/rnaseq (@e2e, slow)
  shared/
    genome.fa                   shared 2-chr synthetic genome (real ACGT)
    genome.fa.gz                gz twin (for auto-decompress tests)
    genome.fa.fai               index (hand-rolled, no samtools dep)
    generate_genome.py          regenerate genome.fa (fixed seed)
    generate_reads.py           FASTQ from genome + annotation coords
    corpus_lib.py               shared helpers (env parser, run_*, seqid)
    make_annotation_fixtures.py one-off bootstrap that writes cases/*/annotation.*
    make_manifests.py           generates cases/*/manifest.json from behaviour
  cases/
    <CASE_ID>/
      annotation.{gtf,gff3}[.gz]
      manifest.json             expected behaviour + tier + reads config
      reads/                    generated FASTQ cache (gitignored)
```

## Tiers

Each case has a `tier` in its `manifest.json` that decides which test layers run:

| tier         | detect | filter | seqid | e2e | examples                       |
|--------------|:------:|:------:|:-----:|:---:|--------------------------------|
| `happy`      | yes    | yes    | yes   | yes | E1-E5, P1-P4, P3gz, F9         |
| `repairable` | yes    | yes    | yes   | yes | F1, F2, F6, F7                 |
| `detect_only`| yes    | yes    | yes   | no  | F4, F11                        |
| `failfast`   | yes/no | no     | yes   | no  | F3 (seqid), F5 (8-col), F10 (empty) |
| `xfail`      | yes*   | no     | yes   | no  | F8 (AGAT, doc §6.1)            |

`*` The xfail case asserts the **correct** behaviour the detector *should*
produce; the current bug makes it fail (xfailed). When the detector is fixed it
xpasses, and the strict xfail turns that into a test failure — an explicit "the
bug is gone, promote this to a happy case" alert.

E5 is `happy` for detect/filter/seqid (those all behave correctly), but its
`expected.e2e.expect_success` is `false` with a `known_failure_reason` -
unlike the detector-only xfail mechanism above, nothing currently enforces
this automatically; it documents a known nf-core/rnaseq bug (doc §6 item 7)
that the real e2e runner (`run_corpus_via_laxycli.py`) will hit.

## Running

```bash
# fast tiers (detect + filter + seqid); no Django, no containers, ~1s
just test-annotation-corpus

# include read-generation sanity (generates + counts reads; no nextflow)
just test-annotation-corpus-reads

# full nf-core/rnaseq e2e (needs nextflow + fake-cluster stack up)
just test-annotation-corpus-e2e
```

Direct pytest works too:

```bash
pytest tests/data/annotation_corpus/ -m "corpus and not e2e"
```

The corpus is intentionally **not** in `pytest.ini`'s `testpaths`, so the normal
unit/integration recipes are unaffected.

## Adding a new example

1. **Drop the annotation** into a new directory:
   `cases/<CASE_ID>/annotation.{gtf,gff3}[.gz]`.

2. **Register it** in `shared/make_manifests.py` — add one line to the `META`
   table: `(tier, description, class, extra_flags)`. Choose a `tier` from the
   table above.

3. **Regenerate manifests** and run:

   ```bash
   just annotation-manifests
   just test-annotation-corpus
   ```

That's it — the parametrized tests pick up the new case automatically; no test
file edits needed. Reads (for `happy`/`repairable` tiers) generate on demand from
the annotation's feature coordinates, so there is nothing to hand-author.

### Optional: regenerate the genome

```bash
just annotation-genome    # regenerates shared/genome.fa[.gz,.fai] from the fixed seed
```

The genome is committed; only regenerate if you change chromosome sizes. Keep
the seed fixed so committed reads stay valid.

## Case catalogue

| ID                          | what it exercises                                            |
|-----------------------------|--------------------------------------------------------------|
| E1_eukaryote_ensembl        | Ensembl-style GTF (`gene_biotype`)                           |
| E2_eukaryote_gencode        | GENCODE-style GTF (`gene_type`)                              |
| E3_eukaryote_refseq         | RefSeq GFF3 gene/mRNA/exon/CDS hierarchy                     |
| E4_eukaryote_no_biotype     | eukaryotic GTF missing biotype -> `--skip_biotype_qc`        |
| E5_eukaryote_ncrna_ids      | RefSeq GFF3 mixing protein-coding + tRNA/rRNA (`ID=rna-*`); detect/filter/seqid pass but the real e2e run is a **known failure** (`expect_success: false`, see doc §6 item 7) |
| P1_prokaryote_minimal_gtf   | minimal prokaryotic CDS-only GTF                             |
| P2_prokaryote_ncbi          | NCBI GenBank GFF3 (gbkey/Dbxref/locus_tag)                   |
| P3_prokaryote_bakta         | Bakta GFF3 (flat CDS, `ID=locus_tag`)                        |
| P3gz_prokaryote_bakta_gz    | as P3 but gzip-compressed (auto-decompress)                  |
| P4_prokaryote_prokka        | Prokka GFF3 (flat CDS, `eC_number`)                          |
| F9_mixed_chromosomes        | multi-contig eukaryotic GTF                                  |
| F1_flat_snapgene            | SnapGene flat GFF3, no ID/Parent (filter stamps gene_id)     |
| F2_snapgene_variation       | SnapGene export with a stray `variation` row                 |
| F6_embedded_fasta           | GFF3 with a trailing `##FASTA` section                       |
| F7_crlf_bom                 | GTF with UTF-8 BOM + CRLF line endings                       |
| F3_seqid_mismatch           | seqids share no overlap with the FASTA (pre-flight fails)    |
| F4_seqid_mismatch_partial   | partial overlap (some contigs match)                        |
| F5_eight_columns            | only 8-column rows (no attributes column)                    |
| F8_agat_converted           | AGAT-converted prok GFF3 (detector bug, doc §6.1) -> xfail   |
| F10_empty                   | empty annotation file                                        |
| F11_mixed_format            | GTF with no biotype (format edge)                            |

## Design notes

- **One shared genome.** All annotations reference the same `chr1`/`chr2`
  coordinates, so the genome is generated once and committed. Read coordinates
  come from each annotation's features, so reads always land on counted features
  regardless of which annotation they pair with.
- **Deterministic.** Genome and reads use fixed seeds; re-running the generators
  yields identical bytes. Manifests are snapshots of actual detector/filter
  behaviour, so they catch regressions rather than encode hand-waved hopes.
- **Stdlib only.** The generators and `corpus_lib.py` use only the Python
  standard library, so they run without a venv. The detector/filter scripts they
  invoke are the real pipeline scripts (subprocess), not reimplementations.
