import os
from io import StringIO
from unittest import TestCase

from ..downloader import (parse_pipeline_config,
                          get_urls_from_pipeline_config)


class PipelineConfigTest(TestCase):

    def setUp(self):
        tests_path = os.path.dirname(os.path.abspath(__file__))
        self.config_json = open(os.path.join(tests_path,
                                             'test_data',
                                             'pipeline_config.json'), 'r').read()

    def test_get_urls_from_config(self):
        config_fh = StringIO(self.config_json)
        config = parse_pipeline_config(config_fh)
        urls = get_urls_from_pipeline_config(config)
        self.assertListEqual(['ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz',
                              'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz'],
                             urls)

