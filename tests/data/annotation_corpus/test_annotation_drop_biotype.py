"""Tier 2b: drop_biotype_features.py removes non-coding RNA gene groups.

Runs on the raw annotation (before any prokaryotic-only synthesis by
filter_annotation_features.py), using ANN_DROP_BIOTYPES from the detector.
For most cases this is empty and the script is a documented no-op; for
E5_eukaryote_ncrna_ids it strips the tRNA/rRNA gene groups that break
nf-core/rnaseq's tximport/SummarizedExperiment step (see
ANNOTATION_REQUIREMENTS_AND_FILTERING.md §6 item 7).
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="drop_biotype"), indirect=False)
def test_drop_biotype(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    env = manifest["expected"]["detect"]["env"]

    result = cl.run_drop_biotype(
        ann, env["ANN_FORMAT"], env.get("ANN_DROP_BIOTYPES", ""),
    )

    expected = manifest["expected"]["drop_biotype"]
    assert result["rc"] == expected["exit"], (
        f"drop_biotype exit {result['rc']}; stderr={result['stderr']!r}")

    for key, want in expected["counts"].items():
        got = result["counts"].get(key)
        assert got == want, (
            f"[{manifest['id']}] drop_biotype {key}: expected {want}, got {got}")
