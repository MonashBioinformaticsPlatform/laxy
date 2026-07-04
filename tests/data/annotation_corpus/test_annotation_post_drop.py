"""Tier 2c: the full detect -> drop -> re-detect -> filter chain.

Only exercised for cases where the detector actually finds ANN_DROP_BIOTYPES.
Mirrors run_job.sh's drop_biotype_features bash function calling
detect_annotation_style.py a second time on the stripped annotation, then
filter_annotation_features using that fresh env - this is what makes real
mitochondrial-shaped annotations (CDS-only protein-coding genes, exon-bearing
tRNA/rRNA genes) work: dropping the non-coding RNA genes leaves zero exon
rows, so the remainder must be reclassified as CDS-only/prokaryotic-shaped
rather than handed to STAR as a GTF with no exon lines (see
ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7).
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="post_drop"), indirect=False)
def test_post_drop_chain(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    det_env = manifest["expected"]["detect"]["env"]
    expected = manifest["expected"]["post_drop"]

    chain = cl.run_post_drop_chain(ann, det_env["ANN_FORMAT"], det_env["ANN_DROP_BIOTYPES"])

    assert chain["redetect"] is not None, "re-detect after drop failed to run"
    assert chain["redetect"]["rc"] == 0, (
        f"re-detect exit {chain['redetect']['rc']}; stderr={chain['redetect']['stderr']!r}")
    assert chain["redetect"]["env"] == expected["redetect_env"], (
        f"[{manifest['id']}] post-drop redetect env mismatch: "
        f"expected {expected['redetect_env']!r}, got {chain['redetect']['env']!r}")

    assert chain["filter"] is not None, "filter after re-detect failed to run"
    assert chain["filter"]["rc"] == 0, (
        f"filter exit {chain['filter']['rc']}; stderr={chain['filter']['stderr']!r}")
    assert chain["filter"]["counts"] == expected["filter_counts"], (
        f"[{manifest['id']}] post-drop filter counts mismatch: "
        f"expected {expected['filter_counts']!r}, got {chain['filter']['counts']!r}")
