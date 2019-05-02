import os
from io import StringIO
from unittest import TestCase

from ..downloader import (parse_pipeline_config,
                          get_urls_from_pipeline_config)


class PipelineConfigTest(TestCase):

    def setUp(self):
        tests_path = os.path.dirname(os.path.abspath(__file__))
        self.config_json = os.path.join(tests_path,
                                        'test_data',
                                        'pipeline_config.json')
        self.config_json_b = os.path.join(tests_path,
                                          'test_data',
                                          'pipeline_config2.json')

    def test_get_urls_from_config(self):
        with open(self.config_json) as fh:
            config = parse_pipeline_config(fh)
            urls = get_urls_from_pipeline_config(config)
            self.assertListEqual(['ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz',
                                  'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz'],
                                 urls)

        with open(self.config_json_b) as fh:
            config = parse_pipeline_config(fh)
            urls = get_urls_from_pipeline_config(config)
            self.assertListEqual(
                ['https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l?path=/&files=SRR5963435_ss_1.fastq.gz',
                 'https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l?path=/&files=SRR5963435_ss_2.fastq.gz',
                 'https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l?path=/&files=SRR5963441_ss_1.fastq.gz',
                 'https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l?path=/&files=SRR5963441_ss_2.fastq.gz'],
                urls)


if __name__ == '__main__':
    import unittest

    unittest.main()
