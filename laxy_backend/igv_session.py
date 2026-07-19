"""
Helpers for generating IGV desktop session XML that points at a Job's BAM
files (and their indices) via ranged Laxy file URLs.

IGV desktop opens a session URL directly (File > Open Session ...) and issues
HTTP Range requests against each BAM + index, which the file-serving endpoints
support (see `http_range.py`). The pieces here are deliberately pure/testable:
matching a BAM to its index sibling, mapping a Laxy reference-genome id to an
IGV-hosted genome id, and rendering the session XML.
"""

from typing import Iterable, List, Optional
from xml.etree import ElementTree as ET

# Recognisable assembly tokens (as they appear in Laxy iGenomes-style genome
# ids, eg "Homo_sapiens/Ensembl/GRCh38.release-109") mapped to the genome ids
# IGV hosts and can auto-download. Conservative on purpose: an unknown genome
# yields no `genome` attribute, so IGV keeps whatever reference is loaded and
# the user can pick one, rather than erroring on an id IGV doesn't recognise.
# Longer / more specific tokens first so they win over generic ones.
_IGV_GENOME_BY_TOKEN = (
    ("GRCh38", "hg38"),
    ("GRCh37", "hg19"),
    ("hg38", "hg38"),
    ("hg19", "hg19"),
    ("GRCm39", "mm39"),
    ("GRCm38", "mm10"),
    ("mm39", "mm39"),
    ("mm10", "mm10"),
    ("GRCz11", "danRer11"),
    ("GRCz10", "danRer10"),
    ("Rnor_6.0", "rn6"),
    ("WBcel235", "ce11"),
    ("BDGP6", "dm6"),
    ("dm6", "dm6"),
    ("R64", "sacCer3"),
    ("TAIR10", "tair10"),
)


def laxy_genome_to_igv_id(genome_id: Optional[str]) -> Optional[str]:
    """
    Map a Laxy reference-genome id to an IGV-hosted genome id, or None if the
    assembly isn't one we can confidently map (caller then omits `genome`).
    """
    if not genome_id:
        return None
    lowered = genome_id.lower()
    for token, igv_id in _IGV_GENOME_BY_TOKEN:
        if token.lower() in lowered:
            return igv_id
    return None


def _index_candidate_names(bam_name: str) -> List[str]:
    """
    Candidate index filenames for a BAM, in preference order. Covers both the
    samtools convention (`aln.bam` -> `aln.bam.bai`) and the Picard/legacy one
    (`aln.bam` -> `aln.bai`), plus CSI indices.
    """
    stem = bam_name[:-4] if bam_name.lower().endswith(".bam") else bam_name
    return [
        f"{bam_name}.bai",
        f"{stem}.bai",
        f"{bam_name}.csi",
        f"{stem}.csi",
    ]


def find_bam_index(bam_file, files: Iterable):
    """
    Return the index `File` that sits beside `bam_file` (same `path`), or None.

    `files` is any iterable of File-like objects exposing `.name`, `.path` and
    `.id` (typically the job's combined file queryset materialised to a list).
    """
    same_dir = {
        f.name: f
        for f in files
        if f.path == bam_file.path and f.id != bam_file.id
    }
    for candidate in _index_candidate_names(bam_file.name):
        if candidate in same_dir:
            return same_dir[candidate]
    return None


def build_session_xml(
    genome_id: Optional[str],
    resources: List[dict],
    locus: str = "All",
) -> str:
    """
    Render an IGV session XML string.

    `resources` is a list of dicts with keys `name`, `path` (the BAM URL) and
    optionally `index` (the index URL). Attribute values are XML-escaped by
    ElementTree, so URLs carrying `?access_token=...&...` are safe.
    """
    session = ET.Element("Session", {"version": "8", "locus": locus})
    if genome_id:
        session.set("genome", genome_id)

    resources_el = ET.SubElement(session, "Resources")
    for resource in resources:
        attrs = {"name": resource["name"], "path": resource["path"]}
        if resource.get("index"):
            attrs["index"] = resource["index"]
        ET.SubElement(resources_el, "Resource", attrs)

    ET.indent(session)
    return ET.tostring(session, encoding="unicode", xml_declaration=True)
