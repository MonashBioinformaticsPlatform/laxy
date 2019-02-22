from os import path
from io import StringIO
import base64
from urllib.parse import urlparse
from paramiko.rsakey import RSAKey
from storages.backends.sftpstorage import SFTPStorage
from ..models import ComputeResource


# TODO: This seems unused (probably replaced by models.File.file) - remove ?
def get_file(url):
    """
    sftp://Some_Compute_UUID/relative/path/from/base_path/file.fastq.gz

    :param url:
    :type url:
    :return:
    :rtype:
    """
    url = urlparse(url)
    scheme = url.scheme
    compute_id = url.host
    compute = ComputeResource.objects.get(id=compute_id)
    host = compute.hostname
    port = compute.port
    if port is None:
        port = 22
    private_key = compute.private_key
    username = compute.extra.get('username')
    base_dir = compute.extra.get('base_dir')
    params = dict(port=port,
                  username=username,
                  pkey=RSAKey.from_private_key(StringIO(private_key)))
    storage = SFTPStorage(host=host, params=params)

    return storage.open(path.join(base_dir, url.path))
