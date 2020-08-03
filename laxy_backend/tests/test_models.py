# from __future__ import absolute_import
from collections import OrderedDict
from datetime import datetime

import unittest
import os
import random

# from compare import expect, ensure, matcher
import json
import tempfile
from pathlib import Path

import jwt

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from django.test.client import Client
from django.urls import reverse
from rest_framework.test import APIClient

from laxy_backend import models
from ..util import ordereddicts_to_dicts, laxy_sftp_url
from ..util import reverse_querystring
from ..models import Job, File, FileSet, SampleCart, ComputeResource
from ..jwt_helpers import (
    get_jwt_user_header_dict,
    make_jwt_header_dict,
    create_jwt_user_token,
)

# from ..models import User
from django.contrib.auth import get_user_model

User = get_user_model()


# from ..authorization import JWTAuthorizedClaimPermission


def _create_user_and_login(username="testuser", password="testpass", is_superuser=True):
    admin_user = User.objects.create_user(username, "", password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = APIClient(HTTP_CONTENT_TYPE="application/json")
    client.login(username=username, password=password)
    return (admin_user, client)


class FileModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user("adminuser", "", "testpass")
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.user = User.objects.create_user("testuser", "", "testpass")
        self.user.is_superuser = False
        self.user.save()

        self.file_sra_ftp = File(
            location="ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR950/SRR950078/"
            "SRR950078_1.fastq.gz",
            owner_id=self.user.id,
        )
        self.file_sra_ftp.save()

        self.file_ftp = File(
            location="ftp://ftp.monash.edu.au/pub/linux/debian/ls-lR.gz",
            owner_id=self.user.id,
        )
        self.file_ftp.save()

        self.file_complex_http = File(
            location="https://example.com:8000/fastq/"
            "sample1_R1.fastq.gz"
            "#hashpart"
            "?format=gz&shuffle=yes",
            owner_id=self.user.id,
        )
        self.file_complex_http.save()

    def tearDown(self):
        self.admin_user.delete()
        self.user.delete()
        self.file_sra_ftp.delete()
        self.file_ftp.delete()
        self.file_complex_http.delete()

    def assertListSameItems(self, list1, list2, msg=None):
        return self.assertListEqual(sorted(list1), sorted(list2), msg=msg)
        # if len(list1) != len(list2):
        #     raise AssertionError("Lists are different lengths.")
        # return self.assertSetEqual(set(list1), set(list2), msg=msg)

    def test_file_location(self):
        url = "ftp://ftp.sra.ebi.ac.uk.example.com/vol1/fastq/SRR950/SRR950078/SRR950078_1.fastq.gz"
        a_file = File(location=url, owner_id=self.user.id,)

        self.assertEqual(a_file.location, url)
        # We shouldn't have any concrete FileLocation records in the db until the File is saved
        self.assertEqual(a_file.locations.count(), 0)
        # File.name is auto-populated from location
        self.assertEqual(a_file.name, "SRR950078_1.fastq.gz")

        a_file.save()
        self.assertEqual(a_file.location, url)
        # After saving we should have an associated FileLocation record in the db
        self.assertEqual(a_file.locations.count(), 1)
        self.assertEqual(a_file.locations.all()[0].url, url)
        self.assertEqual(a_file.name, "SRR950078_1.fastq.gz")

        # Now set a new location. Post-save, ensure it becomes the default.
        # The old location should still maintained under File.locations
        new_url = "ftp://ftp.monash.edu.au.example.com/pub/linux/debian/ls-lR.gz"
        a_file.location = new_url
        # Only one location in the database prior to save
        self.assertEqual(a_file.locations.count(), 1)
        a_file.save()
        # Both locations are in the database after save
        self.assertEqual(a_file.locations.count(), 2)
        self.assertEqual(a_file.location, new_url)
        self.assertListEqual(
            sorted([loc.url for loc in a_file.locations.all()]), sorted([url, new_url])
        )
        self.assertTrue(a_file.locations.filter(url=new_url).first().default)
        # Old location should no longer be defau;t
        self.assertFalse(a_file.locations.filter(url=url).first().default)

        # After calling set_as_default, the original location should be the only default
        a_file.locations.filter(url=url).first().set_as_default(save=True)
        self.assertTrue(a_file.locations.filter(url=url).first().default)
        self.assertFalse(a_file.locations.filter(url=new_url).first().default)

    def test_file_explicit_name_overrides_inferred_name_from_location(self):
        url = "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR950/SRR950078/SRR950078_2.fastq.gz"
        a_file = File(location=url, owner_id=self.user.id, name="a_file.fastq.gz")

        self.assertEqual(a_file.name, "a_file.fastq.gz")  # not 'SRR950078_1.fastq.gz'
        self.assertEqual(
            a_file.path, "/vol1/fastq/SRR950/SRR950078"
        )  # inferred automatically from location

        # Nothing should change after saving, no weird side-effects
        a_file.save()
        self.assertEqual(a_file.name, "a_file.fastq.gz")
        self.assertEqual(a_file.path, "/vol1/fastq/SRR950/SRR950078")

    def test_filename_guessing(self):
        self.assertEqual(self.file_sra_ftp.name, "SRR950078_1.fastq.gz")
        self.assertEqual(self.file_ftp.name, "ls-lR.gz")
        self.assertEqual(self.file_complex_http.name, "sample1_R1.fastq.gz")

    def test_fileobj_from_http_url(self):
        f = File(
            location="https://www.apache.org/licenses/LICENSE-2.0.txt",
            owner=User.objects.get(username="testuser"),
        )
        content = f.file.read().decode()
        lines = content.splitlines()
        self.assertEqual(lines[1].strip(), "Apache License")

    @unittest.skip("Test not implemented")
    def test_fileobj_from_laxysftp_url(self):
        f = File(
            location=laxy_sftp_url(job, "output.txt"),
            owner=User.objects.get(username="testuser"),
        )
        content = f.file.read().decode()
        raise NotImplementedError()

    def test_add_remove_type_tags(self):
        f = File(
            location="https://www.apache.org/licenses/LICENSE-2.0.txt",
            owner=User.objects.get(username="testuser"),
        )

        # Removing non-existant tags does nothing
        f.remove_type_tag(["test2", "licence"])
        self.assertListSameItems(f.type_tags, [])

        # Add a single tag (as a string)
        f.add_type_tag("text/plain")
        self.assertListSameItems(f.type_tags, ["text/plain"])

        # Add multiple tags (list of strings)
        f.add_type_tag(["license", "test", "test2"])
        self.assertListSameItems(
            f.type_tags, ["text/plain", "license", "test", "test2"]
        )

        # Add a tag a second time - list should not contain duplicates
        f.add_type_tag("text/plain")
        self.assertListEqual(
            sorted(f.type_tags), sorted(["text/plain", "license", "test", "test2"])
        )

        # Remove a single tag
        f.remove_type_tag("test")
        self.assertListSameItems(f.type_tags, ["text/plain", "license", "test2"])

        # Check that the changes were saved to the database
        newf = File.objects.get(id=f.id)
        self.assertListSameItems(newf.type_tags, ["text/plain", "license", "test2"])

        # Remove multiple tags
        f.remove_type_tag(["test2", "license"])
        self.assertListSameItems(f.type_tags, ["text/plain"])


class FileSetModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "", "testpass")
        self.user.is_superuser = False
        self.user.save()

        self.file_a = File(
            owner=self.user, name="file_a", location="file:///tmp/file_a"
        )
        self.file_b = File(
            owner=self.user, name="file_b", location="file:///tmp/file_b"
        )
        self.file_a.save()
        self.file_b.save()

        # Unsaved Files have no primary key (until saved)
        self.file_c_unsaved = File(
            owner=self.user, name="file_c", location="file:///tmp/file_c"
        )
        self.file_d_unsaved = File(
            owner=self.user, name="file_d", location="file:///tmp/file_d"
        )

        self.fileset = FileSet(name="test-fileset-1", owner=self.user)

    def tearDown(self):
        self.user.delete()
        try:
            self.file_a.delete()
        except:
            pass
        try:
            self.file_b.delete()
        except:
            pass
        self.fileset.delete()

    def test_fileset(self):
        id_list = sorted([self.file_a.id, self.file_b.id])

        fileset = self.fileset
        file_a = self.file_a
        file_b = self.file_b

        # Add Files to a FileSet
        fileset.add(file_a)
        self.assertIn(file_a, list(fileset.files.all()))
        self.assertNotIn(file_b, list(fileset.files.all()))
        fileset.add(file_b)
        self.assertIn(file_b, list(fileset.files.all()))

        # Adding twice shouldn't create duplicates in the file list
        fileset.add([file_a, file_b])
        self.assertListEqual(id_list, sorted([f.id for f in fileset.files.all()]))
        fileset.add([file_a, file_a, file_a])
        self.assertListEqual(id_list, sorted([f.id for f in fileset.files.all()]))

        # Remove files from a FileSet
        self.fileset.remove(file_b)
        self.assertNotIn(file_b, list(fileset.files.all()))
        self.fileset.remove(file_a)
        self.assertNotIn(file_a, list(fileset.files.all()))

        # The delete flag removes the associated File record
        fileset.add([file_a, file_b])
        fileset.remove(file_a, delete=True)
        with self.assertRaises(ObjectDoesNotExist):
            db_file_a = File.objects.get(id=file_a.id)
        # No exception, file_b should still exist
        db_file_b = File.objects.get(id=file_b.id)

        fileset.add([self.file_c_unsaved, self.file_d_unsaved])
        self.assertIn(self.file_c_unsaved, list(fileset.files.all()))
        self.assertIn(self.file_d_unsaved, list(fileset.files.all()))


class SampleCartTest(TestCase):
    def setUp(self):
        self.csv_text = """SampleA,ftp://ftp.example.com/pub/bla_lane1_R1.fastq.gz,ftp://ftp.example.com/pub/bla_lane1_R2.fastq.gz
SampleA, ftp://ftp.example.com/pub/bla_lane2_R1.fastq.gz, ftp://ftp.example.com/pub/bla_lane2_R2.fastq.gz
SampleB,ftp://ftp.example.com/pub/bla2_R1_001.fastq.gz,ftp://ftp.example.com/pub/bla2_R2_001.fastq.gz
       ,ftp://ftp.example.com/pub/bla2_R1_002.fastq.gz,ftp://ftp.example.com/pub/bla2_R2_002.fastq.gz
SampleC,ftp://ftp.example.com/pub/foo2_lane4_1.fastq.gz,ftp://ftp.example.com/pub/foo2_lane4_2.fastq.gz
SampleC,ftp://ftp.example.com/pub/foo2_lane5_1.fastq.gz,ftp://ftp.example.com/pub/foo2_lane5_2.fastq.gz

"""

        self.sample_list = [
            {
                "name": "SampleA",
                "files": [
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/bla_lane1_R1.fastq.gz",
                            "name": "bla_lane1_R1.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/bla_lane1_R2.fastq.gz",
                            "name": "bla_lane1_R2.fastq.gz",
                        },
                    ),
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/bla_lane2_R1.fastq.gz",
                            "name": "bla_lane2_R1.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/bla_lane2_R2.fastq.gz",
                            "name": "bla_lane2_R2.fastq.gz",
                        },
                    ),
                ],
            },
            {
                "name": "SampleB",
                "files": [
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/bla2_R1_001.fastq.gz",
                            "name": "bla2_R1_001.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/bla2_R2_001.fastq.gz",
                            "name": "bla2_R2_001.fastq.gz",
                        },
                    ),
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/bla2_R1_002.fastq.gz",
                            "name": "bla2_R1_002.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/bla2_R2_002.fastq.gz",
                            "name": "bla2_R2_002.fastq.gz",
                        },
                    ),
                ],
            },
            {
                "name": "SampleC",
                "files": [
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/foo2_lane4_1.fastq.gz",
                            "name": "foo2_lane4_1.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/foo2_lane4_2.fastq.gz",
                            "name": "foo2_lane4_2.fastq.gz",
                        },
                    ),
                    OrderedDict(
                        R1={
                            "location": "ftp://ftp.example.com/pub/foo2_lane5_1.fastq.gz",
                            "name": "foo2_lane5_1.fastq.gz",
                        },
                        R2={
                            "location": "ftp://ftp.example.com/pub/foo2_lane5_2.fastq.gz",
                            "name": "foo2_lane5_2.fastq.gz",
                        },
                    ),
                ],
            },
        ]

        self.from_csv_text = """SampleA,ftp://ftp.example.com/pub/bla_lane1_R1.fastq.gz,ftp://ftp.example.com/pub/bla_lane1_R2.fastq.gz
SampleA,ftp://ftp.example.com/pub/bla_lane2_R1.fastq.gz,ftp://ftp.example.com/pub/bla_lane2_R2.fastq.gz
SampleB,ftp://ftp.example.com/pub/bla2_R1_001.fastq.gz,ftp://ftp.example.com/pub/bla2_R2_001.fastq.gz
SampleB,ftp://ftp.example.com/pub/bla2_R1_002.fastq.gz,ftp://ftp.example.com/pub/bla2_R2_002.fastq.gz
SampleC,ftp://ftp.example.com/pub/foo2_lane4_1.fastq.gz,ftp://ftp.example.com/pub/foo2_lane4_2.fastq.gz
SampleC,ftp://ftp.example.com/pub/foo2_lane5_1.fastq.gz,ftp://ftp.example.com/pub/foo2_lane5_2.fastq.gz
"""

    def tearDown(self):
        pass

    def test_from_csv(self):
        samplecart = SampleCart()
        samplecart.from_csv(self.csv_text, save=False)

        self.assertListEqual(samplecart.samples, self.sample_list)

    def test_to_csv(self):
        samplecart = SampleCart()
        samplecart.from_csv(self.csv_text, save=False)
        csv_txt = samplecart.to_csv()
        self.assertListEqual(self.from_csv_text.splitlines(), csv_txt.splitlines())


class JobModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user("adminuser", "", "testpass")
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.user = User.objects.create_user("testuser", "", "testpass")
        self.user.is_superuser = False
        self.user.save()

        self.compute = ComputeResource(
            owner=self.user,
            host="127.0.0.1",
            disposable=False,
            status=ComputeResource.STATUS_ONLINE,
            name="default",
            extra={},
        )

        self.job_one = Job(
            owner=self.user,
            status=Job.STATUS_COMPLETE,
            remote_id="999",
            exit_code=0,
            params={},
            compute_resource=self.compute,
            completed_time=datetime.now(),
        )

    def tearDown(self):
        self.compute.delete()
        self.job_one.delete()
        self.admin_user.delete()
        self.user.delete()

    def _assert_add_files_from_tsv(self, job):
        self.assertEqual(job.input_files.files.count(), 3)
        self.assertEqual(job.output_files.files.count(), 2)
        self.assertListEqual(
            sorted([c.checksum for c in job.input_files.get_files()]),
            sorted(
                [
                    "md5:7d9960c77b363e2c2f41b77733cf57d4",
                    "md5:d0cfb796d371b0182cd39d589b1c1ce3",
                    "md5:a97e04b6d1a0be20fcd77ba164b1206f",
                ]
            ),
        )
        # FileSet.get_files() returns sorted by path/name, so the second file
        # is 'sample2_R2.fastq.gz'.
        s2_r2 = job.input_files.get_files()[1]
        self.assertEqual(s2_r2.name, "sample2_R2.fastq.gz")
        self.assertEqual(s2_r2.path, "input/some_dir")
        self.assertListEqual(
            job.output_files.get_files()[0].type_tags, ["bai", "jbrowse"]
        )

    def test_add_files_from_tsv(self):
        # Note that we use commas for the list in the type_tags column (and don't require quotes around it)
        tsv = [
            b"filepath\tchecksum\ttype_tags\tmetadata\n",
            b"input/some_dir/table.txt \tmd5:7d9960c77b363e2c2f41b77733cf57d4 \ttext,csv,google-sheets\t{}\n",
            b"input/some_dir/sample1_R2.fastq.gz\tmd5:d0cfb796d371b0182cd39d589b1c1ce3\tfastq\t{}\n",
            b"input/some_dir/sample2_R2.fastq.gz\tmd5:a97e04b6d1a0be20fcd77ba164b1206f\tfastq\t{}\n",
            b'output/sample2/alignments/sample2.bam\tmd5:7c9f22c433ae679f0d82b12b9a71f5d3\tbam,alignment,bam.sorted,jbrowse\t{"some": "metdatas"}\n',
            b"output/sample2/alignments/sample2.bai\tmd5:e57ea180602b69ab03605dad86166fa7\tbai,jbrowse\t{}\n",
        ]
        tsv = b"".join(tsv)

        self.job_one.add_files_from_tsv(tsv, save=True)
        self.job_one.save()
        updated = Job.objects.get(id=self.job_one.id)
        self._assert_add_files_from_tsv(updated)

    def test_add_files_from_csv(self):
        # Note: we require quotes in the type_tags column due to nested comma-separated list
        csv = [
            b"checksum,filepath,metadata,type_tags\n",
            b'md5:7d9960c77b363e2c2f41b77733cf57d4,input/some_dir/table.txt,{},"text,csv,google-sheets"\n',
            b"md5:d0cfb796d371b0182cd39d589b1c1ce3,input/some_dir/sample1_R2.fastq.gz,{},fastq\n",
            b"md5:a97e04b6d1a0be20fcd77ba164b1206f,input/some_dir/sample2_R2.fastq.gz,{},fastq\n",
            b'md5:7c9f22c433ae679f0d82b12b9a71f5d3,output/sample2/alignments/sample2.bam,{"some": "metdatas"},"bam ,alignment, bam.sorted, jbrowse"\n',
            b'md5:e57ea180602b69ab03605dad86166fa7,output/sample2/alignments/sample2.bai,{},"bai,jbrowse"\n',
        ]
        csv = b"".join(csv)

        self.job_one.add_files_from_tsv(csv, save=True)
        self.job_one.save()
        updated = Job.objects.get(id=self.job_one.id)
        self._assert_add_files_from_tsv(updated)
