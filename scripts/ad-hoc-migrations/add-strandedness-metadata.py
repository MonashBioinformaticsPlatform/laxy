# A very specific migration for older Jobs run with RNAsik 1.5.3, on Laxy
# pre ~Nov 2019.
# This script determines the 'strandedness' of a RNAsik 1.5.3 run based on the prescence
# of the relevant *Counts-withNames.txt file, and adds appropriate metdata to the Job.

# Run like:
# ./manage.py shell < add-strandedness-metadata.py
# __or__
# docker-compose -f docker-compose.yml \
#   exec django /bin/bash -c \
#   "/app/manage.py shell < /app/scripts/ad-hoc-migrations/add-strandedness-metadata.py"

from toolz.dicttoolz import merge
from laxy_backend.models import Job

jobs = Job.objects.filter(params__params__pipeline_version='1.5.3')

for j in jobs:
    for countfile in j.output_files.files.filter(type_tags__contains=['degust']):
        if '-withNames.txt' in countfile.name:
            predicted = countfile.name.split('-')[0]
            if not j.metadata:
                j.metadata = {}
            j.metadata['results'] = j.metadata.get('results', {})
            j.metadata['results'] = merge(j.metadata['results'], {'strandedness': {'predicted': predicted}})
            print(j.id, j.metadata['results'])
            j.save()
            break
