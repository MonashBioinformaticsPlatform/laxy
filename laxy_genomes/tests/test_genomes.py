"""
Tests for the ReferenceGenomesView API endpoint.

These tests use SimpleTestCase to avoid database migrations.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Setup Django before importing any Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laxy.test_settings")


# Mock jsonfield before Django imports
class MockJSONField:
    def __init__(self, *args, **kwargs):
        pass


mock_jsonfield = MagicMock()
mock_jsonfield.JSONField = MockJSONField
sys.modules["jsonfield"] = mock_jsonfield
sys.modules["jsonfield.fields"] = mock_jsonfield
sys.modules["jsonfield.forms"] = mock_jsonfield

import django

django.setup()

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status

from laxy_genomes.views import ReferenceGenomesView
from laxy_genomes.serializers import (
    ReferenceGenomeSerializer,
    ReferenceGenomeFileSerializer,
)
from laxy_genomes.data.genomes import REFERENCE_GENOMES, reference_genomes_for_api

GENOMES_API_PATH = "/api/v1/genomes/"


class ReferenceGenomeSerializerTest(SimpleTestCase):
    """Test the ReferenceGenomeSerializer."""

    def test_serialize_genome_with_id_and_organism(self):
        """Test serializing a simple genome with id and organism."""
        data = {"id": "Homo_sapiens/UCSC/hg38", "organism": "Homo sapiens"}
        serializer = ReferenceGenomeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["id"], "Homo_sapiens/UCSC/hg38")
        self.assertEqual(serializer.validated_data["organism"], "Homo sapiens")

    def test_serialize_genome_with_all_fields(self):
        """Test serializing a genome with all optional fields."""
        data = {
            "id": "Homo_sapiens/Ensembl/GRCh38.release-109",
            "organism": "Homo sapiens",
            "source": "http://example.com/source",
            "recommended": True,
            "identifiers": {"genbank": "GCA_000001405.28"},
            "checksums": {"md5": "abc123"},
            "files": [
                {
                    "location": "https://example.com/genome.fa.gz",
                    "name": "genome.fa.gz",
                    "checksum": "md5:abc123",
                    "type_tags": ["fasta"],
                }
            ],
            "tags": ["external", "rnaseq"],
        }
        serializer = ReferenceGenomeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["recommended"], True)
        self.assertEqual(len(serializer.validated_data["files"]), 1)

    def test_serialize_genome_minimal(self):
        """Test serializing a genome with only required fields."""
        data = {"id": "Test organism/Test source/Test build"}
        serializer = ReferenceGenomeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data.get("organism"))

    def test_serialize_file_with_only_location(self):
        """Test serializing a file with only location."""
        data = {"location": "https://example.com/file.txt"}
        serializer = ReferenceGenomeFileSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class ReferenceGenomesViewTest(SimpleTestCase):
    """Test the ReferenceGenomesView API endpoint."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ReferenceGenomesView.as_view()

    def test_get_genomes_returns_200(self):
        """Test that GET returns 200 status."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_genomes_returns_list(self):
        """Test that the response is a list."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        self.assertIsInstance(response.data, list)

    def test_get_genomes_returns_all_reference_genomes(self):
        """Test that all genomes from REFERENCE_GENOMES are returned."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        self.assertEqual(len(response.data), len(REFERENCE_GENOMES))

    def test_get_genomes_has_required_fields(self):
        """Test that each genome has required id and organism fields."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        for genome in response.data:
            self.assertIn("id", genome)
            self.assertIn("organism", genome)

    def test_get_genomes_id_format(self):
        """Test that genome IDs follow the expected format."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        for genome in response.data:
            self.assertIn("/", genome["id"])
            parts = genome["id"].split("/")
            self.assertGreaterEqual(len(parts), 2)

    def test_get_genomes_organism_from_id(self):
        """Test that organism is derived correctly from ID."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        for genome in response.data:
            expected_organism = genome["id"].split("/")[0].replace("_", " ")
            self.assertEqual(genome["organism"], expected_organism)

    def test_get_genomes_contains_human_reference(self):
        """Test that human reference genomes are included."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        human_ids = [g["id"] for g in response.data if "Homo_sapiens" in g["id"]]
        self.assertGreater(len(human_ids), 0)
        self.assertIn("Homo_sapiens/UCSC/hg38", human_ids)
        self.assertIn("Homo_sapiens/UCSC/hg19", human_ids)

    def test_get_genomes_contains_mouse_reference(self):
        """Test that mouse reference genomes are included."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        mouse_ids = [g["id"] for g in response.data if "Mus_musculus" in g["id"]]
        self.assertGreater(len(mouse_ids), 0)
        self.assertIn("Mus_musculus/UCSC/mm10", mouse_ids)

    def test_get_genomes_contains_yeast_reference(self):
        """Test that yeast reference genomes are included."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        yeast_ids = [
            g["id"] for g in response.data if "Saccharomyces_cerevisiae" in g["id"]
        ]
        self.assertGreater(len(yeast_ids), 0)
        self.assertIn("Saccharomyces_cerevisiae/Ensembl/R64-1-1", yeast_ids)

    def test_get_genomes_is_public(self):
        """Test that the endpoint is accessible without authentication."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_genomes_response_is_serialized(self):
        """Test that the response data matches the serializer format."""
        request = self.factory.get(GENOMES_API_PATH)
        response = self.view(request)
        for genome_data in response.data:
            serializer = ReferenceGenomeSerializer(data=genome_data)
            self.assertTrue(
                serializer.is_valid(),
                f"Serializer error: {serializer.errors} for data: {genome_data}",
            )


class ReferenceGenomesForApiTest(SimpleTestCase):
    """Tests for reference_genomes_for_api() merged metadata."""

    def test_human_grch38_release_109_has_recommended_and_files(self):
        rows = reference_genomes_for_api()
        human = next(
            g
            for g in rows
            if g["id"] == "Homo_sapiens/Ensembl/GRCh38.release-109"
        )
        self.assertTrue(human.get("recommended"))
        self.assertGreaterEqual(len(human.get("files", [])), 2)
        self.assertIn("external", human.get("tags", []))

    def test_mouse_grcm38_plain_recommended(self):
        rows = reference_genomes_for_api()
        m = next(g for g in rows if g["id"] == "Mus_musculus/Ensembl/GRCm38")
        self.assertTrue(m.get("recommended"))


class ReferenceGenomesConfigTest(SimpleTestCase):
    """Test that REFERENCE_GENOMES contains expected data."""

    def test_every_genome_has_location(self):
        for genome_id, meta in REFERENCE_GENOMES.items():
            self.assertIn(
                "location",
                meta,
                f"missing location for {genome_id!r}",
            )
            self.assertIsInstance(meta["location"], str)
            self.assertTrue(meta["location"].strip())

    def test_reference_genomes_not_empty(self):
        """Test that REFERENCE_GENOMES is not empty."""
        self.assertGreater(len(REFERENCE_GENOMES), 0)

    def test_reference_genomes_contains_human(self):
        """Test that human genome entries exist."""
        human_ids = [k for k in REFERENCE_GENOMES.keys() if "Homo_sapiens" in k]
        self.assertGreater(len(human_ids), 0)

    def test_reference_genomes_contains_mouse(self):
        """Test that mouse genome entries exist."""
        mouse_ids = [k for k in REFERENCE_GENOMES.keys() if "Mus_musculus" in k]
        self.assertGreater(len(mouse_ids), 0)

    def test_reference_genomes_id_format(self):
        """Test that all genome IDs follow the expected format."""
        for genome_id in REFERENCE_GENOMES.keys():
            parts = genome_id.split("/")
            self.assertGreaterEqual(
                len(parts),
                2,
                f"Genome ID '{genome_id}' should have at least 2 parts separated by '/'",
            )
