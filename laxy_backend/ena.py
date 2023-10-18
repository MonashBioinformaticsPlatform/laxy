from typing import List, Dict, Union
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse
import requests
from requests.exceptions import HTTPError
import csv
from lxml import etree
import xmltodict
import pandas
from django.db import transaction
from cache_memoize import cache_memoize
import enasearch

from .models import File, FileSet

# from .models import User
from django.contrib.auth import get_user_model

User = get_user_model()


# def parse_fastq_table_flatten(table: str, url_scheme='ftp') -> Dict[str, Dict]:
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
#         rec['fastq_ftp'] = f'{url_scheme}://{rec['fastq_ftp']}'
#         rec['read_count'] = int(rec['read_count'])
#         rec['fastq_bytes'] = int(rec['fastq_bytes'])
#
#         by_url[rec[key_by]] = rec
#
#     return by_url


def parse_fastq_table(
    table: str, key_by="run_accession", url_scheme="ftp"
) -> Dict[str, Dict]:
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

    :param table:
    :type table:
    :param key_by:
    :type key_by:
    :param url_scheme: The URL scheme ('ftp', 'http' or 'https') to use first fastq_ftp links
                       (ENA supports both ftp://, http:// and https:// for these URLs).
                       The default is ftp since the http(s) scheme for these ENA URLs seems 
                       slower / undocumented / unsupported / unreliable ?
    :type url_scheme: str
    :return:
    :rtype:
    """

    table = [row for row in csv.DictReader(table.splitlines(), delimiter="\t")]
    by_url = OrderedDict()
    semicol_fields = ["fastq_ftp", "fastq_md5", "fastq_bytes"]
    for rec in table:
        for f in semicol_fields:
            rec[f] = rec[f].split(";")
        rec["read_count"] = int(rec["read_count"])
        rec["fastq_ftp"] = [
            f"{url_scheme}://{host_path}" for host_path in rec["fastq_ftp"]
        ]
        rec["fastq_bytes"] = [int(s) for s in rec["fastq_bytes"]]

        # If there is only one item in the list, make it a value not a list.
        # for field in ['fastq_ftp', 'fastq_md5', 'fastq_bytes']:
        #     if len(rec[field]) == 1:
        #         rec[field] = rec[field].pop()

        key = rec[key_by]
        if isinstance(rec[key_by], list):
            key = rec[key_by][0]
        by_url[key] = rec

    return by_url


def flatten_fastq_table(table: str, delimiter="\t", inner_sep=";") -> str:
    """
    Take a TSV table where some fields are semi-colon;separated and create new
    rows with those fields split.

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

    out = "%s\n" % delimiter.join(rec.keys())
    for r in rows:
        row_values = OrderedDict(r).values()
        out += "%s\n" % delimiter.join(row_values)

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
def create_file_objects(urls: dict, owner: Union[str, int, User] = None) -> List[File]:
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
        owner = User.objects.filter(id=owner).first()

    file_objs = []
    for url, metadata in urls.items():
        name = Path(urlparse(url).path).name
        md5 = metadata["fastq_md5"]
        size = metadata["fastq_bytes"][0]
        f = File(
            location=url,
            name=name,
            checksum=f"md5:{md5}",
            owner=owner,
            metadata=metadata,
        )
        f.size = size
        file_objs.append(f)

    # we can't do a bulk operation when File.save() is overridden
    # File.objects.bulk_create(file_objs)
    with transaction.atomic():
        for fo in file_objs:
            fo.save()

    return file_objs


def retrieve_run_report(accession, fields="fastq_ftp,fastq_md5"):
    """
    Temporary replacement for enasearch.retrieve_run_report which broke due to
    an API change at ENA (waiting for this PR: https://github.com/bebatut/enasearch/pull/49)
    """
    base_url = "https://www.ebi.ac.uk/ena/portal/api"
    resp = requests.get(
        f"{base_url}/filereport?accession={accession}&result=read_run&fields={fields}&format=tsv"
    )
    return resp.text


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
        fields = [
            "run_accession",
            "experiment_accession",
            "study_accession",
            "sample_accession",
            "secondary_sample_accession",
            "instrument_platform",
            "library_strategy",
            "read_count",
            "fastq_ftp",
            "fastq_md5",
            "fastq_bytes",
        ]

    urls_dict = dict()
    # raises HTTPError on status_code 500 (eg ENA is temporarily down)
    for accession in accessions:
        # table = enasearch.retrieve_run_report(
        #     accession=accession, fields=",".join(fields)
        # )
        table = retrieve_run_report(accession=accession, fields=",".join(fields))
        table = flatten_fastq_table(table)
        urls = parse_fastq_table(table, key_by="fastq_ftp", url_scheme="ftp")
        urls_dict.update(urls)

    return urls_dict


def get_run_table(accessions: List[str], fields: List[str] = None) -> Dict[str, Dict]:
    """
    Given an ENA (or SRA) Run (SRR*), Experiment (SRX*), Project (PRJ*)
    (or Study?) accession, return a list of associated Sample-style records
    (including FASTQ download URLs) for each run suitable for use by the
    frontend.

    :param fields:
    :type fields:
    :param accessions:
    :type accessions:
    :return:
    :rtype:
    """

    if fields is None:
        fields = [
            "run_accession",
            "experiment_accession",
            "study_accession",
            "sample_accession",
            "secondary_sample_accession",
            "instrument_platform",
            "instrument_model",
            "library_strategy",
            "library_source",
            "library_layout",
            "library_selection",
            "library_name",
            "broker_name",
            "study_alias",
            "experiment_alias",
            "sample_alias",
            "run_alias",
            "read_count",
            "base_count",
            "fastq_ftp",
            "fastq_md5",
            "fastq_bytes",
            "center_name",
        ]

    runs_dict = dict()
    # raises HTTPError on status_code 500 (eg ENA is temporarily down)
    for accession in accessions:
        # table = enasearch.retrieve_run_report(
        #    accession=accession, fields=",".join(fields)
        # )
        table = retrieve_run_report(accession=accession, fields=",".join(fields))

        # table = flatten_fastq_table(table)
        runs = parse_fastq_table(table, key_by="run_accession", url_scheme="ftp")
        runs_dict.update(runs)

    # We turn the list of FTP urls into a list of dicts like
    # [{'R1': 'ftp://bla_1.fastq.gz'}, {'R2': 'ftp://bla_2.fastq.gz'}]
    for run, metadata in runs_dict.items():
        if metadata.get("fastq_ftp", False):
            metadata["fastq_ftp"] = [
                {"R%s" % str(n + 1): url} for n, url in enumerate(metadata["fastq_ftp"])
            ]
    return runs_dict


@cache_memoize(timeout=24 * 60 * 60, cache_alias="ena-lookups")
def get_organism_from_sample_accession(accession: str) -> Dict:
    """
    :param accession:
    :type accession:
    :return:
    :rtype:
    """
    url = f"https://www.ebi.ac.uk/ena/browser/api/xml/{accession}"
    resp = requests.get(url)
    resp.raise_for_status()
    xml = etree.fromstring(resp.content)
    # organism = xml.xpath("//SAMPLE_NAME/SCIENTIFIC_NAME/text()")[0]
    # taxon_id = xml.xpath("//SAMPLE_NAME/TAXON_ID/text()")[0]
    sample_name_el = xml.xpath("//SAMPLE_NAME")[0]
    raw_organism_info = dict(
        xmltodict.parse(etree.tostring(sample_name_el))["SAMPLE_NAME"]
    )
    # Make keys lowercase
    organism_info = {k.lower(): v for k, v in raw_organism_info.items()}
    return organism_info


def search_ena_accessions(accessions: List[str]):
    ids = ",".join(accessions)
    return enasearch.retrieve_data(ids=ids, display="xml")


@transaction.atomic
def create_fastq_fileset(
    accession: str, owner: Union[str, int, User] = None, save=True
) -> FileSet:
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
        owner = User.objects.filter(id=owner).first()

    # if owner is None:
    #     owner = User.objects.get(id=1)

    urls = get_fastq_urls([accession])
    files = create_file_objects(urls)
    fileset = FileSet(name=accession, owner=owner)
    fileset.add(files)
    if save:
        fileset.save()

    return fileset
