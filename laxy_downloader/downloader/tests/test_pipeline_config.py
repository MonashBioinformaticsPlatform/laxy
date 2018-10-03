from io import StringIO
from unittest import TestCase

from ..downloader import (parse_pipeline_config,
                          get_urls_from_pipeline_config)


class PipelineConfigTest(TestCase):

    def setUp(self):
        self.config_json = '''{"id": "GgfUrFl26fYITqSdLm5F5", "owner": "6FXt16IEZHsz430rClvy5q", 
        "params": {"genome": "Saccharomyces_cerevisiae/Ensembl/R64-1-1"}, 
        "pipeline": "rnasik", 
        "sample_set": {"id": "7I2kR9PFaIogwYFEl3fCgj", 
        "name": "CSV uploaded on 2018-09-25T04:51:13.987203", 
        "owner": "6FXt16IEZHsz430rClvy5q", 
        "samples": [{"name": "SAMN07548382", 
        "files": [
        {"R1": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz"}, 
        {"R2": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz"}], 
        "metadata": {"ena": {"fastq_ftp": 
        [{"R1": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz"}, 
        {"R2": "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz"}], 
        "fastq_md5": ["b22253620fff8f34f643a261594ce824", "4dda785e534c7c0bce46d55291b129ef"], 
        "run_alias": "GSM2752411_r1", "base_count": "7265325000", "read_count": 36326625, "broker_name": "", 
        "center_name": "GEO", "fastq_bytes": [3172059926, 3220124540], "study_alias": "GSE103004", "library_name": "", 
        "sample_alias": "GSM2752411", "run_accession": "SRR5963435", "library_layout": "PAIRED", 
        "library_source": "TRANSCRIPTOMIC", "study_accession": "PRJNA399731", "experiment_alias": "GSM2752411", 
        "instrument_model": "Illumina HiSeq 2000", "library_strategy": "RNA-Seq", "sample_accession": "SAMN07548382", 
        "library_selection": "cDNA", "instrument_platform": "ILLUMINA", "experiment_accession": "SRX3121466"}, 
        "condition": ""}}]}, "description": "more yhast laxy-compute-01 (queued)", 
        "created_time": "2018-09-25T04:51:39.618443Z", "modified_time": "2018-09-25T04:51:39.634445Z"}
        '''

    def test_get_urls_from_config(self):
        config_fh = StringIO(self.config_json)
        config = parse_pipeline_config(config_fh)
        urls = get_urls_from_pipeline_config(config)
        self.assertListEqual(['ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_1.fastq.gz',
                              'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/005/SRR5963435/SRR5963435_2.fastq.gz'],
                             urls)

