"""Tier 2a: insert_missing_transcript.py repairs flat gene->exon/CDS rows.

Runs on the raw annotation, before drop_biotype_features/
filter_annotation_features (mirrors run_job.sh's insert_missing_transcript
bash function, which runs first). For most cases this is a documented
no-op; for E7_eukaryote_flat_pseudogene it synthesises a transcript row
for each flat single/multi-exon pseudogene, which real NCBI RefSeq
annotations use for "processed pseudogenes" (no introns, so no felt need
for an explicit transcript row) - without this, nf-core/rnaseq's own
GFF3->GTF conversion (used to build the transcript FASTA via
rsem-prepare-reference regardless of aligner choice) can't resolve
gene_id for these flat rows and the whole run dies (see
ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 8).
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="insert_transcript"), indirect=False)
def test_insert_transcript(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    env = manifest["expected"]["detect"]["env"]

    result = cl.run_insert_transcript(ann, env["ANN_FORMAT"])

    expected = manifest["expected"]["insert_transcript"]
    assert result["rc"] == expected["exit"], (
        f"insert_transcript exit {result['rc']}; stderr={result['stderr']!r}")

    for key, want in expected["counts"].items():
        got = result["counts"].get(key)
        assert got == want, (
            f"[{manifest['id']}] insert_transcript {key}: expected {want}, got {got}")
