import os
from io import StringIO
from unittest import TestCase

from ..downloader import parse_pipeline_config, get_urls_from_pipeline_config


class PipelineConfigTest(TestCase):
    def setUp(self):
        tests_path = os.path.dirname(os.path.abspath(__file__))
        self.config_json = os.path.join(tests_path, "test_data", "pipeline_config.json")
        self.config_json_b = os.path.join(
            tests_path, "test_data", "pipeline_config2.json"
        )
        self.config_json_c = os.path.join(
            tests_path, "test_data", "pipeline_config2_sane.json"
        )

    # TODO: Better test datasets might be one of these tiny yeast ones (<10,000 reads)
    # https://www.ebi.ac.uk/ena/data/warehouse/search?query=%22read_count%3C10000%20AND%20library_strategy=%22RNA-Seq%22%20AND%20tax_tree(4932)%20AND%20instrument_platform=%22ILLUMINA%22%22&domain=read
    def test_get_urls_from_config(self):
        with open(self.config_json) as fh:
            config = parse_pipeline_config(fh)
            url_filenames = get_urls_from_pipeline_config(config)
            urls = set(url_filenames.keys())
            self.assertSetEqual(
                set(
                    [
                        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz",
                        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz",
                    ]
                ),
                urls,
            )

        with open(self.config_json_b) as fh:
            config = parse_pipeline_config(fh)
            url_filenames = get_urls_from_pipeline_config(config)
            urls = set(url_filenames.keys())
            prefix = "https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l/download?path=/&files="
            self.assertSetEqual(
                set(
                    [
                        f"{prefix}SRR5963435_ss_1.fastq.gz",
                        f"{prefix}SRR5963435_ss_2.fastq.gz",
                        f"{prefix}SRR5963441_ss_1.fastq.gz",
                        f"{prefix}SRR5963441_ss_2.fastq.gz",
                    ]
                ),
                urls,
            )

        with open(self.config_json_c) as fh:
            config = parse_pipeline_config(fh)
            url_filenames = get_urls_from_pipeline_config(config)
            prefix = "https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l/download?path=/&files="

            self.assertEqual(
                url_filenames[f"{prefix}SRR5963435_ss_1.fastq.gz"], "sample1_1.fastq.gz"
            )
            self.assertEqual(
                url_filenames[f"{prefix}SRR5963435_ss_2.fastq.gz"], "sample1_2.fastq.gz"
            )
            self.assertEqual(
                url_filenames[f"{prefix}SRR5963441_ss_1.fastq.gz"], "sample2_1.fastq.gz"
            )
            self.assertEqual(
                url_filenames[f"{prefix}SRR5963441_ss_2.fastq.gz"], "sample2_2.fastq.gz"
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
