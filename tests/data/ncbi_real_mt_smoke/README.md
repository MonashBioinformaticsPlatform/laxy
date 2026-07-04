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
