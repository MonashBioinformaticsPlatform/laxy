# NCBI real mitochondrial genome smoke test fixtures

Small (~16.5kb), genuine NCBI RefSeq FASTA + GFF3 for the human and mouse
mitochondrial genomes, fetched directly via NCBI eutils `efetch`:

- Human: `NC_012920.1` (Homo sapiens mitochondrion, complete genome)
- Mouse: `NC_005089.1` (Mus musculus mitochondrion, complete genome)

Used to run a real end-to-end nf-core/rnaseq job against prod Laxy with a
genuine small real-world SRA RNA-seq dataset and unmodified NCBI RefSeq
annotation, to validate annotation handling against authentic NCBI GFF3
quirks (not just the synthetic corpus fixtures in `annotation_corpus/`).

Hosted here (rather than fetched live from NCBI eutils at job time) because
NCBI eutils' `efetch.fcgi` doesn't support `HEAD` requests properly (returns
405 with an unrelated Content-Length), which trips up laxydl's
download-size verification. See the `laxy_downloader/core.py` fix for the
underlying bug.

## `realistic/` (3Mb chromosome slices) - superseded by whole-chromosome testing

`realistic/human_chr21_3mb.fa`/`.gff3` and `realistic/mouse_chr19_3mb.fa`/`.gff3`
are 3Mb slices of real NCBI RefSeq chr21/chr19, used to test annotation
handling against real gene density/structure at a size practical to commit
to git and serve via CDN.

**This slice size caused a misleading failure that looked like a pipeline
bug but wasn't one.** A job using the human chr21 3Mb slice consistently
failed at `QUANTIFY_STAR_SALMON:SALMON_QUANT` with a non-descript crash.
Investigation traced it to real whole-genome-scale reads (`ERR11181611`)
mapped against an artificially tiny 3Mb reference, producing pathological
STAR alignment stats (1.07% uniquely mapped, 43,256 secondary vs 20,807
primary alignments) that triggered a separate, unrelated Salmon issue - not
a regression in annotation handling.

This was confirmed by re-running against the **whole** chr21 (46.7Mb) and
chr19 (61.4Mb) chromosomes (fetched directly via NCBI eutils, not
committed here due to size - 14-62MB per file), which both completed
successfully with real non-zero gene counts. See
`ANNOTATION_REQUIREMENTS_AND_FILTERING.md` §6 item 9 for the full
writeup and the annotation-handling fixes this also verified.

**Takeaway:** the `realistic/` 3Mb slices remain useful for testing
annotation *detection and filtering* (real gene density/structure), but
are not reliable for testing alignment/quantification correctness -
use whole-chromosome data (or reads subsampled to a realistic depth for
the slice size) for that.
