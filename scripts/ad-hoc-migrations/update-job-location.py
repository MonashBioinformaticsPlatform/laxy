from django.db import transaction
from laxy_backend.models import Job, ComputeResource


def update_job_location(job_id: str, compute_resource_id: str):
    """
    Updates the location of a job (ComputeResource and FileLocations for
    all input and output files).

    This task doesn't actually move any data - it's more intended for situations
    where data has been moved out-of-band (eg, rsynced manually, not via an
    internal Laxy task) but records in the database need to be updated.
    """

    new_compute = compute_resource_id
    job = Job.objects.get(id=job_id)
    old_compute = job.compute_resource.id
    old_prefix = f'laxy+sftp://{old_compute}/'
    new_prefix = f'laxy+sftp://{new_compute}/'

    with transaction.atomic():
        job.compute_resource = ComputeResource.objects.get(id=new_compute)
        job.save()

        for f in job.get_files():
            for loc in f.locations.filter(url__startswith=old_prefix):
                loc.url = loc.url.replace(old_prefix, new_prefix)
                loc.save()
