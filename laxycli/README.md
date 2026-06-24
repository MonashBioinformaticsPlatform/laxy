# laxycli

This is a experimental commandline client for submitting, downloading Laxy jobs etc.

You need to set the environment variable `LAXY_API_KEY` (or `LAXY_API_TOKEN`) with the JWT token provided on the user profile page in the web UI.

```bash
export LAXY_API_KEY=eySDfmklw3nfl3k4fknd.dlkfj3lfj34.drklgjlgejkl4
```

Examples:

Download the tarball for a completed job:

```bash
./laxycli.py job download 2MEHNLYB9CDQigSl4F7VQd
```

Start a job:

```bash
./laxycli.py job create --pipeline_name=nf-core-rnaseq \
                        --pipeline_version=3.10.1 \
                        --job_description="test job" \
                        --reference_genome_id="Homo_sapiens/Ensembl/GRCh38.release-109" \
                        --urls_file urls.txt
```

where `urls.txt` is a list of input file URL, one per line, like:
```
https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/SRR5963435_ss_1.fastq.gz
https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/SRR5963435_ss_2.fastq.gz
https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/SRR5963441_ss_1.fastq.gz
https://bioinformatics.erc.monash.edu/home/andrewperry/test/sample_data/SRR5963441_ss_2.fastq.gz
```

R1/R2 mates are paired automatically from the filenames (`_R1`/`_R2`,
`_ss_1`/`_ss_2`, or a trailing `_1`/`_2`); files with no pair token are
treated as single-end.

### Custom reference genome

Instead of a built-in (iGenomes) `--reference_genome_id`, you can run against a
custom reference by passing a FASTA + annotation URL. This sets `genome: null`
and `user_genome` in the pipeline params (equivalent to "Use a custom genome" in
the web UI):

```bash
./laxycli.py job create --pipeline_name=nf-core-rnaseq \
                        --pipeline_version=3.18.0 \
                        --job_description="custom genome job" \
                        --genome_fasta_url="https://example.org/genome.fa" \
                        --genome_annotation_url="https://example.org/genes.gtf" \
                        --urls_file urls.txt \
                        --no-wait
```

Useful extra options:

- `--pipeline_params_json` — extra pipeline params as a JSON object (or
  `@file.json`) merged into the pipelinerun params, e.g.
  `'{"nf-core-rnaseq": {"strandedness": "auto", "trimmer": "fastp"}}'`.
- `--no-wait` — submit and print the job id to stdout without polling.
- `job status <job_id> [--watch]` — print (or poll) a job's status.

Set the API base with `--api_base_url` or the `LAXY_API_URL` environment
variable (note the dev API listens on port `8001`, e.g.
`https://dev-api.laxy.io:8001/api/v1`).

The annotation corpus driver `tests/data/annotation_corpus/run_corpus_via_laxycli.py`
uses these features to submit the whole corpus as real jobs against a Laxy
server.