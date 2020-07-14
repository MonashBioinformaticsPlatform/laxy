# from __future__ import absolute_import
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
from rest_framework.test import APIClient, RequestsClient

from laxy_backend import util
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
from laxy_backend.views import add_sanitized_names_to_samplecart_json

User = get_user_model()


def get_tmp_dir():
    dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
    os.makedirs(dir, exist_ok=True)
    return dir


def _create_user_and_login(username="testuser", password="testpass", is_superuser=True):
    admin_user = User.objects.create_user(username, "", password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = APIClient(HTTP_CONTENT_TYPE="application/json")
    client.login(username=username, password=password)
    return (admin_user, client)


class FileViewTest(TestCase):
    def setUp(self):
        user, user_client = _create_user_and_login(
            "user1", "userpass1", is_superuser=False
        )
        self.user = user
        self.user_client = user_client

        self.file_a = File(
            owner=self.user,
            # no name to test File.name() property serialization
            # name="file_a",
            location="file:///tmp/file_a",
        )
        self.file_b = File(
            owner=self.user, name="file_b", location="file:///tmp/file_b"
        )
        self.file_a.save()
        self.file_b.save()

        self.file_on_disk_content = b"test data\nline 2\n"
        self.file_on_disk_b64md5 = "nROVtwU1zae3eOK/dZyRZw=="
        self.job_dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
        self.job_output_dir = os.path.join(self.job_dir, "output")
        os.makedirs(self.job_output_dir, exist_ok=True)
        fd, fpath = tempfile.mkstemp(dir=self.job_output_dir)
        os.write(fd, self.file_on_disk_content)
        os.close(fd)

        self.file_on_disk = File(
            location=f"file://{fpath}",
            name=Path(fpath).name,
            path=Path(fpath).parent,
            checksum="md5:9d1395b70535cda7b778e2bf759c9167",
            type_tags=["text", "test"],
            owner_id=self.user.id,
        )
        self.file_on_disk.save()

    def tearDown(self):
        self.user.delete()
        self.file_a.delete()
        self.file_b.delete()
        self.file_on_disk.delete()

    def test_create_file(self):
        job_json = {
            "location": "http://example.com/file_examp.txt",
            "checksum": "xxh64:c70492d07ce72425",
            "metadata": {"tags": ["text", "interesting"]},
        }

        response = self.user_client.post(
            reverse("laxy_backend:create_file"), data=job_json, format="json",
        )

        self.assertEqual(response.status_code, 200)
        file_id = response.data.get("id")
        new_file = File.objects.get(id=file_id)
        self.assertEqual(new_file.location, "http://example.com/file_examp.txt")
        # Note how the name get's automatically assigned based on the URL
        # (if possible)
        self.assertEqual(new_file.name, "file_examp.txt")
        self.assertEqual(new_file.checksum, "xxh64:c70492d07ce72425")
        self.assertEqual(new_file.owner, self.user)
        self.assertDictEqual(new_file.metadata, {"tags": ["text", "interesting"]})

    def test_create_file_with_scheme_file(self):
        job_json = {
            "location": "file:///tmp/file_on_disk.txt",
        }

        response = self.user_client.post(
            reverse("laxy_backend:create_file"),
            data=json.dumps(job_json),
            content_type="application/json",
        )

        # TODO: for some reason file:// URLs are giving a validation error,
        #       returning 400
        import sys

        sys.stderr.write(json.dumps(response.data, indent=2))
        self.assertEqual(response.status_code, 200)

    def test_get_file_unauthenticated(self):
        client = APIClient()
        response = client.get(
            reverse("laxy_backend:file", args=[self.file_a.uuid()]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_get_file(self):
        response = self.user_client.get(
            reverse("laxy_backend:file", args=[self.file_a.uuid()]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        json_data = response.data
        self.assertEqual(json_data.get("id"), self.file_a.id)
        self.assertEqual(json_data.get("location"), "file:///tmp/file_a")
        self.assertEqual(json_data.get("checksum"), None)
        self.assertEqual(json_data.get("metadata"), {})

    def test_update_file_checksum(self):
        new_checksum = "md5:cbda22bcb41ab0151b438589aa4637e2"
        response = self.user_client.patch(
            reverse("laxy_backend:file", args=[self.file_a.uuid()]),
            data=json.dumps({"checksum": new_checksum}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)

        updated_file = File.objects.get(id=self.file_a.id)
        self.assertEqual(updated_file.checksum, new_checksum)

    def test_update_file_id_attempt(self):
        new_id = "some_UUID_string"
        response = self.user_client.patch(
            reverse("laxy_backend:file", args=[self.file_a.uuid()]),
            data=json.dumps({"id": new_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_create_patch_file_metadata_RFC7386(self):
        file_c = File(
            owner=self.user,
            name="file_RFC7386",
            path="tmp",
            location="file:///tmp/file_RFC7386",
            metadata={"tags": ["A", "B"], "size": 3142},
        )
        file_c.save()

        original_metdata = dict(file_c.metadata)
        patch = json.loads('{"size": null, "tags": ["D"]}')
        response = self.user_client.patch(
            reverse("laxy_backend:file", args=[file_c.id]),
            data=json.dumps({"metadata": patch}),
            content_type="application/merge-patch+json",
        )

        self.assertEqual(response.status_code, 204)

        obj = File.objects.get(name="file_RFC7386")
        self.assertDictEqual(obj.metadata, {"tags": ["D"]})

    def test_create_patch_file_metadata_RFC6902(self):
        file_c = File(
            owner=self.user,
            name="file_RFC6902",
            path="tmp",
            location="file:///tmp/file_RFC6902",
            metadata={"tags": ["A", "B"], "size": 3142},
        )
        file_c.save()

        patch = json.loads('[{ "op": "add", "path": "/tags/2", "value": "C" }]')
        response = self.user_client.patch(
            reverse("laxy_backend:file", args=[file_c.id]),
            data=json.dumps({"metadata": patch}),
            content_type="application/json-patch+json",
        )

        self.assertEqual(response.status_code, 204)

        obj = File.objects.get(name="file_RFC6902")
        self.assertDictEqual(obj.metadata, {"size": 3142, "tags": ["A", "B", "C"]})

    def test_file_view_octet_stream(self):
        response = self.user_client.get(
            reverse("laxy_backend:file", args=[self.file_on_disk.uuid()]),
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-disposition"], f"inline")
        self.assertEqual(response["digest"], f"MD5={self.file_on_disk_b64md5}")

        content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_download_octet_stream(self):
        url = reverse("laxy_backend:file", args=[self.file_on_disk.uuid()])
        response = self.user_client.get(
            f"{url}?download", content_type="application/octet-stream"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["content-disposition"],
            f'attachment; filename="{self.file_on_disk.name}"',
        )
        self.assertEqual(response["digest"], f"MD5={self.file_on_disk_b64md5}")

        content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_view_content(self):
        url = reverse(
            "laxy_backend:file_download",
            args=[self.file_on_disk.uuid(), self.file_on_disk.name],
        )
        response = self.user_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-disposition"], f"inline")
        self.assertEqual(response["digest"], f"MD5={self.file_on_disk_b64md5}")

        content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_download_content(self):
        url = reverse(
            "laxy_backend:file_download",
            args=[self.file_on_disk.uuid(), self.file_on_disk.name],
        )
        response = self.user_client.get(f"{url}?download")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["content-disposition"],
            f'attachment; filename="{self.file_on_disk.name}"',
        )
        self.assertEqual(response["digest"], f"MD5={self.file_on_disk_b64md5}")

        content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_job_file_download_content(self):
        compute = ComputeResource(
            host="localhost", status="online", owner=self.user, disposable=False
        )
        compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.add(self.file_on_disk)
        output_files.save()

        job = Job(
            input_files=input_files,
            output_files=output_files,
            owner=self.user,
            compute_resource=compute,
        )
        job.save()

        url = reverse(
            "laxy_backend:job_file", args=[job.id, f"{self.file_on_disk.full_path}"]
        )
        response = self.user_client.get(f"{url}?download")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["content-disposition"],
            f'attachment; filename="{self.file_on_disk.name}"',
        )
        self.assertEqual(response["digest"], f"MD5={self.file_on_disk_b64md5}")

        content = b"".join([chunk for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_job_file_put(self):
        compute = ComputeResource(
            host="localhost", status="online", owner=self.user, disposable=False
        )
        compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.save()

        job = Job(
            input_files=input_files,
            output_files=output_files,
            owner=self.user,
            compute_resource=compute,
        )
        job.save()

        # On a compute node, we only specify the path relative to the
        # job directory.
        frelpath = Path(self.file_on_disk.full_path).relative_to(self.job_dir)
        url = reverse("laxy_backend:job_file", args=[job.id, frelpath])
        response = self.user_client.put(
            url,
            data=json.dumps(
                {  # no location field, will be generated by server
                    "checksum": self.file_on_disk.checksum_hash,
                    "metadata": {},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        f_obj = File.objects.get(id=response.data.get("id"))
        laxified_url = laxy_sftp_url(job, frelpath)
        self.assertEqual(f_obj.location, laxified_url)
        job = Job.objects.get(id=job.id)
        self.assertEqual(f_obj, job.output_files.get_files().first())

        # A second PUT should replace the File record generated in the previous
        # request.
        response = self.user_client.put(
            url,
            data=json.dumps(
                {"checksum": self.file_on_disk.checksum_hash, "metadata": {}}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        job = Job.objects.get(id=job.id)
        self.assertEqual(laxified_url, job.output_files.get_files().first().location)


class JobViewTest(TestCase):
    def setUp(self):
        admin_user, authenticated_client = _create_user_and_login()
        self.admin_user = admin_user
        self.admin_authenticated_client = authenticated_client

        self.compute = ComputeResource(
            owner=self.admin_user,
            host="127.0.0.1",
            disposable=False,
            status=ComputeResource.STATUS_ONLINE,
            name="default",
            extra={"base_dir": get_tmp_dir()},
        )
        self.compute.save()

        self.admin_job = Job(owner=admin_user, params='{"bla":"foo"}')
        self.admin_job.save()

        user, user_client = _create_user_and_login(
            "user1", "userpass1", is_superuser=False
        )
        self.user = user
        self.user_client = user_client

        self.user_job = Job(owner=user, params='{"bing":"bang"}')
        self.user_job.save()

        self.job_with_compute = Job(
            owner=user, params='{"bing":"bang"}', compute_resource=self.compute
        )
        self.job_with_compute.save()

    def tearDown(self):
        self.admin_job.delete()
        self.admin_user.delete()

    def test_unauthenticated_access(self):
        client = APIClient(HTTP_CONTENT_TYPE="application/json")
        response = client.get(reverse("laxy_backend:job", args=[self.admin_job.uuid()]))
        self.assertEqual(response.status_code, 401)

        response = client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            data={"status": Job.STATUS_COMPLETE},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.admin_job.status, Job.STATUS_CREATED)

    def test_admin_authenticated_access(self):
        response = self.admin_authenticated_client.get(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_authenticated_patch(self):
        response = self.admin_authenticated_client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            data=json.dumps({"status": Job.STATUS_COMPLETE}),
            content_type="application/json",
        )

        # we need to re-get the job to see the changes made by the request
        j = Job.objects.get(id=self.admin_job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_COMPLETE)

    def test_patch_exit_code(self):
        # set both status and exit_code
        response = self.admin_authenticated_client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            data=json.dumps({"status": Job.STATUS_CANCELLED, "exit_code": 99}),
            content_type="application/json",
        )

        # we need to re-get the job to see the changes made by the request
        j = Job.objects.get(id=self.admin_job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_CANCELLED)
        self.assertEqual(j.exit_code, 99)

        # set only exit_code, status gets set automatically
        response = self.admin_authenticated_client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            data=json.dumps({"exit_code": 0}),
            content_type="application/json",
        )

        j = Job.objects.get(id=self.admin_job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_COMPLETE)
        self.assertEqual(j.exit_code, 0)

        # set only non-zero exit_code, status gets set to failed automatically
        response = self.admin_authenticated_client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            data=json.dumps({"exit_code": 1}),
            content_type="application/json",
        )

        j = Job.objects.get(id=self.admin_job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_FAILED)
        self.assertEqual(j.exit_code, 1)

    def test_verify_jwt_token(self):
        token = create_jwt_user_token("testuser")[0]
        client = APIClient(HTTP_CONTENT_TYPE="application/json")
        response = client.post(
            reverse("laxy_backend:jwt-verify-token"),
            data={"token": token},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    @unittest.skip("Feature not implemented")
    def test_jwt_object_level_access(self):
        # TODO: This intention of this feature is that
        #       a JWT encodes the id and ContentType of an object
        #       (eg, a Job UUID and ContentType 'job'), but no
        #       specific user. The bearer of the token can modify the
        #       named object (until the token expires).
        #
        #       The goal is to allow remote compute resources to make /job/
        #       API calls to modify only the job they have been given access
        #       to. The alternative would be to do this via /event/ API call,
        #       possibily using the JWT as the secret (and encoding
        #       Authorization to modify a target object as a side effect).
        from ..jwt_helpers import create_object_access_jwt

        jwt_header = make_jwt_header_dict(create_object_access_jwt(self.user_job))
        # jwt_header = {'HTTP_AUTHORIZATION': jwt_header['Authorization']}
        # jwt_client = Client()

        client = APIClient(HTTP_CONTENT_TYPE="application/json")
        client.credentials(HTTP_AUTHORIZATION=jwt_header["Authorization"])

        response = client.get(
            reverse("laxy_backend:job", args=[self.user_job.uuid()]), format="json"
        )
        self.assertEqual(response.status_code, 200)

        response = client.patch(
            reverse("laxy_backend:job", args=[self.user_job.uuid()]),
            {"status": Job.STATUS_COMPLETE},
            format="json",
        )
        self.assertEqual(response.status_code, 204)

        response = client.patch(
            reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
            {"status": Job.STATUS_COMPLETE},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        client.credentials(HTTP_AUTHORIZATION="Bearer __invalid_jwt__")
        with self.assertRaises(jwt.exceptions.DecodeError):
            response = client.patch(
                reverse("laxy_backend:job", args=[self.admin_job.uuid()]),
                {"status": Job.STATUS_COMPLETE},
                format="json",
            )

    def test_jwt_auth_access(self):
        jwt_header = get_jwt_user_header_dict("user1")
        client = APIClient(HTTP_CONTENT_TYPE="application/json")
        client.credentials(HTTP_AUTHORIZATION=jwt_header["Authorization"])
        url = reverse("laxy_backend:job", args=[self.user_job.uuid()])
        response = client.get(url, format="json")
        self.assertEqual(response.status_code, 200)

    def test_jwt_auth_access_user_attempt_unowned(self):
        jwt_header = get_jwt_user_header_dict("user1")
        client = APIClient(HTTP_CONTENT_TYPE="application/json")
        client.credentials(HTTP_AUTHORIZATION=jwt_header["Authorization"])
        # Attempt access to job owned by admin
        url = reverse("laxy_backend:job", args=[self.admin_job.uuid()])
        response = client.get(url, format="json")
        self.assertEqual(response.status_code, 404)

    def test_jwt_auth_access_non_existant_user(self):
        with self.assertRaises(User.DoesNotExist):
            jwt_header = get_jwt_user_header_dict("easterbunny")

    @unittest.skip("JobSerializer functionality incomplete")
    def test_jobserializer(self):
        raise NotImplementedError()
        # The JobSerializer should:
        # * allow either an array of file objects via input_files OR an existing
        #   input_fileset_id, but not both.
        # * when specifying an input_fileset_id, a non-empty input_files
        #   value should raise an error (ValidationError).
        # * when specifying input_files, also setting input_fileset_id
        #   should raise an error (ValidationError).
        # * when input_fileset_id is not specified, a new fileset containing the
        #   is files in input_files should be created.
        # * file objects specified in input_files should have only the id set,
        #   OR only other fields set (name, checksum, location). If both id and
        #   another field are set, an error should be raised (ValidationError).
        # * file objects specified by id only must exist in the database
        # * file objects specified without an id, but with other fields
        #   (name, checksum, location) should be created.

    def test_job_files_from_csv(self):
        csv = [
            b"checksum,filepath,metadata,type_tags\n",
            b'md5:7d9960c77b363e2c2f41b77733cf57d4,input/some_dir/table.txt,{},"text,csv,google-sheets"\n',
            b"md5:d0cfb796d371b0182cd39d589b1c1ce3,input/some_dir/sample1_R2.fastq.gz,{},fastq\n",
            b"md5:a97e04b6d1a0be20fcd77ba164b1206f,input/some_dir/sample2_R2.fastq.gz,{},fastq\n",
            b'md5:7c9f22c433ae679f0d82b12b9a71f5d3,output/sample2/alignments/sample2.bam,{"some": "metdatas"},"bam ,alignment, bam.sorted, jbrowse"\n',
            b'md5:e57ea180602b69ab03605dad86166fa7,output/sample2/alignments/sample2.bai,{},"bai,jbrowse"\n',
        ]
        csv = b"".join(csv)

        client = Client()
        login_url = reverse("laxy_backend:api_login")
        response = client.post(
            login_url, {"username": self.user.username, "password": "userpass1"}
        )

        # client = APIClient(HTTP_CONTENT_TYPE='text/csv')
        # client.force_authenticate(self.user.username)
        url = reverse("laxy_backend:job_file_bulk", args=[self.job_with_compute.id])
        response = client.post(url, data=csv, content_type="text/csv; charset=utf-8")
        self.assertEqual(response.status_code, 200)
        job = Job.objects.get(id=self.job_with_compute.id)
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

    def test_job_files_from_csv_with_location(self):
        csv = [
            b"checksum,filepath,location,metadata,type_tags\n",
            b'md5:f38d1191da1380c7aea5f6e800f05a68,input/SRR5963436_1.fastq.gz,ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/006/SRR5963436/SRR5963436_1.fastq.gz,{},"fastq,ena"\n',
        ]
        csv = b"".join(csv)

        client = Client()
        login_url = reverse("laxy_backend:api_login")
        response = client.post(
            login_url, {"username": self.user.username, "password": "userpass1"}
        )

        # client = APIClient(HTTP_CONTENT_TYPE='text/csv')
        # client.force_authenticate(self.user.username)
        url = reverse("laxy_backend:job_file_bulk", args=[self.job_with_compute.id])
        response = client.post(url, data=csv, content_type="text/csv; charset=utf-8")
        self.assertEqual(response.status_code, 200)
        job = Job.objects.get(id=self.job_with_compute.id)
        self.assertEqual(job.input_files.files.count(), 1)
        self.assertEqual(job.output_files.files.count(), 0)
        self.assertListEqual(
            [c.location for c in job.input_files.get_files()],
            [
                "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR596/006/SRR5963436/SRR5963436_1.fastq.gz"
            ],
        )
        f_one = job.input_files.get_files()[0]
        self.assertEqual(f_one.name, "SRR5963436_1.fastq.gz")
        self.assertEqual(f_one.path, "input")
        self.assertListEqual(job.input_files.get_files()[0].type_tags, ["fastq", "ena"])

    def test_add_sanitized_filenames(self):
        jsonstr = """{"id": "lTKTI4LU2A8u75Nx33UBc", "name": "Sample set created on 2020-07-02T09:28:57.197356", "owner": "3n0KJX6w5XBqIlbmgJeAKK", 
         "samples": [{"name": "I'm an ugly [#2] (L002_1) sample-NAME__r1", 
                      "files": [
                        {"R1": {"name": "I'm an ugly [#2] (L002_1) sample-NAME__r1_R1.fastq.gz", "tags": [], 
                                "location": "https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data2/nasty%20dir%20with%20%23%20...%20spaces%20!/I'm%20an%20ugly%20%5b%232%5d%20(L002_1)%20sample-NAME__r1_R1.fastq.gz"}, 
                         "R2": {"name": "I'm an ugly [#2] (L002_1) sample-NAME__r1_R2.fastq.gz", "tags": [], 
                                "location": "https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data2/nasty%20dir%20with%20%23%20...%20spaces%20!/I'm%20an%20ugly%20%5b%232%5d%20(L002_1)%20sample-NAME__r1_R2.fastq.gz"}
                        }
                      ]}
                    ]
        }
        """
        orig_params = json.loads(jsonstr)
        with_sane_names = add_sanitized_names_to_samplecart_json(orig_params)

        self.assertEqual(
            with_sane_names["samples"][0]["files"][0]["R1"]["sanitized_filename"],
            "Im_an_ugly_2_L002_1_sample-NAME__r1_R1.fastq.gz",
        )
        self.assertEqual(
            with_sane_names["samples"][0]["files"][0]["R2"]["sanitized_filename"],
            "Im_an_ugly_2_L002_1_sample-NAME__r1_R2.fastq.gz",
        )

        self.assertEqual(
            with_sane_names["samples"][0]["sanitized_name"],
            "Im_an_ugly_2_L002_1_sample-NAME__r1_",
        )

