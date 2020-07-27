import os
import tempfile

from datetime import datetime

import unittest
from django.test import TestCase
from rest_framework.test import APIClient

from .. import util
from ..models import Job, File, FileSet, SampleCart, ComputeResource, EventLog
from django.contrib.auth import get_user_model

from ..util import laxy_sftp_url

User = get_user_model()

from ..tasks.job import (
    index_remote_files,
    _finalize_job_task_err_handler,
    set_job_status,
    file_should_be_deleted,
)

from ..tasks.file import (
    add_file_replica_records,
    remove_file_replica_records,
)


def _create_user_and_login(username="testuser", password="testpass", is_superuser=True):
    admin_user = User.objects.create_user(username, "", password)
    admin_user.is_superuser = is_superuser
    admin_user.save()

    client = APIClient(HTTP_CONTENT_TYPE="application/json")
    client.login(username=username, password=password)
    return (admin_user, client)


def get_tmp_dir():
    dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
    os.makedirs(dir, exist_ok=True)
    return dir


class TasksTest(TestCase):
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
            extra={"base_dir": get_tmp_dir()},
        )
        self.compute.save()

        self.job_one = Job(
            owner=self.user,
            status=Job.STATUS_RUNNING,
            remote_id="999",
            exit_code=None,
            params={},
            compute_resource=self.compute,
            completed_time=datetime.now(),
        )
        self.job_one.save()

        self.files = []
        self.file_bam = File(
            location="file:///tmp/laxyjobs/some_job_id/output/bigfile.bam",
            owner_id=self.user.id,
            metadata={"size": 1024 * 1024 * 1024},
        )
        self.file_bam.save()
        self.files.append(self.file_bam)

        self.file_bai = File(
            location="file:///tmp/laxyjobs/some_job_id/output/bigfile.bai",
            owner_id=self.user.id,
            type_tags=["bai"],
            metadata={"size": 1024},
        )
        self.file_bai.save()
        self.files.append(self.file_bai)

        self.file_html = File(
            location="file:///tmp/laxyjobs/some_job_id/output/report.html",
            owner_id=self.user.id,
            metadata={"size": 1024},
        )
        self.file_html.save()
        self.files.append(self.file_html)

        self.file_counts = File(
            location="file:///tmp/laxyjobs/some_job_id/output/counts.txt",
            owner_id=self.user.id,
            type_tags=["counts"],
            metadata={"size": 1024 * 1024 * 1024},
        )
        self.file_counts.save()

        self.file_always_delete_path = File(
            location="file:///tmp/laxyjobs/some_job_id/output/sikRun/refFiles/some_big_index",
            owner_id=self.user.id,
            metadata={"size": 1024},
        )
        self.file_always_delete_path.save()
        self.files.append(self.file_always_delete_path)

        self.file_must_keep_path = File(
            location="file:///tmp/laxyjobs/some_job_id/output/sikRun/multiqc_data/somedatafile",
            owner_id=self.user.id,
            metadata={"size": 1024 * 1024 * 1024},
        )
        self.file_must_keep_path.save()
        self.files.append(self.file_must_keep_path)

        self.file_big = File(
            location="file:///tmp/laxyjobs/some_job_id/output/just_big",
            owner_id=self.user.id,
            metadata={"size": 1024 * 1024 * 1024},
        )
        self.file_big.save()
        self.files.append(self.file_big)

        self.file_small = File(
            location="file:///tmp/laxyjobs/some_job_id/output/tiny_file",
            owner_id=self.user.id,
            metadata={"size": 1024},
        )
        self.file_small.save()
        self.files.append(self.file_small)

    def tearDown(self):
        self.compute.delete()
        self.job_one.delete()
        self.admin_user.delete()
        self.user.delete()

        for f in self.files:
            f.delete()

    def test_file_expiry_matching(self):
        self.assertTrue(file_should_be_deleted(self.file_bam))
        self.assertTrue(file_should_be_deleted(self.file_bai))
        self.assertTrue(file_should_be_deleted(self.file_big))
        self.assertTrue(file_should_be_deleted(self.file_always_delete_path))

        self.assertFalse(file_should_be_deleted(self.file_html))
        self.assertFalse(file_should_be_deleted(self.file_counts))
        self.assertFalse(file_should_be_deleted(self.file_small))
        self.assertFalse(file_should_be_deleted(self.file_must_keep_path))

    def test_set_job_status_task(self):
        task_data = dict(job_id=self.job_one.id, status=Job.STATUS_COMPLETE)
        result = set_job_status(task_data)
        self.assertEqual(task_data["status"], Job.STATUS_COMPLETE)

    # See: https://stackoverflow.com/q/46530784
    #      https://stackoverflow.com/q/42058295
    #      https://gist.github.com/Sovetnikov/a7ad982fc77e8dfbc528bfc20fcf3b1e
    @unittest.skip("Needs task_always_eager=True and a real celery worker")
    def test_finalize_job_task_err_handler(self):
        # queue this task for 3 seconds in the future
        index_task_result = index_remote_files.s(
            task_data=dict(job_id=self.job_one.id)
        ).apply_async(countdown=3)
        finalize_errorlog_count = EventLog.objects.filter(
            event="JOB_FINALIZE_ERROR"
        ).count()
        # then before it's actually complete, call the 'link_error' handler task with it's UUID
        _finalize_job_task_err_handler(index_task_result.id, job_id=self.job_one.id)
        # a JOB_FINALIZE_ERROR event should be generated
        self.assetEqual(
            finalize_errorlog_count + 1,
            EventLog.objects.filter(event="JOB_FINALIZE_ERROR").count(),
        )

    def test_add_remove_replica_records(self):
        orig_compute = ComputeResource(
            owner=self.user,
            host="127.0.0.1",
            disposable=False,
            status=ComputeResource.STATUS_ONLINE,
            name="default",
            extra={"base_dir": get_tmp_dir()},
        )
        orig_compute.save()

        archive_compute = ComputeResource(
            owner=self.user,
            host="localhost",
            disposable=False,
            status=ComputeResource.STATUS_ONLINE,
            name="archive",
            extra={"base_dir": get_tmp_dir()},
        )
        archive_compute.save()

        job = Job(
            owner=self.user,
            status=Job.STATUS_COMPLETE,
            remote_id="999",
            exit_code=0,
            params={},
            compute_resource=orig_compute,
            completed_time=datetime.now(),
        )
        job.save()

        in_file = File(
            name="pipeline_config.json", path="input/config", metadata={"size": 512}
        )
        in_file.location = laxy_sftp_url(job, in_file.full_path)
        out_file = File(
            name="alignment.bam",
            path="output/bams",
            metadata={"size": 1024 * 1024 * 1024},
        )
        out_file.location = laxy_sftp_url(job, out_file.full_path)

        job.input_files.add(in_file)
        job.output_files.add(out_file)

        files = job.get_files()

        # First establish that we have only a single default location.
        for f in files:
            self.assertEqual(f.locations.count(), 1)
            self.assertTrue(f.locations.first().default)
            self.assertTrue(f.location.startswith(f"laxy+sftp://{orig_compute.id}/"))

        add_file_replica_records(files, archive_compute, set_as_default=True)

        # After adding the replica location as the default, check that we have two locations.
        # The default location should be on archive_compute, non-default should be on orig_compute.
        for f in job.get_files():
            self.assertEqual(f.locations.count(), 2)
            self.assertTrue(f.location.startswith(f"laxy+sftp://{archive_compute.id}/"))
            self.assertTrue(
                f.locations.filter(default=False)
                .first()
                .url.startswith(f"laxy+sftp://{orig_compute.id}")
            )

        remove_file_replica_records(files, orig_compute)

        # After removing the original location, we should only have a single location
        # pointing to archive_compute
        for f in job.get_files():
            self.assertTrue(f.location.startswith(f"laxy+sftp://{archive_compute.id}"))
            self.assertEqual(f.locations.count(), 1)
