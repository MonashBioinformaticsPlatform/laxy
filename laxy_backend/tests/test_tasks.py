import os
import tempfile

from datetime import datetime

import unittest
from django.test import TestCase
from rest_framework.test import APIClient

from .. import util
from ..models import Job, File, FileSet, SampleSet, ComputeResource, EventLog
from django.contrib.auth import get_user_model

User = get_user_model()

from ..tasks.job import (index_remote_files,
                         _index_remote_files_task_err_handler,
                         set_job_status)


def _create_user_and_login(username='testuser',
                           password='testpass',
                           is_superuser=True):
    admin_user = User.objects.create_user(username, '', password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = APIClient(HTTP_CONTENT_TYPE='application/json')
    client.login(username=username, password=password)
    return (admin_user, client)


def get_tmp_dir():
    dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
    os.makedirs(dir, exist_ok=True)
    return dir


class TasksTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user('adminuser', '', 'testpass')
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.user = User.objects.create_user('testuser', '', 'testpass')
        self.user.is_superuser = False
        self.user.save()

        self.compute = ComputeResource(owner=self.user,
                                       host='127.0.0.1',
                                       disposable=False,
                                       status=ComputeResource.STATUS_ONLINE,
                                       name='default',
                                       extra={'base_dir': get_tmp_dir()})
        self.compute.save()

        self.job_one = Job(owner=self.user, status=Job.STATUS_RUNNING,
                           remote_id='999', exit_code=None, params={},
                           compute_resource=self.compute,
                           completed_time=datetime.now())
        self.job_one.save()

    def tearDown(self):
        self.compute.delete()
        self.job_one.delete()
        self.admin_user.delete()
        self.user.delete()

    def test_set_job_status_task(self):
        task_data = dict(job_id=self.job_one.id, status=Job.STATUS_COMPLETE)
        result = set_job_status(task_data)
        self.assertEqual(task_data['status'], Job.STATUS_COMPLETE)

    # See: https://stackoverflow.com/q/46530784
    #      https://stackoverflow.com/q/42058295
    #      https://gist.github.com/Sovetnikov/a7ad982fc77e8dfbc528bfc20fcf3b1e
    @unittest.skip("Needs task_always_eager=True and a real celery worker")
    def test_index_remote_files_task_err_handler(self):
        # queue this task for 3 seconds in the future
        index_task_result = index_remote_files.s(task_data=dict(job_id=self.job_one.id)).apply_async(countdown=3)
        finalize_errorlog_count = EventLog.objects.filter(event='JOB_FINALIZE_ERROR').count()
        # then before it's actually complete, call the 'link_error' handler task with it's UUID
        _index_remote_files_task_err_handler(index_task_result.id, job_id=self.job_one.id)
        # a JOB_FINALIZE_ERROR event should be generated
        self.assetEqual(finalize_errorlog_count + 1, EventLog.objects.filter(event='JOB_FINALIZE_ERROR').count())

