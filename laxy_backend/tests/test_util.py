from unittest import TestCase
import string
from ..util import sanitize_filename, truncate_fastq_to_pair_suffix, simplify_fastq_name


class UtilFunctionsTest(TestCase):
    def setUp(self):
        pass

    def test_sanitize_filename(self):
        horrid_sample_name = "my sàmplé ❤😸蛇影 (A/B; C), #1.txt.gz"

        self.assertEqual(
            sanitize_filename(horrid_sample_name, unicode_to_ascii=False),
            "my_sample__AB_C_1.txt.gz",
        )

        self.assertEqual(
            sanitize_filename(horrid_sample_name, unicode_to_ascii=True),
            "my_sample_She_Ying__AB_C_1.txt.gz",
        )

        including_brackets = "-_.() %s%s" % (string.ascii_letters, string.digits)
        self.assertEqual(
            sanitize_filename(
                horrid_sample_name,
                valid_filename_chars=including_brackets,
                unicode_to_ascii=True,
            ),
            "my_sample_She_Ying__(AB_C)_1.txt.gz",
        )

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
