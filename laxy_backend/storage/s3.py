from django.conf import settings
from .. import tasks

def generate_s3_download_urls(self, job_id,
                              subpath='input/final',
                              expires_in=getattr(settings,
                                                 'PRESIGNED_S3_URL_TTL', None)):
    """
    For a completed job, generates a set of expiring pre-signed
    S3 download URLs, to be passed to a third party application
    that wants to download the job output.

    :param job_id: The Job UUID
    :type job_id: str
    :param subpath: The relative path inside the job (pseudo)directory
                    (eg under {bucket}/{job_id}/)
    :type subpath: str
    :param expires_in: Expiry time, in seconds from 'now'.
    :type expires_in: datetime.datetime
    :return:
    :rtype:
    """
    subpath = subpath.lstrip('/').rstrip('/')
    path = f'{job_id}/{subpath}/'
    args = (settings.S3_BUCKET,
            path,
            settings.PRESIGNED_S3_URL_TTL)
    # result = tasks.generate_s3_download_urls.apply_async(args=args))
    # Blocking call, since this usually seems fast enough that is doesn't
    # need to be queued
    result = tasks.generate_s3_download_urls.apply(args=args)
    return result.get()
