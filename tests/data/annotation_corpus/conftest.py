"""Pytest harness for the synthetic annotation corpus.

Auto-collects every ``cases/<id>/manifest.json``; adding a new example is just
"drop the annotation file + regenerate manifests" (see README). No manual test
edits required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "shared"))
import corpus_lib as cl  # noqa: E402


def _load_all() -> list[tuple[Path, dict]]:
    out = []
    for case_dir in cl.discover_cases():
        if (case_dir / "manifest.json").is_file():
            out.append((case_dir, cl.load_manifest(case_dir)))
    return out


CASES = _load_all()


def case_params(stage: str | None = None):
    """Return pytest.param list, optionally filtered to cases that run ``stage``.

    Cases with ``xfail_reason`` get a strict xfail mark (so a fix turns the
    xpass into a failure = an explicit "bug fixed" alert).
    """
    items = []
    for case_dir, manifest in CASES:
        if stage and not manifest["expected"].get(stage):
            continue
        marks = []
        # The xfail (doc §6.1) is specifically about detector
        # misclassification, so only the detect stage carries the mark.
        if manifest.get("xfail_reason") and stage == "detect":
            marks.append(pytest.mark.xfail(
                strict=True, reason=manifest["xfail_reason"]))
        items.append(pytest.param(
            (case_dir, manifest), id=manifest["id"], marks=marks))
    return items


def detect_env_subset_ok(actual: dict, expected_subset: dict) -> tuple[bool, str]:
    """Subset-compare detector env: every key in expected_subset must match."""
    for k, v in expected_subset.items():
        if actual.get(k) != v:
            return False, f"{k}: expected {v!r}, got {actual.get(k)!r}"
    return True, ""
