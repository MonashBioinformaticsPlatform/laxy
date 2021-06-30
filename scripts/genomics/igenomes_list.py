#!/usr/bin/env python3
#
# Retrieves the file list from https://github.com/ewels/AWS-iGenomes and formats it as a
# Javascript object suitable for use  in the Laxy UI (eg PipelineParams.vue).

import requests
import json

manifest = requests.get(
    "https://raw.githubusercontent.com/ewels/AWS-iGenomes/master/ngi-igenomes_file_manifest.txt"
).text

ids = set()
for l in manifest.splitlines():
    if l.endswith("genome.fa") or l.endswith("genes.gtf"):
        s = l.split("/")
        if s[6]:
            genome_id = "/".join(s[4:7])
            ids.add(genome_id)

####

prev_species = ""
print("// for Javascript UI")
print("public available_genomes: Array<ReferenceGenome> = [")
for genome_id in sorted(list(ids)):
    species = genome_id.split("/")[0].replace("_", " ")

    if prev_species != species:
        print()
    prev_species = species

    nfcore_id = genome_id.split("/")[-1]
    record = {"id": genome_id, "organism": species, "nfcore_id": nfcore_id}
    print("  " + json.dumps(record) + ",")

print("];")

####

prev_species = ""
print("# For Python backend, validation")
print("REFERENCE_GENOME_MAPPINGS = {")
for genome_id in sorted(list(ids)):
    species = genome_id.split("/")[0].replace("_", " ")
    if prev_species != species:
        print()
    prev_species = species

    # genomes.append(record)
    print(f'    "{genome_id}": "{genome_id}",')

print("}")

####

genomes = []
for genome_id in sorted(list(ids)):
    species = genome_id.split("/")[0].replace("_", " ")
    record = {"id": genome_id, "organism": species}
    genomes.append(record)

# Raw JSON, may be served by the backend at some point instead of hard-coding
# print(json.dumps(genomes, indent=2))
