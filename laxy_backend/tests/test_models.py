# from __future__ import absolute_import
import unittest
import random
# from compare import expect, ensure, matcher
import json
import jwt

from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from django.contrib.auth.models import User

from rest_framework.test import APIClient

from ..models import Job, File, FileSet
from ..jwt_helpers import (get_jwt_user_header_dict,
                           make_jwt_header_dict,
                           create_jwt_user_token)
# from ..authorization import JWTAuthorizedClaimPermission


def _create_user_and_login(username='testuser',
                           password='testpass',
                           is_superuser=True):
    admin_user = User.objects.create_user(username, '', password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = Client()
    client.login(username=username, password=password)
    return (admin_user, client)


class FileModelTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user('adminuser', '', 'testpass')
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.user = User.objects.create_user('testuser', '', 'testpass')
        self.user.is_superuser = False
        self.user.save()

        self.file_sra_ftp = File(
            location="ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR950/SRR950078/"
                     "SRR950078_1.fastq.gz",
            owner_id=self.user.id)
        self.file_sra_ftp.save()

        self.file_ftp = File(
            location="ftp://ftp.monash.edu.au/pub/linux/debian/ls-lR.gz",
            owner_id=self.user.id)
        self.file_ftp.save()

        self.file_complex_http = File(
            location="https://example.com:8000/fastq/"
                     "sample1_R1.fastq.gz"
                     "#hashpart"
                     "?format=gz&shuffle=yes",
            owner_id=self.user.id)
        self.file_complex_http.save()

    def test_filename_guessing(self):
        self.assertEqual(self.file_sra_ftp.name, 'SRR950078_1.fastq.gz')
        self.assertEqual(self.file_ftp.name, 'ls-lR.gz')
        self.assertEqual(self.file_complex_http.name, "sample1_R1.fastq.gz")


class JobViewTest(TestCase):
    def setUp(self):
        admin_user, authenticated_client = _create_user_and_login()
        self.admin_user = admin_user
        self.admin_authenticated_client = authenticated_client

        self.job = Job(owner=admin_user,
                       params='{"bla":"foo"}',
                       )
        self.job.save()

        user, user_client = _create_user_and_login('user1', 'userpass1',
                                                   is_superuser=False)
        self.user = user
        self.user_client = user_client

        self.user_job = Job(owner=user,
                            params='{"bing":"bang"}',
                            )
        self.user_job.save()

    def tearDown(self):
        self.job.delete()
        self.admin_user.delete()

    def test_unauthenticated_access(self):
        client = APIClient()
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
        client = APIClient()
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

        client = APIClient()
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


    # @unittest.skip("JWT Authentication not working")
    def test_jwt_auth_access(self):
        jwt_header = get_jwt_user_header_dict('testuser')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=jwt_header['Authorization'])
        response = client.get(
            reverse('laxy_backend:job', args=[self.job.uuid()]), format='json')
        self.assertEqual(response.status_code, 200)

    def test_fileset(self):
        fs = FileSet(name='test-fileset-1', owner=self.user)
        file_a = File(owner=self.user,
                      name="file_a",
                      location="file:///tmp/file_a")
        file_b = File(owner=self.user,
                      name="file_b",
                      location="file:///tmp/file_b")
        file_a.save()
        file_b.save()
        id_list = sorted([file_a.id, file_b.id])

        fs.add(file_a)
        self.assertIn(file_a.id, fs.files)
        fs.add(file_b.id)
        self.assertListEqual(id_list, fs.files)
        fs.add([file_a.id, file_b])
        self.assertListEqual(id_list, fs.files)
        fs.add([file_a, file_a])
        self.assertListEqual(id_list, fs.files)

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
