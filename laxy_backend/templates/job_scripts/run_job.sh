#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
# export DEBUG="${DEBUG:-yes}"
# export JOB_ID="${JOB_ID:-}"
# export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"
# export JOB_COMPLETE_AUTH_HEADER="${JOB_COMPLETE_AUTH_HEADER:-}"

export JOB_ID="{{ JOB_ID }}"
export JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
export JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"

mkdir -p input
mkdir -p output

####
#### Stage input data ###
####

if [ "${JOB_INPUT_STAGED}" == "no" ]; then

    PARALLEL_DOWNLOADS=4
    jq '.sample_set.samples[].files[][]' <pipeline_config.json | \
      sed s'/"//g' | \
      parallel --no-notice --line-buffer -j ${PARALLEL_DOWNLOADS} \
      wget --continue --trust-server-names --retry-connrefused --read-timeout=60 \
           --waitretry 60 --timeout=30 --tries 8 \
           --output-file output/download.log --directory-prefix input {}

fi

####
#### Import a Conda environment
####

# Conda activate misbehaves if nounset and errexit are set
# https://github.com/conda/conda/issues/3200
set +o nounset
# set +o errexit
# export PATH=$PATH:$(pwd)/../miniconda3/bin:$(pwd)/../miniconda3/envs/rnasik/bin
# source activate rnasik
source ../miniconda3/bin/activate ../miniconda3/envs/rnasik
set -o nounset
# set -o errexit

cd output

env >job_env.out

####
#### Job happens in here
####

IGENOMES_REFERENCE="Saccharomyces_cerevisiae/Ensembl/R64-1-1"
GENOME_FASTA="references/iGenomes/${IGENOMES_REFERENCE}/Sequence/WholeGenomeFasta/genome.fa"
GENOME_GTF="references/iGenomes/${IGENOMES_REFERENCE}/Annotation/Genes/genes.gtf"

# Don't exit on error, since we
set +o errexit
RNAsik -align star \
       -fastaRef ../../${GENOME_FASTA} \
       -fqDir ../input \
       -counts \
       -gtfFile ../../${GENOME_GTF} \
       -all \
       -paired \
       -extn ".fastq.gz" \
       -pairIds "_1,_2" \
       >>job.out 2>>job.err

# Capture the exit code of the important process, to be returned
# in the curl request below
EXIT_CODE=$?

####
#### Notify service we are done
####

# Authorization header is stored in a file so it doesn't
# leak in 'ps' etc.

# -H "Content-Type: application/json" \
# -H "${JOB_COMPLETE_AUTH_HEADER}" \

curl -X PATCH \
     -H @../.private_request_headers \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     -d '{"exit_code":'${EXIT_CODE}'}' \
     "${JOB_COMPLETE_CALLBACK_URL}"
