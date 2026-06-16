#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One-off bootstrap: write the case annotation fixtures from ANNOTATION_* doc.

Re-runnable: overwrites cases/*/annotation.* in place. Edit fixtures by hand
afterwards; this just seeds them. Tabs matter (GTF/GFF3 are TSV) so content is
written via explicit "\\t".
"""

from __future__ import annotations

import gzip
from pathlib import Path

# Script lives in ``shared/``; the corpus root is one level up.
ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"


def write(path: Path, body: str) -> None:  # noqa: A001 (shadow fine here)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def write_bytes(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def write_gz(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fp:
        fp.write(body)


# ---------------------------------------------------------------------------
# Eukaryotic happy paths
# ---------------------------------------------------------------------------

# --- E1: Ensembl-style GTF (gene_biotype, ENSG/ENST ids) ---
E1 = (
    "chr1\tlaxy_test\texon\t1000\t1250\t.\t+\t.\tgene_id \"ENSGTEST00000000001\"; transcript_id \"ENSMTEST00000000001\"; gene_name \"GENE_A\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\texon\t1500\t2000\t.\t+\t.\tgene_id \"ENSGTEST00000000001\"; transcript_id \"ENSMTEST00000000001\"; gene_name \"GENE_A\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\texon\t3000\t4500\t.\t+\t.\tgene_id \"ENSGTEST00000000002\"; transcript_id \"ENSMTEST00000000002\"; gene_name \"GENE_B\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\texon\t4600\t5200\t.\t+\t.\tgene_id \"ENSGTEST00000000002\"; transcript_id \"ENSMTEST00000000002\"; gene_name \"GENE_B\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\texon\t5300\t6800\t.\t-\t.\tgene_id \"ENSGTEST00000000003\"; transcript_id \"ENSMTEST00000000003\"; gene_name \"GENE_C\"; gene_biotype \"lncRNA\";\n"
    "chr1\tlaxy_test\texon\t7000\t8000\t.\t-\t.\tgene_id \"ENSGTEST00000000003\"; transcript_id \"ENSMTEST00000000003\"; gene_name \"GENE_C\"; gene_biotype \"lncRNA\";\n"
    "chr1\tlaxy_test\texon\t8200\t9000\t.\t+\t.\tgene_id \"ENSGTEST00000000004\"; transcript_id \"ENSMTEST00000000004\"; gene_name \"GENE_D\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\texon\t5000\t6000\t.\t+\t.\tgene_id \"ENSGTEST00000000005\"; transcript_id \"ENSMTEST00000000005\"; gene_name \"GENE_E\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\texon\t6500\t8000\t.\t+\t.\tgene_id \"ENSGTEST00000000005\"; transcript_id \"ENSMTEST00000000005\"; gene_name \"GENE_E\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\texon\t8500\t9200\t.\t-\t.\tgene_id \"ENSGTEST00000000006\"; transcript_id \"ENSMTEST00000000006\"; gene_name \"GENE_F\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\texon\t9300\t9800\t.\t-\t.\tgene_id \"ENSGTEST00000000006\"; transcript_id \"ENSMTEST00000000006\"; gene_name \"GENE_F\"; gene_biotype \"protein_coding\";\n"
)
write(CASES / "E1_eukaryote_ensembl" / "annotation.gtf", E1)

# --- E2: GENCODE-style (gene_type instead of gene_biotype) ---
E2 = E1.replace(" gene_biotype \"", " gene_type \"")
write(CASES / "E2_eukaryote_gencode" / "annotation.gtf", E2)

# --- E3: RefSeq GFF3 eukaryotic (gene/mRNA/exon/CDS, no biotype attr) ---
# E3 needs >10 exon rows AND >=1 mRNA/transcript so the detector classifies it
# refseq_gff3 (see detect_annotation_style.py: _classify_profile). Four genes,
# each with an mRNA and 3 exons (12 exons total). Coordinates stay well within
# chr1 (100 kb) and chr2 (50 kb).
_E3_ROWS = [
    # gene / mRNA / 3 exons / 3 CDS per gene
    ("chr1", "+", "gene1", "rna1", "GENE_A", [(1000, 2000), (3000, 5200), (7000, 9000)]),
    ("chr1", "-", "gene2", "rna2", "GENE_B", [(5000, 6200), (7000, 8100), (9000, 11000)]),
    ("chr1", "+", "gene3", "rna3", "GENE_C", [(15000, 16500), (18000, 19500), (21000, 23000)]),
    ("chr2", "+", "gene4", "rna4", "GENE_D", [(1000, 2000), (3500, 4500), (6000, 7200)]),
]


def _refseq_gene(parent: str, name: str) -> str:
    # Real RefSeq GFF3 carries gene_biotype on the gene row; the detector
    # keys off it (together with >10 exons + >=1 mRNA) for refseq_gff3.
    return f"ID={parent};Name={name};gbkey=Gene;gene_biotype=protein_coding"


def _refseq_mRNA(rna: str, parent: str) -> str:
    return f"ID={rna};Parent={parent};gbkey=mRNA;product=test"


def _refseq_exon(eid: str, parent: str) -> str:
    return f"ID={eid};Parent={parent}"


def _refseq_cds(cid: str, parent: str) -> str:
    return f"ID={cid};Parent={parent}"


def _gff_row(seqid: str, feat: str, start: int, end: int, strand: str, frame: str, attrs: str) -> str:
    return f"{seqid}\tRefSeq\t{feat}\t{start}\t{end}\t.\t{strand}\t{frame}\t{attrs}\n"


_E3_LINES = ["##gff-version 3\n"]
for seqid, strand, gid, rna, name, exons in _E3_ROWS:
    g_start, g_end = exons[0][0], exons[-1][1]
    _E3_LINES.append(_gff_row(seqid, "gene", g_start, g_end, strand, ".", _refseq_gene(gid, name)))
    _E3_LINES.append(_gff_row(seqid, "mRNA", g_start, g_end, strand, ".", _refseq_mRNA(rna, gid)))
    for i, (s, e) in enumerate(exons, start=1):
        _E3_LINES.append(_gff_row(seqid, "exon", s, e, strand, ".", _refseq_exon(f"exon-{rna}-{i}", rna)))
        _E3_LINES.append(_gff_row(seqid, "CDS", s, e, strand, "0", _refseq_cds(f"cds-{rna}-{i}", rna)))
E3 = "".join(_E3_LINES)
write(CASES / "E3_eukaryote_refseq" / "annotation.gff3", E3)

# --- E4: eukaryotic exons with no biotype attr anywhere (skip biotype QC) ---
E4 = (
    "chr1\tlaxy_test\texon\t1000\t2000\t.\t+\t.\tgene_id \"GENE_A\"; transcript_id \"GENE_A.t1\"; gene_name \"GENE_A\";\n"
    "chr1\tlaxy_test\texon\t3000\t4500\t.\t+\t.\tgene_id \"GENE_A\"; transcript_id \"GENE_A.t1\"; gene_name \"GENE_A\";\n"
    "chr1\tlaxy_test\texon\t5000\t6800\t.\t-\t.\tgene_id \"GENE_B\"; transcript_id \"GENE_B.t1\"; gene_name \"GENE_B\";\n"
    "chr2\tlaxy_test\texon\t5000\t6800\t.\t+\t.\tgene_id \"GENE_C\"; transcript_id \"GENE_C.t1\"; gene_name \"GENE_C\";\n"
    "chr2\tlaxy_test\texon\t7000\t9000\t.\t+\t.\tgene_id \"GENE_C\"; transcript_id \"GENE_C.t1\"; gene_name \"GENE_C\";\n"
)
write(CASES / "E4_eukaryote_no_biotype" / "annotation.gtf", E4)

# ---------------------------------------------------------------------------
# Prokaryotic happy paths
# ---------------------------------------------------------------------------

# --- P1: minimal prokaryotic CDS-only GTF (self-contained gene_id) ---
P1 = (
    "chr1\tlaxy_test\tCDS\t100\t1200\t.\t+\t0\tgene_id \"b0001\"; transcript_id \"b0001\"; gene_name \"dnaA\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\tCDS\t1300\t2400\t.\t+\t0\tgene_id \"b0002\"; transcript_id \"b0002\"; gene_name \"dnaN\"; gene_biotype \"protein_coding\";\n"
    "chr1\tlaxy_test\tCDS\t2500\t3000\t.\t-\t0\tgene_id \"b0003\"; transcript_id \"b0003\"; gene_name \"recF\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\tCDS\t100\t900\t.\t+\t0\tgene_id \"b0004\"; transcript_id \"b0004\"; gene_name \"gyrA\"; gene_biotype \"protein_coding\";\n"
)
write(CASES / "P1_prokaryote_minimal_gtf" / "annotation.gtf", P1)

# --- P2: NCBI GenBank bacterial GFF3 (gene+CDS, gbkey/Dbxref/locus_tag) ---
def cds(pid: str, parent: str, gene: str, tag: str, prod: str) -> str:
    return (f"ID=cds-{gene};Parent={parent};Name={gene};gbkey=CDS;gene={gene};"
            f"locus_tag={tag};product={prod};protein_id={pid};Dbxref=PFAM:PF00000")


P2 = (
    "##gff-version 3\n"
    "chr1\tRefSeq\tgene\t100\t1200\t.\t+\t.\tID=gene-dnaA;Name=dnaA;gbkey=Gene;gene=dnaA;locus_tag=LAXYTEST_0001\n"
    + f"chr1\tRefSeq\tCDS\t100\t1200\t.\t+\t0\t{cds('WP_TEST001','gene-dnaA','dnaA','LAXYTEST_0001','DNA replication initiator DnaA')}\n"
    + "chr1\tRefSeq\tgene\t1300\t2400\t.\t+\t.\tID=gene-dnaN;Name=dnaN;gbkey=Gene;gene=dnaN;locus_tag=LAXYTEST_0002\n"
    + f"chr1\tRefSeq\tCDS\t1300\t2400\t.\t+\t0\t{cds('WP_TEST002','gene-dnaN','dnaN','LAXYTEST_0002','DNA pol III subunit beta DnaN')}\n"
    + "chr1\tRefSeq\tgene\t2500\t3000\t.\t-\t.\tID=gene-recF;Name=recF;gbkey=Gene;gene=recF;locus_tag=LAXYTEST_0003\n"
    + f"chr1\tRefSeq\tCDS\t2500\t3000\t.\t-\t0\t{cds('WP_TEST003','gene-recF','recF','LAXYTEST_0003','DNA replication protein RecF')}\n"
    + "chr2\tRefSeq\tgene\t100\t900\t.\t+\t.\tID=gene-gyrA;Name=gyrA;gbkey=Gene;gene=gyrA;locus_tag=LAXYTEST_0004\n"
    + f"chr2\tRefSeq\tCDS\t100\t900\t.\t+\t0\t{cds('WP_TEST004','gene-gyrA','gyrA','LAXYTEST_0004','DNA gyrase subunit A GyrA')}\n"
)
write(CASES / "P2_prokaryote_ncbi" / "annotation.gff3", P2)

# --- P3: Bakta GFF3 (flat CDS, ID=locus_tag, product, gene, no Parent) ---
P3 = (
    "##gff-version 3\n"
    "chr1\tBakta\tCDS\t100\t1200\t.\t+\t0\tID=LAXYTEST_00001;locus_tag=LAXYTEST_00001;gene=dnaA;product=DNA replication initiator DnaA\n"
    "chr1\tBakta\tCDS\t1300\t2400\t.\t+\t0\tID=LAXYTEST_00002;locus_tag=LAXYTEST_00002;gene=dnaN;product=DNA pol III subunit beta DnaN\n"
    "chr1\tBakta\tCDS\t2500\t3000\t.\t-\t0\tID=LAXYTEST_00003;locus_tag=LAXYTEST_00003;gene=recF;product=DNA replication protein RecF\n"
    "chr2\tBakta\tCDS\t100\t900\t.\t+\t0\tID=LAXYTEST_00004;locus_tag=LAXYTEST_00004;gene=gyrA;product=DNA gyrase subunit A GyrA\n"
)
write(CASES / "P3_prokaryote_bakta" / "annotation.gff3", P3)

# --- P4: Prokka GFF3 (flat CDS, ID, gene, product, eC_number, no locus_tag) ---
P4 = (
    "##gff-version 3\n"
    "chr1\tProkka\tCDS\t100\t1200\t.\t+\t0\tID=LAXY_00001;gene=dnaA;product=chromosomal_replication_initiator_protein;eC_number=2.7.7.-;inference=ab initio\n"
    "chr1\tProkka\tCDS\t1300\t2400\t.\t+\t0\tID=LAXY_00002;gene=dnaN;product=DNA_polymerase_III_subunit_beta;eC_number=2.7.7.-;inference=ab initio\n"
    "chr1\tProkka\tCDS\t2500\t3000\t.\t-\t0\tID=LAXY_00003;gene=recF;product=DNA_replication_protein_RecF;eC_number=2.7.7.-;inference=ab initio\n"
    "chr2\tProkka\tCDS\t100\t900\t.\t+\t0\tID=LAXY_00004;gene=gyrA;product=DNA_gyrase_subunit_A;eC_number=5.99.1.3;inference=ab initio\n"
)
write(CASES / "P4_prokaryote_prokka" / "annotation.gff3", P4)

# ---------------------------------------------------------------------------
# Failure / edge cases
# ---------------------------------------------------------------------------

# --- F1: flat SnapGene GFF3 (gene+CDS rows, Name= quoted, no ID, no Parent) ---
F1 = (
    "##gff-version 3\n"
    "chr1\texported\tgene\t100\t1200\t.\t+\t.\tName=\"dnaA\"\n"
    "chr1\texported\tCDS\t100\t1200\t.\t+\t0\tName=\"dnaA\"\n"
    "chr1\texported\tgene\t1300\t2400\t.\t+\t.\tName=\"dnaN\"\n"
    "chr1\texported\tCDS\t1300\t2400\t.\t+\t0\tName=\"dnaN\"\n"
    "chr1\texported\tgene\t2500\t3000\t.\t-\t.\tName=\"recF\"\n"
    "chr1\texported\tCDS\t2500\t3000\t.\t-\t0\tName=\"recF\"\n"
    "chr2\texported\tgene\t100\t900\t.\t+\t.\tName=\"gyrA\"\n"
    "chr2\texported\tCDS\t100\t900\t.\t+\t0\tName=\"gyrA\"\n"
)
write(CASES / "F1_flat_snapgene" / "annotation.gff3", F1)

# --- F2: SnapGene export with a stray 'variation' feature row mixed in ---
F2 = (
    "##gff-version 3\n"
    "chr1\texported\tgene\t100\t1200\t.\t+\t.\tName=\"dnaA\"\n"
    "chr1\texported\tCDS\t100\t1200\t.\t+\t0\tName=\"dnaA\"\n"
    "chr1\texported\tvariation\t150\t160\t.\t+\t.\tName=\"SNP_marker\";Note=\"synthetic\"\n"
    "chr1\texported\tgene\t1300\t2400\t.\t+\t.\tName=\"dnaN\"\n"
    "chr1\texported\tCDS\t1300\t2400\t.\t+\t0\tName=\"dnaN\"\n"
    "chr2\texported\tgene\t100\t900\t.\t+\t.\tName=\"gyrA\"\n"
    "chr2\texported\tCDS\t100\t900\t.\t+\t0\tName=\"gyrA\"\n"
)
write(CASES / "F2_snapgene_variation" / "annotation.gff3", F2)

# --- F3: P2 content but seqids = Accession tokens (no overlap with FASTA) ---
F3 = P2.replace("chr1\t", "TEST_CHR1\t").replace("chr2\t", "TEST_CHR2\t")
write(CASES / "F3_seqid_mismatch" / "annotation.gff3", F3)

# --- F4: partial overlap (some chr1 rows match, some chr3 rows don't) ---
F4 = P2.replace("chr2\t", "chr3\t", 1)  # first chr2 line -> chr3 only
# Build explicitly to be safe: keep chr1 rows, add one non-matching contig
F4 = (
    "##gff-version 3\n"
    "chr1\tRefSeq\tgene\t100\t1200\t.\t+\t.\tID=gene-dnaA;Name=dnaA;gbkey=Gene;gene=dnaA;locus_tag=LAXYTEST_0001\n"
    + f"chr1\tRefSeq\tCDS\t100\t1200\t.\t+\t0\t{cds('WP_TEST001','gene-dnaA','dnaA','LAXYTEST_0001','DnaA')}\n"
    + "chr3\tRefSeq\tgene\t100\t900\t.\t+\t.\tID=gene-gyrA;Name=gyrA;gbkey=Gene;gene=gyrA;locus_tag=LAXYTEST_0004\n"
    + f"chr3\tRefSeq\tCDS\t100\t900\t.\t+\t0\t{cds('WP_TEST004','gene-gyrA','gyrA','LAXYTEST_0004','GyrA')}\n"
)
write(CASES / "F4_seqid_mismatch_partial" / "annotation.gff3", F4)

# --- F5: only 8-column rows (no attributes col) -> detector finds no valid rows ---
F5 = (
    "##gff-version 3\n"
    "chr1\tRefSeq\tgene\t100\t1200\t.\t+\t.\n"
    "chr1\tRefSeq\tCDS\t100\t1200\t.\t+\t0\n"
)
write(CASES / "F5_eight_columns" / "annotation.gff3", F5)

# --- F6: GFF3 with trailing ##FASTA section (must be skipped) ---
F6 = (
    "##gff-version 3\n"
    "chr1\tRefSeq\tCDS\t100\t1200\t.\t+\t0\tID=cds1;gene=dnaA;product=DnaA\n"
    "chr1\tRefSeq\tCDS\t1300\t2400\t.\t+\t0\tID=cds2;gene=dnaN;product=DnaN\n"
    "##FASTA\n"
    ">chr1 synthetic\n"
    "ACGTACGTAC\n"
)
write(CASES / "F6_embedded_fasta" / "annotation.gff3", F6)

# --- F8: AGAT-converted F1 (gene->mRNA->exon->CDS, synthetic mRNA/exon) ---
F8 = (
    "##gff-version 3\n"
    "chr1\tAGAT\tgene\t100\t1200\t.\t+\t.\tID=gene1;Name=dnaA\n"
    "chr1\tAGAT\tmRNA\t100\t1200\t.\t+\t.\tID=mrna1;Parent=gene1\n"
    "chr1\tAGAT\texon\t100\t1200\t.\t+\t.\tID=exon1;Parent=mrna1\n"
    "chr1\tAGAT\tCDS\t100\t1200\t.\t+\t0\tID=cds1;Parent=mrna1\n"
    "chr1\tAGAT\tgene\t1300\t2400\t.\t+\t.\tID=gene2;Name=dnaN\n"
    "chr1\tAGAT\tmRNA\t1300\t2400\t.\t+\t.\tID=mrna2;Parent=gene2\n"
    "chr1\tAGAT\texon\t1300\t2400\t.\t+\t.\tID=exon2;Parent=mrna2\n"
    "chr1\tAGAT\tCDS\t1300\t2400\t.\t+\t0\tID=cds2;Parent=mrna2\n"
)
write(CASES / "F8_agat_converted" / "annotation.gff3", F8)

# --- F9: multi-contig eukaryotic GTF (more genes, both chromosomes) ---
F9 = E1 + (
    "chr2\tlaxy_test\texon\t10000\t10800\t.\t+\t.\tgene_id \"ENSGTEST00000000007\"; transcript_id \"ENSMTEST00000000007\"; gene_name \"GENE_G\"; gene_biotype \"protein_coding\";\n"
    "chr2\tlaxy_test\texon\t11000\t12000\t.\t+\t.\tgene_id \"ENSGTEST00000000007\"; transcript_id \"ENSMTEST00000000007\"; gene_name \"GENE_G\"; gene_biotype \"protein_coding\";\n"
)
write(CASES / "F9_mixed_chromosomes" / "annotation.gtf", F9)

# --- F10: empty annotation ---
write(CASES / "F10_empty" / "annotation.gtf", "")

# --- F11: mixed-attr format (GTF rows then a GFF3 '=' row) ---
F11 = (
    "chr1\tlaxy_test\texon\t1000\t2000\t.\t+\t.\tgene_id \"GENE_A\"; transcript_id \"GENE_A.t1\"; gene_name \"GENE_A\";\n"
    "chr1\tlaxy_test\texon\t3000\t4500\t.\t+\t.\tgene_id \"GENE_A\"; transcript_id \"GENE_A.t1\"; gene_name \"GENE_A\";\n"
    "chr1\tlaxy_test\texon\t5000\t6800\t.\t-\t.\tgene_id \"GENE_B\"; transcript_id \"GENE_B.t1\"; gene_name \"GENE_B\";\n"
)
write(CASES / "F11_mixed_format" / "annotation.gtf", F11)

# ---------------------------------------------------------------------------
# Compression edge: gzipped GFF3 (P3 content) - tests gz auto-detection
# ---------------------------------------------------------------------------
write_gz(CASES / "P3gz_prokaryote_bakta_gz" / "annotation.gff3.gz", P3)

# --- F7: CRLF + UTF-8 BOM (P1 content as bytes) ---
P1_bytes = ("\ufeff" + P1).replace("\n", "\r\n").encode("utf-8")
write_bytes(CASES / "F7_crlf_bom" / "annotation.gtf", P1_bytes)

print("wrote annotation fixtures:")
for p in sorted(CASES.glob("*/annotation.*")):
    print(" ", p.relative_to(ROOT))
