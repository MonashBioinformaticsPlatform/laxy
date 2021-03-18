# seqkit stats Laxy pluggable pipeline 'app'

This app exists as an example of a 'pluggable' pipeline definition for Laxy.
In this case, it runs `seqkit stats` on all provided FASTQ/FASTA files.

A pluggable pipeline definition is a Django app that follows a few conventions.

Two variables `LAXY_JOB_TEMPLATES` and `LAXY_PIPELINE_NAME` must be defined
at the top level of the `apps.py` module.

The `LAXY_PIPELINE_NAME` should match a corresponding `Pipeline.pipeline_name` 
record in the database.

`LAXY_JOB_TEMPLATES` (usually `templates/`) is the path to 'skeleton' job template
files. These are processed via Jinja2 and copied to the compute host before starting a job.
Skeleton files for a specific version of the pipeline live in `templates/job_scripts/{pipeline_name}/{version}`,
where version may be `default`, or some other version identifier.
The only required file is `templates/job_scripts/{pipeline_name}/default/input/scripts/run_job.sh`.

## Frontend files

Each pipeline will generally require some customized web (Vue) frontend files.
Currently these exist in `laxy_frontend/src/components/pipelines/{pipeline_name}`,
however in a later release these will be moved to inside this Django app, or
to a corresponding `npm` package (WIP !).