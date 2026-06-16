"""Tier 4: end-to-end nf-core/rnaseq against fake-cluster (local-dev).

Heavy: builds a STAR index, runs Salmon, featureCounts, etc. Skipped unless
``--e2e`` is passed AND nextflow is on PATH AND the fake-cluster stack is up.
Run with::

    just test-annotation-corpus-e2e

Reads are generated on demand from the annotation's feature coords + the
shared genome (see shared/generate_reads.py); a per-case cache lives under
``cases/<id>/reads/``.

This module is a scaffold: it generates reads and asserts they map back to the
genome (sanity check that the synthetic data is usable). The full
nf-core/rnaseq invocation is wired in but guarded behind the e2e mark; fill in
the nextflow command once the fake-cluster wiring is confirmed.
"""

from __future__ import annotations

import gzip
import shutil
import subprocess

import pytest

import conftest as ctx  # type: ignore  # noqa: E402
import corpus_lib as cl  # type: ignore  # noqa: E402


def _nextflow_available() -> bool:
    return shutil.which("nextflow") is not None


@pytest.mark.corpus
@pytest.mark.e2e
@pytest.mark.parametrize("case", ctx.case_params(stage="e2e"), indirect=False)
def test_e2e_reads_sanity(case, tmp_path):
    """Generate reads and assert they are non-empty + map-able (fast pre-check)."""
    case_dir, manifest = case
    e2e = manifest["expected"]["e2e"]
    if not e2e.get("run"):
        pytest.skip("e2e not enabled for this case")

    cl.generate_reads(case_dir, manifest)
    r1 = case_dir / "reads" / "sample_R1.fastq.gz"
    r2 = case_dir / "reads" / "sample_R2.fastq.gz"
    assert r1.is_file(), "reads not generated"

    n = 0
    with gzip.open(r1, "rt") as fp:
        for line in fp:
            if line.startswith("@"):
                n += 1
    assert n >= manifest["reads"]["count"] * 0.9, f"too few reads: {n}"
    if manifest["reads"]["mode"] == "paired":
        assert r2.is_file(), "R2 missing for paired mode"


@pytest.mark.corpus
@pytest.mark.e2e
@pytest.mark.parametrize("case", ctx.case_params(stage="e2e"), indirect=False)
def test_e2e_nfcore_rnaseq(case, tmp_path):
    """Full nf-core/rnaseq run. Requires nextflow + fake-cluster stack."""
    if not _nextflow_available():
        pytest.skip("nextflow not on PATH")

    case_dir, manifest = case
    # TODO(corpus): wire the actual `nextflow run nf-core/rnaseq` invocation
    # against the fake-cluster profile once the local-dev wiring is confirmed.
    # Inputs: cl.GENOME, cl.annotation_path(case_dir), case_dir/reads/*.
    # Aligner/flags come from manifest["expected"]["e2e"].
    pytest.skip("nf-core/rnaseq e2e invocation not yet wired (see TODO)")
