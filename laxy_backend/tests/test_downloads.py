# from __future__ import absolute_import
# from compare import expect, ensure, matcher
import unittest
import os
import tempfile
from pathlib import Path

from django.test import TestCase

from ..models import Job, File, FileSet
from ..ena import get_fastq_urls, create_file_objects, create_fastq_fileset

from ..tasks.download import download_url, download_file

# from ..models import User
from django.contrib.auth import get_user_model

User = get_user_model()


class DownloadTaskTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user("adminuser", "", "testpass")
        self.admin_user.is_superuser = True
        self.admin_user.save()

        base_url = "ftp://ftp.ebi.ac.uk"

        self.file_sra_ftp = File(
            name="SRR950078_1.fastq.gz",
            location=f"{base_url}/vol1/fastq/SRR950/SRR950078/" "SRR950078_1.fastq.gz",
            # name='SRR950078_1.fastq.gz',
            owner_id=1,
        )
        self.file_sra_ftp.save()

        self.file_ftp = File(
            name="SRR4020122.fastq.gz",
            location=f"{base_url}/vol1/fastq/SRR402/002/SRR4020122/SRR4020122.fastq.gz",
            # location="ftp://ftp.gnu.org/gnu/Licenses/gpl-3.0.txt",
            # location="ftp://ftp.ubuntu.com/ubuntu/ls-lR.gz",
            # name='testfile',
            owner_id=1,
        )
        self.file_ftp.save()

        self.ena_expected_urls = [
            f"{base_url}/vol1/fastq/SRR950/SRR950078/SRR950078_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950078/SRR950078_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950079/SRR950079_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950079/SRR950079_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950080/SRR950080_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950080/SRR950080_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950081/SRR950081_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950081/SRR950081_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950082/SRR950082_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950082/SRR950082_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950083/SRR950083_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950083/SRR950083_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950084/SRR950084_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950084/SRR950084_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950085/SRR950085_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950085/SRR950085_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950086/SRR950086_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950086/SRR950086_2.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950087/SRR950087_1.fastq.gz",
            f"{base_url}/vol1/fastq/SRR950/SRR950087/SRR950087_2.fastq.gz",
        ]

    def tearDown(self):
        self.admin_user.delete()
        self.file_sra_ftp.delete()
        self.file_ftp.delete()

    def assetFileExists(self, file):
        return self.assertTrue(os.path.exists(file))

    def test_ftp_download_url(self):
        tmpfile = str(Path(tempfile.gettempdir(), self.file_ftp.name))
        fn = download_url(self.file_ftp.location, tmpfile)
        self.assertEqual(fn, tmpfile)
        self.assetFileExists(tmpfile)

    def test_ftp_download_file(self):
        # Download by File UUID (normal Celery task mode)
        fn = download_file(self.file_ftp.id)
        self.assetFileExists(fn)

        # Download by File object
        fn = download_file(self.file_ftp)
        self.assetFileExists(fn)

    def test_ena_get_fastq_urls(self):
        urls = get_fastq_urls(["PRJNA214799"])

        self.assertListEqual([k for k in urls.keys()], self.ena_expected_urls)

        urls = get_fastq_urls(["PRJNA214799", "PRJNA214799"])

        self.assertListEqual([k for k in urls.keys()], self.ena_expected_urls)

    def test_ena_create_file_objects(self):
        urls = get_fastq_urls(["PRJNA214799"])
        file_objs = create_file_objects(urls, owner=self.admin_user)

        self.assertTrue(file_objs)
        self.assertEqual(len(file_objs), 20)
        # Check objects were saved to database
        for f in file_objs:
            url = f.location
            md5 = f.checksum
            self.assertTrue(
                File.objects.filter(
                    locations__url__exact=url, checksum__exact=md5
                ).exists()
            )
            self.assertIsNotNone(f.size)

    def test_ena_create_fileset(self):
        accession = "PRJNA214799"
        fileset = create_fastq_fileset(accession, owner=self.admin_user.id, save=True)

        self.assertEqual(fileset.files.count(), 20)
        query = FileSet.objects.filter(name=accession)
        self.assertTrue(query.exists())
        self.assertEqual(query.first().files.count(), 20)
