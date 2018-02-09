from typing import List, Dict, Union
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse
import requests
from requests.exceptions import HTTPError
import csv
from lxml import etree
import pandas
from django.db import transaction
from django.contrib.auth.models import User
import enasearch

from .models import File, FileSet


# def parse_fastq_table_flatten(table: str) -> Dict[str, Dict]:
#     """
#     Return a dictionary keyed by url, given the raw text with tab-delimited
#     fields:
#
#     run_accession	fastq_ftp	fastq_md5	fastq_bytes
#
#     All fields other than run_accession may contain a semi-colon (;)
#     delimited list. The scheme ftp:// is added to all fastq_ftp URLs.
#
#     Returned dictionary is of the form:
#
#     {'ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR950/SRR950078/SRR950078_1.fastq.gz':
#        {'accession': 'PRJNA214799',
#         'md5': 'eee21620ca17744147ff66cdd2529066',
#         'size': 8584375694}
#     }
#
#     eg, from:
#
#     https://www.ebi.ac.uk/ena/data/warehouse/filereport?
#     accession=PRJNA214799&
#     result=read_run&
#     fields=run_accession,fastq_ftp,fastq_md5,fastq_bytes
#
#     :param key_by:
#     :type key_by:
#     :param table:
#     :type table:
#     :return:
#     :rtype:
#     """
#
#     key_by = 'fastq_ftp'
#
#     table = flatten_fastq_table(table, delimiter='\t', inner_sep=';')
#
#     table = [row for row in csv.DictReader(table.splitlines(), delimiter='\t')]
#     by_url = OrderedDict()
#     for rec in table:
#         rec['fastq_ftp'] = 'ftp://%s' % rec['fastq_ftp']
#         rec['read_count'] = int(rec['read_count'])
#         rec['fastq_bytes'] = int(rec['fastq_bytes'])
#
#         by_url[rec[key_by]] = rec
#
#     return by_url


def parse_fastq_table(table: str, key_by='run_accession') -> Dict[str, Dict]:
    """
    Return a dictionary keyed by run_accession, given the raw text with tab-delimited
    fields:

    run_accession	read_count	fastq_ftp	fastq_md5	fastq_bytes

    Other fields may be present but are optional.

    All fields other than run_accession may contain a semi-colon (;)
    delimited list. The scheme ftp:// is added to all fastq_ftp URLs.

    Returned dictionary is of the form:
    {"SRR1819888": {"run_accession": "SRR1819888", "experiment_accession": "SRX891607",
                    "study_accession": "PRJNA276493", "sample_accession": "SAMN03375745",
                    "instrument_platform": "ILLUMINA", "library_strategy": "RNA-Seq", "read_count": 46731654,
                    "fastq_ftp": ["ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR181/008/SRR1819888/SRR1819888_1.fastq.gz",
                                  "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR181/008/SRR1819888/SRR1819888_2.fastq.gz"],
                    "fastq_md5": ["58a845ac61ae48efdb704bff2df2576f", "cfc8334c8892ebe8c02d4c192dd49740"],
                    "fastq_bytes": [3719354690, 3730960959]}
     }

    eg, from:

    https://www.ebi.ac.uk/ena/data/warehouse/filereport?
    accession=PRJNA276493&
    result=read_run&
    fields=run_accession,experiment_accession,study_accession,sample_accession,instrument_platform,library_strategy,
    read_count,fastq_ftp,fastq_md5,fastq_bytes

    :param key_by:
    :type key_by:
    :param table:
    :type table:
    :return:
    :rtype:
    """

    table = [row for row in csv.DictReader(table.splitlines(), delimiter='\t')]
    by_url = OrderedDict()
    semicol_fields = ['fastq_ftp', 'fastq_md5', 'fastq_bytes']
    for rec in table:
        for f in semicol_fields:
            rec[f] = rec[f].split(';')
        rec['read_count'] = int(rec['read_count'])

        rec['fastq_ftp'] = ['ftp://%s' % l for l in rec['fastq_ftp']]
        rec['fastq_bytes'] = [int(s) for s in rec['fastq_bytes']]
        key = rec[key_by]
        if isinstance(rec[key_by], list):
            key = rec[key_by].pop()
        by_url[key] = rec

    return by_url


def flatten_fastq_table(table: str, delimiter='\t', inner_sep=';') -> str:
    """
    Take a TSV table where some fields are semi-colon;separated and create new rows with
    those fields split.

    1   2   A;B   C;D

    becomes

    1   2   A   C
    1   2   B   D

    :param inner_sep:
    :type inner_sep:
    :param delimiter:
    :type delimiter:
    :param table:
    :type table:
    :return:
    :rtype:
    """
    table = [row for row in csv.DictReader(table.splitlines(), delimiter=delimiter)]
    rows = []

    for rec in table:
        n_subfields = max([len(v.split(inner_sep)) for v in rec.values()])
        row = [split_extend(v, inner_sep, n_subfields) for k, v in rec.items()]
        fanned_out_rows = list(zip(*row))
        for r in fanned_out_rows:
            rows.append(list(zip(list(rec.keys()), r)))

    out = '%s\n' % delimiter.join(rec.keys())
    for r in rows:
        row_values = OrderedDict(r).values()
        out += '%s\n' % delimiter.join(row_values)

    return out


def split_extend(seq, sep, length):
    """
    Splits on a character, but also output a list of defined length.
    Used the first field of the split result to pad out the requested length.

    eg

    >>> split_extend("A;B;C", ';', 3)
    ['A', 'B', 'C']

    >>> split_extend("A", ';', 3)
    ['A', 'A', 'A']

    >>> split_extend("A;B", ';', 4)
    ['A', 'B', 'A', 'A']

    :param seq:
    :type seq:
    :param sep:
    :type sep:
    :param length:
    :type length:
    :return:
    :rtype:
    """
    s = seq.split(sep)
    s.extend([s[0]] * (length - len(s)))
    return s


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
        md5 = metadata['fastq_md5']
        size = metadata['fastq_bytes']
        f = File(location=url, name=name,
                 checksum=f'md5:{md5}',
                 owner=owner,
                 metadata=metadata)
        file_objs.append(f)

    File.objects.bulk_create(file_objs)

    return file_objs


def get_fastq_urls(accessions: List[str], fields: List[str] = None) -> Dict[str, Dict]:
    """
    Given an ENA (or SRA) Run (SRR*), Experiment (SRX*), Project (PRJ*)
    (or Study?) accession, return a list of associated FASTQ download URLs.

    :param fields:
    :type fields:
    :param accessions:
    :type accessions:
    :return:
    :rtype:
    """

    if fields is None:
        fields = ['run_accession', 'experiment_accession', 'study_accession', 'sample_accession',
                  'instrument_platform', 'library_strategy', 'read_count',
                  'fastq_ftp', 'fastq_md5', 'fastq_bytes']

    urls_dict = dict()
    # raises HTTPError on status_code 500 (eg ENA is temporarily down)
    for accession in accessions:
        table = enasearch.retrieve_run_report(accession=accession, fields=','.join(fields))
        table = flatten_fastq_table(table)
        urls = parse_fastq_table(table, key_by='fastq_ftp')
        urls_dict.update(urls)

    return urls_dict


def search_ena_accessions(accessions: List[str]):
    ids = ','.join(accessions)
    return enasearch.retrieve_data(ids=ids, display="xml")


@transaction.atomic
def create_fastq_fileset(accession: str,
                         owner: Union[str, int, User] = None,
                         save=True) -> FileSet:
    """
    Given an ENA accession, create a set of Files and a FileSet with
    the locations (eg ftp:// URLs) for each associated FASTQ file.

    Return the FileSet.

    :param accession:
    :type accession:
    :param owner:
    :type owner:
    :param save:
    :type save:
    :return:
    :rtype:
    """
    if isinstance(owner, int) or isinstance(owner, str):
        owner = User.objects.get(id=owner)

    if owner is None:
        owner = User.objects.get(id=1)

    urls = get_fastq_urls([accession])
    files = create_file_objects(urls)
    fileset = FileSet(name=accession, owner=owner)
    fileset.add(files)
    if save:
        fileset.save()

    return fileset
