import unittest
from unittest import TestCase
from unittest.mock import patch, MagicMock
import string
from urllib.parse import urlparse
from ..util import (
    sanitize_filename,
    truncate_fastq_to_pair_suffix,
    simplify_fastq_name,
    find_filename_and_size_from_url,
)
import requests


# Used for patching the cache_memoize decorator, so caching function calls
# doesn't interfere with testing
def no_op_decorator(*args, **kwargs):
    def inner(func):
        return func

    return inner


class UtilFunctionsTest(TestCase):
    def setUp(self):
        pass

    def test_sanitize_filename(self):
        funky_sample_name = "my sàmplé ❤😸蛇影 (A/B; C), #1.txt.gz"

        self.assertEqual(
            sanitize_filename(funky_sample_name, unicode_to_ascii=False),
            "my_sample__AB_C_1.txt.gz",
        )

        self.assertEqual(
            sanitize_filename(funky_sample_name, unicode_to_ascii=True),
            "my_sample_She_Ying_AB_C_1.txt.gz",
        )

        including_brackets = f"-_.() {string.ascii_letters}{string.digits}"
        self.assertEqual(
            sanitize_filename(
                funky_sample_name,
                valid_filename_chars=including_brackets,
                unicode_to_ascii=True,
            ),
            "my_sample_She_Ying_(AB_C)_1.txt.gz",
        )

        injection_tests = [
            ("file;ls", "filels"),
            ("file&cat /etc/passwd", "filecat_etcpasswd"),
            ("file\nrm -rf /", "file_rm_-rf_"),
            ("../../etc/passwd", "....etcpasswd"),
            ("file`whoami`", "filewhoami"),
            ("file$(whoami)", "filewhoami"),
            ("file|whoami", "filewhoami"),
            ("file||whoami", "filewhoami"),
            ("file&&whoami", "filewhoami"),
            ("file>output.txt", "fileoutput.txt"),
            ("file<input.txt", "fileinput.txt"),
        ]

        for input_name, expected_output in injection_tests:
            self.assertEqual(sanitize_filename(input_name), expected_output)

    def test_fastq_filename_mods(self):
        self.assertEqual(
            "XXX_BLA_FOO_L04_R2",
            truncate_fastq_to_pair_suffix("XXX_BLA_FOO_L04_R2_001.fastq.gz"),
        )
        self.assertEqual(
            "XXX_BLA_FOO_L04", simplify_fastq_name("XXX_BLA_FOO_L04_R2_001.fastq.gz")
        )

        self.assertEqual("XXX_BLA_FOO", simplify_fastq_name("XXX_BLA_FOO_R2.fq.gz"))
        self.assertEqual("XXX_BLA_FOO", simplify_fastq_name("XXX_BLA_FOO_2.fasta.gz"))
        self.assertEqual("XXX_BLA_FOO", simplify_fastq_name("XXX_BLA_FOO_2.fasta"))
        self.assertEqual("XXX_BLA_FOO", simplify_fastq_name("XXX_BLA_FOO_1.fastq"))


@patch("laxy_backend.util.cache_memoize", no_op_decorator)
class TestFindFilenameAndSizeFromUrl(TestCase):

    @patch("laxy_backend.util.requests.head")
    def test_http_url_with_content_disposition(self, mock_head):
        url = "https://example.com/download?file=test.txt"
        mock_response = MagicMock()
        mock_response.headers = {
            "content-disposition": 'attachment; filename="test.txt"',
            "content-length": "1024",
        }
        mock_head.return_value = mock_response

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "test.txt")
        self.assertEqual(size, 1024)

    @patch("laxy_backend.util.requests.head")
    def test_http_url_without_content_disposition(self, mock_head):
        url = "https://example.com/files/test.txt"
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_head.return_value = mock_response

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "test.txt")
        self.assertIsNone(size)

    def test_file_url(self):
        url = "file:///path/to/test.txt"
        with patch("os.path.getsize", return_value=2048):
            filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "test.txt")
        self.assertEqual(size, 2048)

    @patch("laxy_backend.util.requests.head")
    def test_url_with_query_and_fragment(self, mock_head):
        url = "https://example.com/download?file=test.txt&param=value#section"
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_head.return_value = mock_response

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "download")
        self.assertIsNone(size)

    @patch("laxy_backend.util.requests.head")
    def test_nextcloud_url(self, mock_head):
        url = "https://some-nextcloud.example.com/s/XHRYeotdqSXJ6JK/download?path=/&files=datafile_1.fastq.gz"
        mock_response = MagicMock()
        mock_response.headers = {
            "content-disposition": "attachment; filename*=UTF-8''datafile_1.fastq.gz; filename=\"datafile_1.fastq.gz\"",
            "content-length": "1048576",
        }
        mock_head.return_value = mock_response

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "datafile_1.fastq.gz")
        self.assertEqual(size, 1048576)

    @patch("laxy_backend.util.requests.head")
    def test_url_with_commas(self, mock_head):
        url = "https://example.com/download?files=file1.txt,file2.txt"
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_head.return_value = mock_response

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "download")
        self.assertIsNone(size)

    @patch("laxy_backend.util.requests.head")
    def test_http_url_with_only_query_string_filename(self, mock_head):
        url = "https://example.com/download?file=testfile.txt"

        mock_head.side_effect = [
            MagicMock(
                headers={
                    "content-length": "2048",
                }
            ),
        ]

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "download")
        self.assertEqual(size, 2048)
        self.assertEqual(mock_head.call_count, 1)

    @patch("laxy_backend.util.requests.head")
    def test_http_url_with_initial_404_then_200(self, mock_head):
        url = "https://example.com/download/test.txt"

        # Configure the mock to first raise a 404 error, then return a successful response
        # with a content-disposition header (with the authoratative filename)
        mock_head.side_effect = [
            requests.exceptions.HTTPError("404 Not Found"),
            MagicMock(
                headers={
                    "content-disposition": 'attachment; filename="success.txt"',
                    "content-length": "2048",
                }
            ),
        ]

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "success.txt")
        self.assertEqual(size, 2048)
        self.assertEqual(mock_head.call_count, 2)

    @patch("laxy_backend.util.requests_head_with_retries")
    def test_http_url_always_404(self, mock_head):
        url = "https://example.com/path/to/filename.txt"

        # Configure the mock to always raise a 404 error
        mock_head.side_effect = requests.exceptions.HTTPError("404 Not Found")

        filename, size = find_filename_and_size_from_url(url)
        self.assertEqual(filename, "filename.txt")
        self.assertIsNone(size)


if __name__ == "__main__":
    unittest.main()
