from typing import List, Dict, Union
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse
import requests
import csv
from lxml import etree
from django.db import transaction
from django.contrib.auth.models import User

from .models import File, FileSet


def parse_fastq_table(table: str) -> Dict[str, Dict]:
    """
    Return a dictionary keyed by url, given the raw text with tab-delimited
    fields:

    run_accession	fastq_ftp	fastq_md5	fastq_bytes

    All fields other than run_accession may contain a semi-colon (;)
    delimited list. The scheme ftp:// is added to all fastq_ftp URLs.

    Returned dictionary is of the form:

    {'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR950/SRR950078/SRR950078_1.fastq.gz':
       {'accession': 'PRJNA214799',
        'md5': 'eee21620ca17744147ff66cdd2529066',
        'size': 8584375694}
    }

    eg, from:

    https://www.ebi.ac.uk/ena/data/warehouse/filereport?
    accession=PRJNA214799&
    result=read_run&
    fields=run_accession,fastq_ftp,fastq_md5,fastq_bytes

    :param table:
    :type table:
    :return:
    :rtype:
    """

    table = [row for row in csv.DictReader(table.splitlines(), delimiter='\t')]
    by_url = dict()
    for rec in table:
        accession = rec[list(rec.keys())[0]]
        links = rec['fastq_ftp'].split(';')
        checksums = rec['fastq_md5'].split(';')
        sizes = rec['fastq_bytes'].split(';')

        links = ['ftp://%s' % l for l in links]
        sizes = [int(s) for s in sizes]
        for url, md5, size in zip(links, checksums, sizes):
            by_url[url] = {'accession': accession,
                           'md5': md5,
                           'size': size}

    return by_url


@transaction.atomic
def create_file_objects(urls: dict,
                        owner: Union[str, int, User] = None) -> List[File]:
    """
    Create a set of corresponding file objects, given the raw text with
    tab-delimited fields:

    run_accession	fastq_ftp	fastq_md5	fastq_bytes

    All fields other than run_accession may contain a semi-colon (;)
    delimited list.

    eg, from:

    https://www.ebi.ac.uk/ena/data/warehouse/filereport?
    accession=PRJNA214799&
    result=read_run&
    fields=run_accession,fastq_ftp,fastq_md5,fastq_bytes

    :param urls:
    :type urls:
    :param owner:
    :type owner:
    :return:
    :rtype:
    """

    if isinstance(owner, int) or isinstance(owner, str):
        owner = User.objects.get(id=owner)

    if owner is None:
        owner = User.objects.get(id=1)

    file_objs = []
    for url, metadata in urls.items():
        name = Path(urlparse(url).path).name
        md5 = metadata['md5']
        size = metadata['size']
        f = File(location=url, name=name,
                 checksum=f'md5:{md5}', owner=owner)
        file_objs.append(f)

    File.objects.bulk_create(file_objs)

    return file_objs


def get_fastq_urls(accession: str) -> Dict[str, Dict]:
    """
    Given an ENA (or SRA) Run, Experiment, Project (or Study?) accession,
    return a list of associated FASTQ download URLs.

    :param accession:
    :type accession:
    :return:
    :rtype:
    """

    # An alternative here would be to use the enasearch library
    # import enasearch
    # record = enasearch.retrieve_data(ids=accession, display="xml")
    # record is a dictionary that is equivalent to the xml -
    # we'd need to extract the same fields, probably via a jq expression

    record_url = f'https://www.ebi.ac.uk/ena/data/view/{accession}&display=xml&download=xml'
    record = requests.get(record_url)
    xml = etree.fromstring(record.content)
    xref_db_links = xml.xpath(
        "//XREF_LINK/DB[text()='ENA-FASTQ-FILES']/following-sibling::ID/text()")
    urls = dict()
    for fastq_table_url in xref_db_links:
        table = requests.get(fastq_table_url)
        by_url = parse_fastq_table(table.text)
        urls.update(by_url)

    return urls


@transaction.atomic
def create_fastq_fileset(accession: str,
                         owner: Union[str, int, User] = None,
                         save=True) -> FileSet:

    if isinstance(owner, int) or isinstance(owner, str):
        owner = User.objects.get(id=owner)

    if owner is None:
        owner = User.objects.get(id=1)

    urls = get_fastq_urls(accession)
    files = create_file_objects(urls)
    fileset = FileSet(name=accession, owner=owner)
    fileset.add(files)
    if save:
        fileset.save()

    return fileset
