"""Tier 3: FASTA/annotation seqid overlap (mirrors check_fasta_annotation_seqids).

The real check is a bash function in agat_normalize_annotation.sh that runs
awk + ``comm -12``. We reproduce its seqid-extraction + overlap logic here
(clearly documented) so the corpus can assert the contract without standing up
the whole job environment. The authoritative bash path is exercised in tier 4
(e2e).
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="seqid"), indirect=False)
def test_seqid_overlap(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    assert ann is not None

    fa_ids, ann_ids, overlap = cl.seqid_overlap(cl.GENOME, ann)
    expected = manifest["expected"]["seqid"]

    if expected["expect_overlap"]:
        assert overlap, (
            f"[{manifest['id']}] expected seqid overlap but FASTA={sorted(fa_ids)} "
            f"and ann={sorted(ann_ids)} share none")
    else:
        assert not overlap, (
            f"[{manifest['id']}] expected NO overlap but shared={sorted(overlap)}")
