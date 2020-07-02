from unittest import TestCase
import string
from ..util import sanitize_filename


class UtilFunctionsTest(TestCase):
    def setUp(self):
        pass

    def test_sanitize_filename(self):
        horrid_sample_name = "my sàmplé ❤😸蛇影 (A/B; C), #1.txt.gz"

        self.assertEqual(
            sanitize_filename(horrid_sample_name, unicode_to_ascii=False), "my_sample__AB_C_1.txt.gz"
        )

        self.assertEqual(
            sanitize_filename(horrid_sample_name, unicode_to_ascii=True), "my_sample_She_Ying__AB_C_1.txt.gz"
        )

        including_brackets = "-_.() %s%s" % (string.ascii_letters, string.digits)
        self.assertEqual(
            sanitize_filename(
                horrid_sample_name, valid_filename_chars=including_brackets, unicode_to_ascii=True
            ),
            "my_sample_She_Ying__(AB_C)_1.txt.gz",
        )
