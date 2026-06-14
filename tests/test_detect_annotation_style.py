"""Smoke tests for annotation style detector used by nf-core-rnaseq job scripts."""

from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "laxy_pipeline_apps/nf-core-rnaseq/templates/common/input/scripts/detect_annotation_style.py"
)


def _run(path: Path, out_env: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "-o", str(out_env)],
        capture_output=True,
        text=True,
        check=False,
    )


def _source_vars(env_path: Path) -> dict:
    lines = env_path.read_text(encoding="utf-8").strip().splitlines()
    out: dict = {}
    for line in lines:
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        out[key] = rest.strip().strip("'")
    return out


def _assert_cds_only_skip_bundle(flags: str) -> None:
    got = set(flags.split())
    expected = {
        "--skip_rseqc",
        "--skip_qualimap",
        "--skip_bigwig",
        "--skip_dupradar",
    }
    assert expected.issubset(got)


def test_ensembl_like_gtf(tmp_path: Path) -> None:
    gtf = tmp_path / "x.gtf"
    gtf.write_text(
        'chr1\tunknown\texon\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "GENE1"; '
        'gene_biotype "protein_coding"; transcript_id "t1";\n',
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gtf, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "exon"
    assert v["ANN_GROUP_FEATURES"] == "gene_id"
    assert v["ANN_BIOTYPE_ATTR"] == "gene_biotype"


def test_prokka_like_gtf(tmp_path: Path) -> None:
    gtf = tmp_path / "p.gtf"
    gtf.write_text(
        'contig\tProdigal:002\tCDS\t10\t100\t.\t+\t0\tgene_id "gene1"; '
        'locus_tag "gene1"; product "hypothetical protein";\n',
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gtf, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "CDS"
    assert v["ANN_GROUP_FEATURES"] == "gene_id"
    assert "--skip_biotype_qc" in v["ANN_SKIP_FLAGS"].split()
    _assert_cds_only_skip_bundle(v["ANN_SKIP_FLAGS"])


def test_prokka_like_gff3(tmp_path: Path) -> None:
    gff = tmp_path / "p.gff3"
    gff.write_text(
        "contig\tProdigal\tCDS\t10\t100\t.\t+\t0\tID=gene1;inference=foo;"
        "locus_tag=gene1;product=hypothetical+protein\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "CDS"
    # ID and locus_tag both work for grouping (each CDS is a unique gene).
    assert v["ANN_GROUP_FEATURES"] in {"ID", "locus_tag"}
    assert v["ANN_PROKARYOTIC"] == "yes"
    assert "--skip_biotype_qc" in v["ANN_SKIP_FLAGS"].split()
    _assert_cds_only_skip_bundle(v["ANN_SKIP_FLAGS"])


def test_ncbi_genbank_bacterial_gff(tmp_path: Path) -> None:
    """NCBI GenBank-source bacterial GFF: CDS rows have Parent=/gene= but no locus_tag."""
    gff = tmp_path / "ncbi.gff"
    gff.write_text(
        "##gff-version 3\n"
        "CP001172.1\tGenbank\tregion\t1\t100\t.\t+\t.\tID=CP001172.1:1..100;"
        "Dbxref=taxon:557600\n"
        "CP001172.1\tGenbank\tgene\t57\t1481\t.\t+\t.\tID=CP001172.1:gene1;"
        "Name=dnaA;gbkey=Gene;gene=dnaA\n"
        "CP001172.1\tGenbank\tCDS\t57\t1481\t.\t+\t0\tID=CP001172.1:dnaA:cds1;"
        "Parent=CP001172.1:gene1;Dbxref=NCBI_GP:ACJ56891.1;Name=ACJ56891.1;"
        "gbkey=CDS;gene=dnaA;product=DnaA\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "CDS"
    # GROUP_ATTR_PRIORITY picks Parent/Name/gene/ID for this file - any is fine.
    assert v["ANN_GROUP_FEATURES"] in {"Parent", "Name", "gene", "ID"}
    assert v["ANN_PROKARYOTIC"] == "yes"
    assert v["ANN_PROFILE"] == "ncbi_genbank"
    extras = v["ANN_EXTRA_ATTRIBUTES"].split(",")
    assert "gene" in extras or "Name" in extras


def test_minimal_gff_with_only_id_and_name(tmp_path: Path) -> None:
    """File where CDS rows only have ID/Name/product (no gene_id/locus_tag)."""
    gff = tmp_path / "minimal.gff"
    gff.write_text(
        "ctg\t.\tCDS\t1\t100\t.\t+\t0\tID=cds1;Name=foo;product=bar\n"
        "ctg\t.\tCDS\t200\t300\t.\t+\t0\tID=cds2;Name=baz;product=qux\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "CDS"
    # Either Name or ID is acceptable here; both are unique per CDS.
    assert v["ANN_GROUP_FEATURES"] in {"Name", "ID"}
    assert v["ANN_PROKARYOTIC"] == "yes"


def test_geneious_export_only_name(tmp_path: Path) -> None:
    """Geneious GFF exports often have only Name= on CDS/gene/Old_Gene rows."""
    gff = tmp_path / "geneious.gff"
    gff.write_text(
        "##gff-version 3\n"
        "chrA\tGeneious\tCDS\t6394\t6786\t.\t+\t0\tName=cybC CDS\n"
        "chrA\tGeneious\tgene\t6394\t6786\t.\t+\t.\tName=cybC gene\n"
        "chrA\tGeneious\tOld_Gene\t6394\t6786\t.\t+\t.\tName=ABBFA 000005 gene\n"
        "chrA\tGeneious\tCDS\t6870\t7427\t.\t-\t0\tName=yqjA 1 CDS\n"
        "chrA\tGeneious\tgene\t6870\t7427\t.\t-\t.\tName=yqjA 1 gene\n"
        "chrA\tGeneious\tCDS\t7678\t9609\t.\t-\t0\tName=yheS 1 CDS\n"
        "chrA\tGeneious\tgene\t7678\t9609\t.\t-\t.\tName=yheS 1 gene\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FEATURE_TYPE"] == "CDS"
    assert v["ANN_GROUP_FEATURES"] == "Name"
    assert v["ANN_PROKARYOTIC"] == "yes"
    assert v["ANN_EXTRA_ATTRIBUTES"] == ""
    assert "--skip_biotype_qc" in v["ANN_SKIP_FLAGS"].split()
    _assert_cds_only_skip_bundle(v["ANN_SKIP_FLAGS"])


def test_prokaryotic_prefers_gene_over_name_for_extras(tmp_path: Path) -> None:
    """For prokaryotes, gene= (symbol) should be preferred over Name= (often a protein accession)."""
    gff = tmp_path / "prok.gff"
    gff.write_text(
        "##gff-version 3\n"
        "ctg\tx\tCDS\t1\t100\t.\t+\t0\tID=cds1;Parent=gene1;"
        "Name=ACJ56891.1;gene=dnaA;product=DnaA;locus_tag=GENE_001\n"
        "ctg\tx\tCDS\t200\t300\t.\t+\t0\tID=cds2;Parent=gene2;"
        "Name=ACJ56892.1;gene=dnaN;product=DnaN;locus_tag=GENE_002\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_PROKARYOTIC"] == "yes"
    extras = v["ANN_EXTRA_ATTRIBUTES"].split(",")
    # gene must come before Name in extras for prokaryotes
    assert "gene" in extras
    assert "Name" in extras
    assert extras.index("gene") < extras.index("Name")


def test_eukaryotic_prefers_gene_name_over_gene_for_extras(tmp_path: Path) -> None:
    """For eukaryotes (Ensembl-like), gene_name should be preferred over gene."""
    gtf = tmp_path / "ens.gtf"
    gtf.write_text(
        'chr1\tens\texon\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "DNAA"; '
        'gene "dnaa_alt"; gene_biotype "protein_coding"; transcript_id "t1";\n',
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gtf, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_PROKARYOTIC"] == "no"
    extras = v["ANN_EXTRA_ATTRIBUTES"].split(",")
    assert "gene_name" in extras
    if "gene" in extras:
        assert extras.index("gene_name") < extras.index("gene")


def test_attribute_keys_logged_on_failure(tmp_path: Path) -> None:
    """Failure messages should include observed attribute keys for diagnosis."""
    gff = tmp_path / "bad.gff"
    gff.write_text(
        "ctg\t.\tCDS\t1\t100\t.\t+\t0\tweird_attr=foo;another=bar\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(gff, env_out)
    assert r.returncode != 0
    assert "weird_attr" in r.stderr or "another" in r.stderr


def test_gzip_gtf(tmp_path: Path) -> None:
    path = tmp_path / "x.gtf.gz"
    data = (
        'chr1\tunknown\texon\t1\t100\t.\t+\t.\tgene_id "g1"; gene_name "GENE1"; '
        'gene_biotype "protein_coding"; transcript_id "t1";\n'
    ).encode()
    path.write_bytes(gzip.compress(data))
    env_out = tmp_path / "style.env"
    r = _run(path, env_out)
    assert r.returncode == 0, r.stderr


def test_misnamed_gz_actually_plain_text(tmp_path: Path) -> None:
    """File named ``.gz`` but actually plain GFF3: detection must use file magic, not extension."""
    path = tmp_path / "genes.gff.gz"
    path.write_text(
        "##gff-version 3\n"
        "ctg\t.\tCDS\t1\t100\t.\t+\t0\tID=cds1;Name=foo\n",
        encoding="utf-8",
    )
    env_out = tmp_path / "style.env"
    r = _run(path, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FORMAT"] == "gff3"
    assert v["ANN_FEATURE_TYPE"] == "CDS"


def test_misnamed_plain_actually_gzipped(tmp_path: Path) -> None:
    """File without ``.gz`` suffix but actually gzipped: should still decompress."""
    path = tmp_path / "genes.gff"
    path.write_bytes(
        gzip.compress(
            b"##gff-version 3\n"
            b"ctg\t.\tCDS\t1\t100\t.\t+\t0\tID=cds1;Name=foo\n"
        )
    )
    env_out = tmp_path / "style.env"
    r = _run(path, env_out)
    assert r.returncode == 0, r.stderr
    v = _source_vars(env_out)
    assert v["ANN_FORMAT"] == "gff3"
    assert v["ANN_FEATURE_TYPE"] == "CDS"


def test_empty_file_fails(tmp_path: Path) -> None:
    empty = tmp_path / "empty.gtf"
    empty.write_text("", encoding="utf-8")
    env_out = tmp_path / "style.env"
    r = _run(empty, env_out)
    assert r.returncode != 0
