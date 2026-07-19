"""
View-level tests for the IGV session endpoint (job/<uuid>/igv-session.xml).

Files are file://-backed local temp files (no live SFTP host needed); we only
exercise URL/XML generation and auth, not byte streaming.
"""

import os
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from laxy_backend import util
from ..models import Job, File, FileSet, ComputeResource, AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


def _create_user_and_login(username, password, is_superuser=False):
    user = User.objects.create_user(username, "", password)
    user.is_superuser = is_superuser
    user.save()
    client = APIClient()
    client.login(username=username, password=password)
    return user, client


class IgvSessionViewTest(TestCase):
    def setUp(self):
        self.owner, self.owner_client = _create_user_and_login(
            "igvowner", "igvpass"
        )

        self.job_dir = os.path.join(tempfile.gettempdir(), util.generate_uuid())
        self.output_dir = os.path.join(self.job_dir, "output", "aln")
        os.makedirs(self.output_dir, exist_ok=True)

        self.bam = self._make_file("aln.bam", b"BAMDATA")
        self.bai = self._make_file("aln.bam.bai", b"IDX")

        self.compute = ComputeResource(
            host="localhost",
            status=ComputeResource.STATUS_ONLINE,
            owner=self.owner,
            disposable=False,
        )
        self.compute.save()

        input_files = FileSet()
        input_files.save()
        output_files = FileSet()
        output_files.add(self.bam)
        output_files.add(self.bai)
        output_files.save()

        self.job = Job(
            input_files=input_files,
            output_files=output_files,
            owner=self.owner,
            compute_resource=self.compute,
            params={"params": {"genome": "Homo_sapiens/Ensembl/GRCh38.release-109"}},
        )
        self.job.save()

    def _make_file(self, name, content):
        fpath = os.path.join(self.output_dir, name)
        with open(fpath, "wb") as fh:
            fh.write(content)
        f = File(
            location=f"file://{fpath}",
            name=name,
            path="output/aln",
            owner_id=self.owner.id,
        )
        f.save()
        return f

    def tearDown(self):
        self.job.delete()
        for f in (self.bam, self.bai):
            if f.pk is not None:
                f.delete()
        self.compute.delete()
        self.owner.delete()

    def _url(self):
        return reverse("laxy_backend:job_igv_session", args=[self.job.id])

    def test_owner_gets_session_xml_with_genome_and_indexed_bam(self):
        response = self.owner_client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertIn("igv-session.xml", response["Content-Disposition"])

        root = ET.fromstring(response.content)
        self.assertEqual(root.get("genome"), "hg38")
        resources = root.findall("./Resources/Resource")
        self.assertEqual(len(resources), 1)
        bam_res = resources[0]
        self.assertIn("job/", bam_res.get("path"))
        self.assertIn("output/aln/aln.bam", bam_res.get("path"))
        self.assertIn("output/aln/aln.bam.bai", bam_res.get("index"))
        # BAM + index both carry a token so IGV can fetch without a cookie.
        self.assertIn("access_token=", bam_res.get("path"))
        self.assertIn("access_token=", bam_res.get("index"))

    def test_owner_request_mints_a_reusable_job_token(self):
        self.assertEqual(AccessToken.objects.filter(object_id=self.job.id).count(), 0)
        response = self.owner_client.get(self._url())
        self.assertEqual(response.status_code, 200)
        # A single job token is created and embedded.
        tokens = AccessToken.objects.filter(object_id=self.job.id)
        self.assertEqual(tokens.count(), 1)

        # A second request reuses it rather than minting another.
        self.owner_client.get(self._url())
        self.assertEqual(
            AccessToken.objects.filter(object_id=self.job.id).count(), 1
        )

    def test_supplied_access_token_is_propagated_and_authorises(self):
        token = AccessToken.objects.create(object_id=self.job.id).token
        anon = APIClient()

        response = anon.get(f"{self._url()}?access_token={token}")

        self.assertEqual(response.status_code, 200)
        root = ET.fromstring(response.content)
        path = root.find("./Resources/Resource").get("path")
        self.assertIn(f"access_token={token}", path)

    def test_no_bam_files_returns_404(self):
        empty_out = FileSet()
        empty_out.save()
        empty_in = FileSet()
        empty_in.save()
        job = Job(
            input_files=empty_in,
            output_files=empty_out,
            owner=self.owner,
            compute_resource=self.compute,
            params={"params": {}},
        )
        job.save()
        try:
            url = reverse("laxy_backend:job_igv_session", args=[job.id])
            response = self.owner_client.get(url)
            self.assertEqual(response.status_code, 404)
        finally:
            job.delete()

    def test_unindexed_bam_has_no_index_attribute(self):
        self.bai.delete()
        response = self.owner_client.get(self._url())
        self.assertEqual(response.status_code, 200)
        resource = ET.fromstring(response.content).find("./Resources/Resource")
        self.assertIsNone(resource.get("index"))

    def test_unknown_genome_omits_genome_attribute(self):
        self.job.params = {"params": {"genome": "Vicugna_pacos/Ensembl/vicPac1"}}
        self.job.save()
        response = self.owner_client.get(self._url())
        root = ET.fromstring(response.content)
        self.assertIsNone(root.get("genome"))

    def test_non_owner_without_token_is_denied(self):
        _, other_client = _create_user_and_login("igvintruder", "nope")
        response = other_client.get(self._url())
        self.assertIn(response.status_code, (403, 404))

    def test_restrictive_accept_header_is_not_406(self):
        # IGV/htsjdk sends an Accept header that includes neither */* nor
        # application/json; content negotiation must not reject it with 406.
        response = self.owner_client.get(
            self._url(), HTTP_ACCEPT="application/octet-stream"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
