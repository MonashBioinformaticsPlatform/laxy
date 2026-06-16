"""Tier 1: detect_annotation_style.py behaves as the manifest snapshots.

For happy/repairable/detect_only/failfast cases we assert the captured env.
For the xfail case (F8) we assert the CORRECT behaviour the detector should
produce once doc §6.1 is fixed -- strict xfail means the fix turns xpass into
a failure, flagging that the manifest tier can be promoted to happy.
"""

from __future__ import annotations

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


@pytest.mark.corpus
@pytest.mark.parametrize("case", ctx.case_params(stage="detect"), indirect=False)
def test_detect(case):
    case_dir, manifest = case
    ann = cl.annotation_path(case_dir)
    assert ann is not None, f"no annotation.* in {case_dir}"

    expected = manifest["expected"]["detect"]
    result = cl.run_detect(ann)

    assert result["rc"] == expected["exit"], (
        f"exit {result['rc']} != {expected['exit']}; stderr={result['stderr']!r}")

    if expected["exit"] != 0:
        needle = expected.get("stderr_contains", "")
        if needle:
            assert needle in result["stderr"], (
                f"{needle!r} not in stderr: {result['stderr']!r}")
        return

    ok, why = ctx.detect_env_subset_ok(result["env"], expected["env"])
    assert ok, f"[{manifest['id']}] env mismatch: {why}\nfull env: {result['env']}"
