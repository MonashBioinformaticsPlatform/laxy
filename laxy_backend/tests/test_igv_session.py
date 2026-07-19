"""
Unit tests for the pure IGV-session helpers in `laxy_backend.igv_session`:
genome-id mapping, BAM->index sibling matching, and session XML rendering.
No database or network required.
"""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

from django.test import SimpleTestCase

from ..igv_session import (
    laxy_genome_to_igv_id,
    find_bam_index,
    build_session_xml,
    reference_urls_from_genome,
)


def _f(name, path="output/aln", fid=None):
    return SimpleNamespace(name=name, path=path, id=fid or name)


class LaxyGenomeToIgvIdTest(SimpleTestCase):
    def test_known_assemblies_map_to_igv_ids(self):
        cases = {
            "Homo_sapiens/Ensembl/GRCh38.release-109": "hg38",
            "Homo_sapiens/Ensembl/GRCh37": "hg19",
            "Mus_musculus/Ensembl/GRCm39": "mm39",
            "Mus_musculus/Ensembl/GRCm38": "mm10",
            "Danio_rerio/Ensembl/GRCz11.97-noalt": "danRer11",
            "Saccharomyces_cerevisiae/Ensembl/R64-1-1": "sacCer3",
            "Drosophila_melanogaster/Ensembl/BDGP6": "dm6",
            "Caenorhabditis_elegans/Ensembl/WBcel235": "ce11",
        }
        for genome_id, expected in cases.items():
            self.assertEqual(laxy_genome_to_igv_id(genome_id), expected, genome_id)

    def test_unknown_or_empty_genome_returns_none(self):
        self.assertIsNone(laxy_genome_to_igv_id(None))
        self.assertIsNone(laxy_genome_to_igv_id(""))
        self.assertIsNone(laxy_genome_to_igv_id("Vicugna_pacos/Ensembl/vicPac1"))

    def test_grch38_does_not_mismatch_grch37(self):
        # A guard against substring ordering bugs.
        self.assertEqual(
            laxy_genome_to_igv_id("Homo_sapiens/Ensembl/GRCh38"), "hg38"
        )


class FindBamIndexTest(SimpleTestCase):
    def test_prefers_samtools_style_bam_bai(self):
        bam = _f("aln.bam")
        files = [bam, _f("aln.bam.bai"), _f("aln.bai")]
        self.assertEqual(find_bam_index(bam, files).name, "aln.bam.bai")

    def test_falls_back_to_picard_style_bai(self):
        bam = _f("aln.bam")
        files = [bam, _f("aln.bai")]
        self.assertEqual(find_bam_index(bam, files).name, "aln.bai")

    def test_matches_csi_index(self):
        bam = _f("aln.bam")
        files = [bam, _f("aln.bam.csi")]
        self.assertEqual(find_bam_index(bam, files).name, "aln.bam.csi")

    def test_only_matches_same_directory(self):
        bam = _f("aln.bam", path="output/sampleA")
        # Index-looking file in a different directory must not match.
        other = _f("aln.bam.bai", path="output/sampleB")
        self.assertIsNone(find_bam_index(bam, [bam, other]))

    def test_returns_none_when_no_index(self):
        bam = _f("aln.bam")
        self.assertIsNone(find_bam_index(bam, [bam, _f("aln.bam.md5")]))


class ReferenceUrlsFromGenomeTest(SimpleTestCase):
    def test_extracts_fasta_and_annotation_by_tags(self):
        meta = {
            "files": [
                {"location": "https://ftp/x.fa.gz", "type_tags": ["fasta"]},
                {"location": "https://ftp/x.gtf.gz", "type_tags": ["gtf", "annotation"]},
            ]
        }
        fasta, annotation = reference_urls_from_genome(meta)
        self.assertEqual(fasta, "https://ftp/x.fa.gz")
        self.assertEqual(annotation, "https://ftp/x.gtf.gz")

    def test_missing_files_returns_none(self):
        self.assertEqual(reference_urls_from_genome(None), (None, None))
        self.assertEqual(reference_urls_from_genome({"location": "x"}), (None, None))


class BuildSessionXmlTest(SimpleTestCase):
    def test_includes_genome_and_resources_with_index(self):
        xml = build_session_xml(
            "hg38",
            [
                {
                    "name": "aln.bam",
                    "path": "https://laxy/api/v1/job/J/files/output/aln.bam?access_token=T",
                    "index": "https://laxy/api/v1/job/J/files/output/aln.bam.bai?access_token=T",
                }
            ],
        )
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "Session")
        self.assertEqual(root.get("genome"), "hg38")
        resources = root.findall("./Resources/Resource")
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].get("name"), "aln.bam")
        self.assertTrue(resources[0].get("path").endswith("aln.bam?access_token=T"))
        self.assertTrue(
            resources[0].get("index").endswith("aln.bam.bai?access_token=T")
        )

    def test_omits_genome_when_none(self):
        xml = build_session_xml(None, [{"name": "aln.bam", "path": "https://x/aln.bam"}])
        root = ET.fromstring(xml)
        self.assertIsNone(root.get("genome"))

    def test_omits_index_attribute_when_absent(self):
        xml = build_session_xml(None, [{"name": "aln.bam", "path": "https://x/aln.bam"}])
        resource = ET.fromstring(xml).find("./Resources/Resource")
        self.assertIsNone(resource.get("index"))

    def test_type_attribute_is_emitted(self):
        xml = build_session_xml(
            "hg38",
            [{"name": "aln.bam", "path": "https://x/aln.bam", "type": "bam"}],
        )
        resource = ET.fromstring(xml).find("./Resources/Resource")
        self.assertEqual(resource.get("type"), "bam")

    def test_reference_note_emitted_as_comment(self):
        xml = build_session_xml(
            "hg38",
            [{"name": "aln.bam", "path": "https://x/aln.bam", "type": "bam"}],
            reference_note="Reference genome: Homo_sapiens/Ensembl/GRCh38",
        )
        self.assertIn("<!--", xml)
        self.assertIn("Homo_sapiens/Ensembl/GRCh38", xml)
        # Comment must not break parsing.
        self.assertIsNotNone(ET.fromstring(xml).find("./Resources/Resource"))

    def test_ampersands_in_urls_are_escaped_and_reparse(self):
        # URLs with multiple query params must produce valid XML.
        url = "https://laxy/api/v1/job/J/files/output/aln.bam?access_token=T&download=1"
        xml = build_session_xml("hg38", [{"name": "aln.bam", "path": url}])
        self.assertIn("&amp;", xml)
        # Round-trips back to the original unescaped URL.
        resource = ET.fromstring(xml).find("./Resources/Resource")
        self.assertEqual(resource.get("path"), url)
