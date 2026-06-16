"""Tier 2: filter_annotation_features.py produces the expected row counts.

Runs the filter with the feature_type / format / group-feature the detector
picked, then asserts the synthesised-GTF row counts match the snapshot.
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="filter"), indirect=False)
def test_filter(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    env = manifest["expected"]["detect"]["env"]

    result = cl.run_filter(
        ann, env["ANN_FORMAT"], env["ANN_FEATURE_TYPE"],
        env.get("ANN_GROUP_FEATURES", ""),
    )

    expected = manifest["expected"]["filter"]
    assert result["rc"] == expected["exit"], (
        f"filter exit {result['rc']}; stderr={result['stderr']!r}")

    for key, want in expected["counts"].items():
        got = result["counts"].get(key)
        assert got == want, (
            f"[{manifest['id']}] filter {key}: expected {want}, got {got}")
