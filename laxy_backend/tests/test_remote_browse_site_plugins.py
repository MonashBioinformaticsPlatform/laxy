from django.test import SimpleTestCase

from laxy_backend.scraping.plugins import run_remote_browse_site_plugins
from laxy_backend.scraping.plugins.zenodo import extract_zenodo_record_id


class ExtractZenodoRecordIdTest(SimpleTestCase):
    def test_records_url(self):
        self.assertEqual(
            extract_zenodo_record_id("https://zenodo.org/records/14366711"),
            "14366711",
        )

    def test_records_url_trailing_slash(self):
        self.assertEqual(
            extract_zenodo_record_id("https://zenodo.org/records/14366711/"),
            "14366711",
        )

    def test_www_host(self):
        self.assertEqual(
            extract_zenodo_record_id("https://www.zenodo.org/records/14366711"),
            "14366711",
        )

    def test_api_records_url(self):
        self.assertEqual(
            extract_zenodo_record_id("https://zenodo.org/api/records/14366711"),
            "14366711",
        )

    def test_file_under_record(self):
        self.assertEqual(
            extract_zenodo_record_id(
                "https://zenodo.org/records/14366711/files/ARDIG49_1.fastq.gz?download=1"
            ),
            "14366711",
        )

    def test_non_zenodo_returns_none(self):
        self.assertIsNone(
            extract_zenodo_record_id("https://example.com/records/14366711"),
        )


class RunRemoteBrowseSitePluginsTest(SimpleTestCase):
    def test_unhandled_url_returns_none(self):
        listing, err = run_remote_browse_site_plugins(
            "https://example.com/data/",
            "https://example.com/data/",
        )
        self.assertIsNone(listing)
        self.assertIsNone(err)
