# laxycli

This is a experimental commandline client for submitting, downloading Laxy jobs etc.

You need to set the environment variable `LAXY_API_TOKEN` with the JWT token provided on the user profile page in the web UI.

```bash
export LAXY_API_TOKEN=eySDfmklw3nfl3k4fknd.dlkfj3lfj34.drklgjlgejkl4
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