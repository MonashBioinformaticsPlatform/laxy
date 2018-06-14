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
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from ..util import ordereddicts_to_dicts
from ..util import reverse_querystring
from ..models import Job, File, FileSet, SampleSet, ComputeResource
from ..jwt_helpers import (get_jwt_user_header_dict,
                           make_jwt_header_dict,
                           create_jwt_user_token)


def _create_user_and_login(username='testuser',
                           password='testpass',
                           is_superuser=True):
    admin_user = User.objects.create_user(username, '', password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = APIClient(HTTP_CONTENT_TYPE='application/json')
    client.login(username=username, password=password)
    return (admin_user, client)


class FileViewTest(TestCase):
    def setUp(self):
        user, user_client = _create_user_and_login('user1', 'userpass1',
                                                   is_superuser=False)
        self.user = user
        self.user_client = user_client

        self.file_a = File(owner=self.user,
                           # no name to test File.name() property serialization
                           # name="file_a",
                           location="file:///tmp/file_a")
        self.file_b = File(owner=self.user,
                           name="file_b",
                           location="file:///tmp/file_b")
        self.file_a.save()
        self.file_b.save()

        self.file_on_disk_content = b'test data\nline 2\n'
        self.file_on_disk_b64md5 = 'nROVtwU1zae3eOK/dZyRZw=='
        fd, fpath = tempfile.mkstemp()
        os.write(fd, self.file_on_disk_content)
        os.close(fd)

        self.file_on_disk = File(
            location=f'file://{fpath}',
            name=Path(fpath).name,
            path=Path(fpath).parent,
            checksum='md5:9d1395b70535cda7b778e2bf759c9167',
            type_tags=['text', 'test'],
            owner_id=self.user.id)
        self.file_on_disk.save()

    def test_create_file(self):
        job_json = {
            'location': 'http://example.com/file_examp.txt',
            'checksum': 'xxh64:c70492d07ce72425',
            'metadata': {'tags': ['text', 'interesting']}
        }

        response = self.user_client.post(
            reverse('laxy_backend:create_file'),
            data=job_json,
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        file_id = response.data.get('id')
        new_file = File.objects.get(id=file_id)
        self.assertEqual(new_file.location, 'http://example.com/file_examp.txt')
        # Note how the name get's automatically assigned based on the URL
        # (if possible)
        self.assertEqual(new_file.name, 'file_examp.txt')
        self.assertEqual(new_file.checksum, 'xxh64:c70492d07ce72425')
        self.assertEqual(new_file.owner, self.user)
        self.assertDictEqual(new_file.metadata,
                             {'tags': ['text', 'interesting']})

    def test_create_file_with_scheme_file(self):
        job_json = {
            'location': 'file:///tmp/file_on_disk.txt',
        }

        response = self.user_client.post(
            reverse('laxy_backend:create_file'),
            data=json.dumps(job_json),
            content_type='application/json'
        )

        # TODO: for some reason file:// URLs are giving a validation error,
        #       returning 400
        import sys
        sys.stderr.write(json.dumps(response.data, indent=2))
        self.assertEqual(response.status_code, 200)

    def test_get_file_unauthenticated(self):
        client = APIClient()
        response = client.get(reverse('laxy_backend:file',
                                      args=[self.file_a.uuid()]),
                              content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_get_file(self):
        response = self.user_client.get(
            reverse('laxy_backend:file', args=[self.file_a.uuid()]),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        json_data = response.data
        self.assertEqual(json_data.get('id'), self.file_a.id)
        self.assertEqual(json_data.get('location'), 'file:///tmp/file_a')
        self.assertEqual(json_data.get('checksum'), None)
        self.assertEqual(json_data.get('metadata'), {})

    def test_update_file_checksum(self):
        new_checksum = 'md5:cbda22bcb41ab0151b438589aa4637e2'
        response = self.user_client.patch(
            reverse('laxy_backend:file', args=[self.file_a.uuid()]),
            data=json.dumps({'checksum': new_checksum}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 204)

        updated_file = File.objects.get(id=self.file_a.id)
        self.assertEqual(updated_file.checksum, new_checksum)

    def test_update_file_id_attempt(self):
        new_id = 'some_UUID_string'
        response = self.user_client.patch(
            reverse('laxy_backend:file', args=[self.file_a.uuid()]),
            data=json.dumps({'id': new_id}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    def test_create_patch_file_metadata_RFC7386(self):
        file_c = File(owner=self.user,
                      name="file_RFC7386",
                      path="tmp",
                      location="file:///tmp/file_RFC7386",
                      metadata={"tags": ["A", "B"],
                                "size": 3142})
        file_c.save()

        original_metdata = dict(file_c.metadata)
        patch = json.loads('{"size": null, "tags": ["D"]}')
        response = self.user_client.patch(
            reverse('laxy_backend:file', args=[file_c.id]),
            data=json.dumps({'metadata': patch}),
            content_type='application/merge-patch+json'
        )

        self.assertEqual(response.status_code, 204)

        obj = File.objects.get(name="file_RFC7386")
        self.assertDictEqual(obj.metadata, {"tags": ["D"]})

    def test_create_patch_file_metadata_RFC6902(self):
        file_c = File(owner=self.user,
                      name="file_RFC6902",
                      path="tmp",
                      location="file:///tmp/file_RFC6902",
                      metadata={"tags": ["A", "B"],
                                "size": 3142})
        file_c.save()

        patch = json.loads('[{ "op": "add", "path": "/tags/2", "value": "C" }]')
        response = self.user_client.patch(
            reverse('laxy_backend:file', args=[file_c.id]),
            data=json.dumps({'metadata': patch}),
            content_type='application/json-patch+json'
        )

        self.assertEqual(response.status_code, 204)

        obj = File.objects.get(name="file_RFC6902")
        self.assertDictEqual(obj.metadata, {"size": 3142, "tags": ["A", "B", "C"]})

    def test_file_view_octet_stream(self):
        response = self.user_client.get(
            reverse('laxy_backend:file', args=[self.file_on_disk.uuid()]),
            content_type='application/octet-stream')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-disposition'],
                         f'inline')
        self.assertEqual(response['digest'], f'MD5={self.file_on_disk_b64md5}')

        content = b''.join([chunk
                            for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_download_octet_stream(self):
        url = reverse('laxy_backend:file', args=[self.file_on_disk.uuid()])
        response = self.user_client.get(f'{url}?download',
                                        content_type='application/octet-stream')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-disposition'],
                         f'attachment; filename="{self.file_on_disk.name}"')
        self.assertEqual(response['digest'], f'MD5={self.file_on_disk_b64md5}')

        content = b''.join([chunk
                            for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_view_content(self):
        url = reverse('laxy_backend:file_download',
                      args=[self.file_on_disk.uuid(), self.file_on_disk.name])
        response = self.user_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-disposition'],
                         f'inline')
        self.assertEqual(response['digest'], f'MD5={self.file_on_disk_b64md5}')

        content = b''.join([chunk
                            for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_file_download_content(self):
        url = reverse('laxy_backend:file_download',
                      args=[self.file_on_disk.uuid(), self.file_on_disk.name])
        response = self.user_client.get(f'{url}?download')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-disposition'],
                         f'attachment; filename="{self.file_on_disk.name}"')
        self.assertEqual(response['digest'], f'MD5={self.file_on_disk_b64md5}')

        content = b''.join([chunk
                            for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_job_file_download_content(self):
        compute = ComputeResource(host='localhost',
                                  status='online',
                                  owner=self.user,
                                  disposable=False)
        compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.add(self.file_on_disk)
        output_files.save()

        job = Job(input_files=input_files,
                  output_files=output_files,
                  owner=self.user,
                  compute_resource=compute)
        job.save()

        url = reverse('laxy_backend:job_file',
                      args=[job.id, f'{self.file_on_disk.absolute_path}'])
        response = self.user_client.get(f'{url}?download')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-disposition'],
                         f'attachment; filename="{self.file_on_disk.name}"')
        self.assertEqual(response['digest'], f'MD5={self.file_on_disk_b64md5}')

        content = b''.join([chunk
                            for chunk in response.streaming_content])
        self.assertEqual(content, self.file_on_disk_content)

    def test_job_file_put(self):
        compute = ComputeResource(host='localhost',
                                  status='online',
                                  owner=self.user,
                                  disposable=False)
        compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.save()

        job = Job(input_files=input_files,
                  output_files=output_files,
                  owner=self.user,
                  compute_resource=compute)
        job.save()

        url = reverse('laxy_backend:job_file',
                      args=[job.id, f'output/{self.file_on_disk.absolute_path}'])
        response = self.user_client.put(
            url,
            data=json.dumps(
                {'location': self.file_on_disk.location,
                 'checksum': self.file_on_disk.checksum_hash,
                 'metadata': {}}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        f_obj = File.objects.get(id=response.data.get('id'))
        self.assertEqual(f_obj.location, self.file_on_disk.location)
        job = Job.objects.get(id=job.id)
        self.assertEqual(f_obj, job.output_files.get_files().first())


class JobViewTest(TestCase):
    def setUp(self):
        admin_user, authenticated_client = _create_user_and_login()
        self.admin_user = admin_user
        self.admin_authenticated_client = authenticated_client

        self.job = Job(owner=admin_user,
                       params='{"bla":"foo"}')
        self.job.save()

        user, user_client = _create_user_and_login('user1', 'userpass1',
                                                   is_superuser=False)
        self.user = user
        self.user_client = user_client

        self.user_job = Job(owner=user,
                            params='{"bing":"bang"}')
        self.user_job.save()

    def tearDown(self):
        self.job.delete()
        self.admin_user.delete()

    def test_unauthenticated_access(self):
        client = APIClient(HTTP_CONTENT_TYPE='application/json')
        response = client.get(reverse('laxy_backend:job',
                                      args=[self.job.uuid()]))
        self.assertEqual(response.status_code, 401)

        response = client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            data={'status': Job.STATUS_COMPLETE},
            format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.job.status, Job.STATUS_CREATED)

    def test_admin_authenticated_access(self):
        response = self.admin_authenticated_client.get(
            reverse('laxy_backend:job', args=[self.job.uuid()]))
        self.assertEqual(response.status_code, 200)

    def test_admin_authenticated_patch(self):
        response = self.admin_authenticated_client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            data=json.dumps({'status': Job.STATUS_COMPLETE}),
            content_type='application/json')

        # we need to re-get the job to see the changes made by the request
        j = Job.objects.get(id=self.job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_COMPLETE)

    def test_patch_exit_code(self):
        # set both status and exit_code
        response = self.admin_authenticated_client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            data=json.dumps({'status': Job.STATUS_CANCELLED,
                             'exit_code': 99}),
            content_type='application/json')

        # we need to re-get the job to see the changes made by the request
        j = Job.objects.get(id=self.job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_CANCELLED)
        self.assertEqual(j.exit_code, 99)

        # set only exit_code, status gets set automatically
        response = self.admin_authenticated_client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            data=json.dumps({'exit_code': 0}),
            content_type='application/json')

        j = Job.objects.get(id=self.job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_COMPLETE)
        self.assertEqual(j.exit_code, 0)

        # set only non-zero exit_code, status gets set to failed automatically
        response = self.admin_authenticated_client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            data=json.dumps({'exit_code': 1}),
            content_type='application/json')

        j = Job.objects.get(id=self.job.id)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(j.status, Job.STATUS_FAILED)
        self.assertEqual(j.exit_code, 1)

    def test_verify_jwt_token(self):
        token = create_jwt_user_token('testuser')[0]
        client = APIClient(HTTP_CONTENT_TYPE='application/json')
        response = client.post(
            reverse('jwt-verify-token'),
            data={'token': token},
            format='json')
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

        jwt_header = make_jwt_header_dict(
            create_object_access_jwt(self.user_job))
        # jwt_header = {'HTTP_AUTHORIZATION': jwt_header['Authorization']}
        # jwt_client = Client()

        client = APIClient(HTTP_CONTENT_TYPE='application/json')
        client.credentials(HTTP_AUTHORIZATION=jwt_header['Authorization'])

        response = client.get(
            reverse('laxy_backend:job', args=[self.user_job.uuid()]),
            format='json')
        self.assertEqual(response.status_code, 200)

        response = client.patch(
            reverse('laxy_backend:job', args=[self.user_job.uuid()]),
            {'status': Job.STATUS_COMPLETE}, format='json')
        self.assertEqual(response.status_code, 204)

        response = client.patch(
            reverse('laxy_backend:job', args=[self.job.uuid()]),
            {'status': Job.STATUS_COMPLETE}, format='json')
        self.assertEqual(response.status_code, 403)

        client.credentials(HTTP_AUTHORIZATION="Bearer __invalid_jwt__")
        with self.assertRaises(jwt.exceptions.DecodeError):
            response = client.patch(
                reverse('laxy_backend:job', args=[self.job.uuid()]),
                {'status': Job.STATUS_COMPLETE}, format='json')

    def test_jwt_auth_access(self):
        jwt_header = get_jwt_user_header_dict('testuser')
        client = APIClient(HTTP_CONTENT_TYPE='application/json')
        client.credentials(HTTP_AUTHORIZATION=jwt_header['Authorization'])
        url = reverse('laxy_backend:job', args=[self.job.uuid()])
        response = client.get(url, format='json')
        self.assertEqual(response.status_code, 200)

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
