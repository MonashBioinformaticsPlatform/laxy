from __future__ import absolute_import
import os
import tempfile
from pathlib import Path

from django.test import TestCase

import stat
from ..utils import _generate_secret_key_file


class UtilTest(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_create_secret_file(self):
        filepath = str(Path(tempfile.gettempdir(), '.secret_key'))
        _generate_secret_key_file(filepath)

        self.assertEqual(os.stat(filepath)[stat.ST_MODE], 33152)  # 0o100600)  # -rw-------
