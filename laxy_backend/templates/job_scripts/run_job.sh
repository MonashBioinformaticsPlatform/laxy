#!/usr/bin/env bash
set -o nounset
set -o pipefail
set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"
# export JOB_ID="${JOB_ID:-}"
# export JOB_COMPLETE_CALLBACK_URL="${JOB_COMPLETE_CALLBACK_URL:-}"

readonly TMP="${PWD}/../tmp"
readonly JOB_ID="{{ JOB_ID }}"
readonly JOB_COMPLETE_CALLBACK_URL="{{ JOB_COMPLETE_CALLBACK_URL }}"
readonly JOB_EVENT_URL="{{ JOB_EVENT_URL }}"
readonly JOB_FILE_REGISTRATION_URL="{{ JOB_FILE_REGISTRATION_URL }}"
readonly JOB_INPUT_STAGED="{{ JOB_INPUT_STAGED }}"
readonly REFERENCE_GENOME="{{ REFERENCE_GENOME }}"
readonly PIPELINE_VERSION="{{ PIPELINE_VERSION }}"
readonly JOB_PATH=${PWD}
readonly PIPELINE_CONFIG="${JOB_PATH}/input/pipeline_config.json"
readonly CONDA_BASE="${JOB_PATH}/../miniconda3"
readonly REFERENCE_BASE="${PWD}/../references/iGenomes"
readonly DOWNLOAD_CACHE_PATH="${PWD}/../cache"
readonly AUTH_HEADER_FILE="${JOB_PATH}/.private_request_headers"
readonly IGNORE_SELF_SIGNED_CERTIFICATE="{{ IGNORE_SELF_SIGNED_CERTIFICATE }}"

# These are applied via chmod to all files and directories in the run, upon completion
readonly JOB_FILE_PERMS='ug+rw-s'
readonly JOB_DIR_PERMS='ug+rwx-s'

readonly SCHEDULER="{{ SCHEDULER }}"
# readonly SCHEDULER="local"

readonly BDS_SINGLE_NODE="{{ BDS_SINGLE_NODE }}"

if [[ ${IGNORE_SELF_SIGNED_CERTIFICATE} == "yes" ]]; then
    readonly CURL_INSECURE="--insecure"
    readonly LAXYDL_INSECURE="--ignore-self-signed-ssl-certificate"
else
    readonly CURL_INSECURE=""
    readonly LAXYDL_INSECURE=""
fi

##
# These memory settings are important when running BigDataScript in single-node
# 'system=local' mode. When running in multi-node 'system=generic' (or 'system=slurm')
# the CPUS and MEM values should be small (eg 2 and 2000) since they reflect only the
# resources required to run the BDS workflow manager, not the tasks it launches (BDS
# will [hopefully!] ask for appropriate resources in the sbatch jobs it launches).

if [[ ${BDS_SINGLE_NODE} == "yes" ]]; then
    # system=local in bds.config - BDS will run each task as local process, not SLURM-aware

    # M3 (typically 24 core, ~256 Gb RAM nodes)
    MEM=64000  # defaults for Human, Mouse
    CPUS=12

    # laxy-compute-01 - 16 cores, 64 Gb RAM
    # MEM=40000  # defaults for Human, Mouse
    # CPUS=16

    if [[ "${REFERENCE_GENOME}" == *"Saccharomyces_cerevisiae"* ]]; then
        MEM=16000 # yeast (uses ~ 8Gb)
        CPUS=4
    fi
else
    # system=generic or system=slurm in bds.config - BDS will run sbatch tasks
    MEM=4000
    CPUS=2
fi

readonly SRUN_OPTIONS="--cpus-per-task=${CPUS} --mem=${MEM} -t 1-0:00 --ntasks-per-node=1 --ntasks=1 --job-name=laxy:${JOB_ID}"

PREFIX_JOB_CMD=""
if [[ "${SCHEDULER}" == "slurm" ]]; then
    PREFIX_JOB_CMD="srun ${SRUN_OPTIONS} "
fi

function add_sik_config() {
   send_event "JOB_INFO" "Configuring RNAsik (sik.config)."

   # Find that ComputeResource specific sik.config, and if there is none, use the default.
   # Always copy it to the job input directory so preserve it.
    local SIK_CONFIG

    SIK_CONFIG="${JOB_PATH}/../sik.config"
    if [[ ! -f "${SIK_CONFIG}" ]]; then
        SIK_CONFIG="$(dirname RNAsik)/../opt/rnasik-${PIPELINE_VERSION}/configs/sik.config"
    fi

    # special lower resource sik.config for yeast
    if [[ "${REFERENCE_GENOME}" == *"Saccharomyces_cerevisiae"* ]] && [[ -f "${JOB_PATH}/../sik.yeast.config" ]]; then
        echo "Using low resource yeast specific sik.config."
        SIK_CONFIG="${JOB_PATH}/../sik.yeast.config"
    fi

    cp -n "${SIK_CONFIG}" "${JOB_PATH}/input/sik.config" || true
}

function send_event() {
    local event=${1:-"HEARTBEAT"}
    local message=${2:-""}
    local extra=${3:-"{}"}
    # escape double quotes since this is JSON nested inside JSON ?
    # extra=$(sed 's/"/\\"/g' <<< "${extra}")

    # || true so we don't stop on errors irrespective of set -o errexit state,
    # so if a curl call fails we don't bring down the whole script
    # NOTE: curl v7.55+ is required to use -H @filename

    VERBOSITY="--silent"
    if [[ "${DEBUG}" == "yes" ]]; then
        # NOTE: verbose mode should NOT be used in production since it prints
        # full headers to stdout/stderr, including Authorization tokens.
        VERBOSITY="-vvv"
    fi

    curl -X POST \
         ${CURL_INSECURE} \
         -H "Content-Type: application/json" \
         -H @"${AUTH_HEADER_FILE}" \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"event":"'"${event}"'","message":"'"${message}"'","extra":'"${extra}"'}' \
         ${VERBOSITY} \
         "${JOB_EVENT_URL}" || true
}

function send_job_finished() {
    local exit_code=$1
    curl -X PATCH \
         ${CURL_INSECURE} \
         -H "Content-Type: application/json" \
         -H @"${AUTH_HEADER_FILE}" \
         --silent \
         -o /dev/null \
         -w "%{http_code}" \
         --connect-timeout 10 \
         --max-time 10 \
         --retry 8 \
         --retry-max-time 600 \
         -d '{"exit_code":'${exit_code}'}' \
         "${JOB_COMPLETE_CALLBACK_URL}"
}

function install_miniconda() {
    send_event "JOB_INFO" "Installing dependencies (conda env)."

    if [[ ! -d "${CONDA_BASE}" ]]; then
         wget --directory-prefix "${TMP}" -c "https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh"
         chmod +x "${TMP}"/Miniconda3-latest-Linux-x86_64.sh
         "${TMP}"/Miniconda3-latest-Linux-x86_64.sh -b -p "${CONDA_BASE}"
    fi
}

function init_conda_env() {
    # By convention, we name our Conda environments after {pipeline}-{version}
    # Each new pipeline version has it's own Conda env
    local env_name="${1}-${2}"
    local conda="${CONDA_BASE}/bin/conda"
    local pip="${CONDA_BASE}/bin/pip"

    send_event "JOB_INFO" "Activating conda environment (${env_name})."

    if [[ ! -d "${CONDA_BASE}/envs/${env_name}" ]]; then

        # Conda activate misbehaves if nounset and errexit are set
        # https://github.com/conda/conda/issues/3200
        set +o nounset
        # First we update conda itself
        "${conda}" update --yes -n base conda

        # Add required channels
        "${conda}" config --add channels serine/label/dev \
                                       --add channels serine \
                                       --add channels bioconda \
                                       --add channels conda-forge

        # Create a base environment
        "${conda}" create --yes -m -n "${env_name}"

        # Install an up-to-date curl and GNU parallel
        "${conda}" install --yes -n "${env_name}" curl aria2 parallel jq awscli
        "${pip}" install oneliner

        # Then install rnasik
        "${conda}" install --yes -n "${env_name}" rnasik=${2}

        # Environment takes a very long time to solve if qualimap is included initially
        "${conda}" install --yes -n "${env_name}" qualimap

        # Add mash for contamination screening
        "${conda}" install --yes -n "${env_name}" mash
    fi

    # We shouldn't need to do this .. but it seems required for _some_ environments (ie M3)
    export JAVA_HOME="${CONDA_BASE}/envs/${env_name}/jre"

    # shellcheck disable=SC1090
    source "${CONDA_BASE}/bin/activate" "${CONDA_BASE}/envs/${env_name}"

    "${conda}" env export >"${JOB_PATH}/input/conda_environment.yml"

    set -o nounset
}

function update_laxydl() {
     # Requires conda environment to be activated first
     local pip="${CONDA_BASE}/bin/pip"
    "${pip}" install -U --process-dependency-links "git+https://github.com/MonashBioinformaticsPlatform/laxy#egg=laxy_downloader&subdirectory=laxy_downloader"
}

function get_reference_data_aws() {
    # TODO: Be smarter about what we pull in - eg only the reference required,
    #       not the whole lot. Assume reference is present if appropriate
    #       directory is there
    if [[ ! -d "${REFERENCE_BASE}" ]]; then
        prev="${PWD}"
        mkdir -p "${REFERENCE_BASE}"
        cd "${REFERENCE_BASE}"
        aws s3 sync s3://bioinformatics-au/iGenomes .
        cd "${prev}"
    fi
}

function get_ensembl_grch38() {
     local fasta="${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/genome.fa"
     local gtf="${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/genes.gtf"
     local fasta_checksum="6ee1ec578b2b6495eb7da26885d0a496"
     local gtf_checksum="cfe6daf315889981b6c22789127232ef"

     mkdir -p "${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta"
     mkdir -p "${REFERENCE_BASE}/${REF_ID}/Annotation/Genes"

     if [[ ! -f "${fasta}" ]]; then
         curl ftp://ftp.ensembl.org/pub/release-95/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna_sm.primary_assembly.fa.gz \
              --silent --retry 10 | gunzip -c > "${fasta}"
         checksum=$(md5sum "${fasta}" | cut -f 1 -d ' ')
         if [[ "${checksum}" != "${fasta_checksum}" ]]; then
             exit -1
         fi
     fi
     if [[ ! -f "${gtf}" ]]; then
         curl ftp://ftp.ensembl.org/pub/release-95/gtf/homo_sapiens/Homo_sapiens.GRCh38.95.gtf.gz \
              --silent --retry 10 | gunzip -c > "${gtf}"
         checksum=$(md5sum "${gtf}" | cut -f 1 -d ' ')
         if [[ "${checksum}" != "${gtf_checksum}" ]]; then
             exit -1
         fi
     fi
}

function get_igenome_aws() {
     local REF_ID=$1

     send_event "JOB_INFO" "Getting reference genome (${REF_ID})."

     if [[ "${REF_ID}" == "Homo_sapiens/Ensembl/GRCh38" ]]; then
         get_ensembl_grch38
         return 0
     fi

     aws s3 --no-sign-request --region eu-west-1 sync \
         s3://ngi-igenomes/igenomes/${REF_ID}/Annotation/Genes/ ${REFERENCE_BASE}/${REF_ID}/Annotation/Genes/ --exclude "*" --include "genes.gtf"
     aws s3 --no-sign-request --region eu-west-1 sync \
        s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/WholeGenomeFasta/ ${REFERENCE_BASE}/${REF_ID}/Sequence/WholeGenomeFasta/
     aws s3 --no-sign-request --region eu-west-1 sync \
        s3://ngi-igenomes/igenomes/${REF_ID}/Sequence/STARIndex/ ${REFERENCE_BASE}/${REF_ID}/Sequence/STARIndex/
}

function add_to_manifest() {
    # Call like:
    # add_to_manifest "." "*.bam" "bam,alignment" '{"some":"extradata"}'

    # Writes manifest.csv with lines like:
    # checksum,filepath,type_tags,metadata
    # "md5:c0a248f159f700a340361e07421e3e62","output/sikRun/bamFiles/SRR5963435_ss_sorted_mdups.bam","bam,alignment",{"metadata":"datadata"}
    #" md5:eb8c7a1382f1ef0cf984749a42e136bc","output/sikRun/bamFiles/SRR5963441_ss_sorted_mdups.bam","bam,alignment",{"metadata":"datadata"}

    python3 -c '#
import os, sys, stat
from fnmatch import fnmatch
import hashlib
import re
import json

job_path = os.environ.get("JOB_PATH", ".")
manifest_file = os.path.join(job_path, "manifest.csv")

# exclude_files = [".private_request_headers", "manifest.csv", "job.pid"]

base_path = "."
glob_pattern = sys.argv[1]  # "*.bam"
tags = sys.argv[2]          # "html,report,multiqc"
if len(sys.argv) >= 4 and sys.argv[3]:
    metadata = sys.argv[3]      # {"some_file": "extra_data"}
else:
    metadata = "{}"

metadata = json.dumps(json.loads(metadata))

def lstrip_dotslash(path):
  return re.sub("^%s" % "./", "", path)

existing_paths = []
if os.path.exists(manifest_file):
  with open(manifest_file, "r") as fh:
    for l in fh:
      s = l.split(",")
      existing_paths.append(s[1].strip("\""))

def find(base_path, f):
  for path in base_path:
    for root, dirs, files in os.walk(path):
      for fi in files:
        if f(os.path.join(root, fi)):
          yield os.path.join(root, fi)
      for di in dirs:
        if f(os.path.join(root, di)):
          yield os.path.join(root, fi)

def get_md5(file_path, blocksize=512):
  md5 = hashlib.md5()
  with open(file_path, "rb") as f:
    while True:
      chunk = f.read(blocksize)
      if not chunk:
        break
      md5.update(chunk)
  return md5.hexdigest()

def md5sum(file_path, md5sum_executable="/usr/bin/md5sum"):
  out = subprocess.check_output([md5sum_executable, file_path])
  checksum = out.split()[0]
  if len(checksum) == 32:
    return checksum
  else:
    raise ValueError("md5sum failed: %s", out)

write_header = not os.path.exists(manifest_file)

with open(manifest_file, "a") as fh:
  if write_header:
    fh.write("checksum,filepath,type_tags,metadata\n")

  for hit in find([base_path], lambda fn: fnmatch(fn, glob_pattern)):
    abspath = lstrip_dotslash(hit)
    # if abspath in exclude_files:
    #   continue
    # if not (abspath.startswith("output") or abspath.startswith("input")):
    #   continue
    if abspath in existing_paths:
      continue
    if not os.path.exists(abspath):
      continue
    checksum = f"md5:{get_md5(abspath)}"
    fh.write(f"\"{checksum}\",\"{abspath}\",\"{tags}\",{metadata}\n")
    existing_paths.append(abspath)

' "$1" "$2" "${3:-}"
}

# TODO: This has become complex enough that it probably should be a Python script for file registration,
#  (pulled into the Conda environment, just like laxydl)
function register_files() {
    send_event "JOB_INFO" "Registering interesting output files."

    # Not find and tag specific files/filetypes
    add_to_manifest "*.bam" "bam,alignment"
    add_to_manifest "*.bai" "bai"
    add_to_manifest "*.fastq.gz" "fastq"
    add_to_manifest "**/multiqc_report.html" "multiqc,html,report"
    add_to_manifest "**/RNAsik.bds.*.html" "bds,logs,html,report"
    add_to_manifest "**/*_fastqc.html" "fastqc,html,report"
    add_to_manifest "**/*StrandedCounts-withNames-proteinCoding.txt" "counts,degust"
    add_to_manifest "**/*StrandedCounts.txt" "counts"
    add_to_manifest "**/*StrandedCounts-withNames.txt" "counts"
    add_to_manifest "input/**" ""
    add_to_manifest "output/**" ""

    curl -X POST \
      ${CURL_INSECURE} \
     -H "Content-Type: text/csv" \
     -H @"${AUTH_HEADER_FILE}" \
     --silent \
     -o /dev/null \
     -w "%{http_code}" \
     --connect-timeout 10 \
     --max-time 10 \
     --retry 8 \
     --retry-max-time 600 \
     --data-binary @manifest.csv \
     "${JOB_FILE_REGISTRATION_URL}"
}

function setup_bds_config() {
    send_event "JOB_INFO" "Configuring BigDataScript (bds.config)."

    local default_bds_config
    local job_bds_config

    default_bds_config="$(which bds).config"
    job_bds_config="${JOB_PATH}/input/bds.config"

    # Check for custom bds.config
    if [[ -f "${JOB_PATH}/../bds.config" ]]; then
        default_bds_config="${JOB_PATH}/../bds.config"
    fi

    # TODO: This won't work yet since the default bds.config contains
    # ~/.bds/clusterGeneric/* paths to the SLURM wrapper scripts.
    # The SLURM wrappers don't appear to come with the bds conda package (yet)
    # if [ "${SCHEDULER}" == "slurm" ]; then
    #     sed -i 's/#system = "local"/system = "generic"/' ${job_bds_config}
    # fi

    # special lower resource bds.config for yeast
    if [[ "${REFERENCE_GENOME}" == *"Saccharomyces_cerevisiae"* ]] && [[ -f "${JOB_PATH}/../bds.yeast.config" ]]; then
        echo "Using low resource yeast specific bds.config."
        default_bds_config="${JOB_PATH}/../bds.yeast.config"
    fi

    cp -n "${default_bds_config}" "${job_bds_config}" || true

    if [[ -f "${job_bds_config}" ]]; then
        export RNASIK_BDS_CONFIG="${job_bds_config}"
    fi
}

function get_input_data_urls() {
    # Output is one URL one per line
    local urls
    urls=$(jq '.sample_set.samples[].files[][]' <${PIPELINE_CONFIG} | sed s'/"//g')
    echo "${urls}"
}

function detect_pairs() {
    PAIRIDS=""
    EXTN=".fastq.gz"
    if stat -t "${JOB_PATH}"/input/*_R2_001.fastq.gz >/dev/null 2>&1; then
      EXTN=".fastq.gz"
      PAIRIDS="_R1_001,_R2_001"
    elif stat -t "${JOB_PATH}"/input/*_R2.fastq.gz >/dev/null 2>&1; then
      EXTN=".fastq.gz"
      PAIRIDS="_R1,_R2"
    elif stat -t "${JOB_PATH}"/input/*_2.fastq.gz >/dev/null 2>&1; then
      EXTN=".fastq.gz"
      PAIRIDS="_1,_2"
    # Very occasionally, we get FASTA format reads
    elif stat -t "${JOB_PATH}"/input/*_R2.fasta.gz >/dev/null 2>&1; then
      EXTN=".fasta.gz"
      PAIRIDS="_R1,_R2"
    elif stat -t "${JOB_PATH}"/input/*_2.fasta.gz >/dev/null 2>&1; then
      EXTN=".fasta.gz"
      PAIRIDS="_1,_2"
    fi

    if [[ -z "${PAIRIDS}" ]]; then
        send_event "JOB_INFO" "(Looks like unpaired reads)"
    else
        send_event "JOB_INFO" "(Looks like paired end data [${PAIRIDS}]) 👍"
    fi
}

function set_genome_index_arg() {
    GENOME_INDEX_ARG=""
    if [[ -d "${REFERENCE_BASE}/${REFERENCE_GENOME}/Sequence/STARIndex" ]]; then
        GENOME_INDEX_ARG="-genomeIdx ${REFERENCE_BASE}/${REFERENCE_GENOME}/Sequence/STARIndex"
    fi
}

function update_permissions() {
    send_event "JOB_INFO" "Updating Unix file permissions for job outputs on compute node."

    # This can be used to update the permission on files after job completion
    # (eg if you want to automatically share files locally with a group of users on a compute resource).
    chmod "${JOB_DIR_PERMS}" "${JOB_PATH}"
    find "${JOB_PATH}" -type d -exec chmod "${JOB_DIR_PERMS}" {} \;
    find "${JOB_PATH}" -type f -exec chmod "${JOB_FILE_PERMS}" {} \;
}

function run_mash_screen() {
    # This is additional 'pre-pipeline' step - might make sense integrating it as an option to RNAsik
    # in the future.

    #local _globstat_state=$(shopt -p globstar)
    #shopt -s globstar

    send_event "JOB_INFO" "Starting Mash screen (detects organism/contamination)."

    local -r mash_db_base="${REFERENCE_BASE}/../mash"
    local -r mash_reference_sketches="${mash_db_base}/refseq.genomes.k21s1000.msh"

    mkdir -p "${mash_db_base}"
    if [[ ! -f "${mash_reference_sketches}/refseq.genomes.k21s1000.msh" ]]; then
        curl -L -o "${mash_reference_sketches}" -C - "https://gembox.cbcb.umd.edu/mash/refseq.genomes.k21s1000.msh" || true
    fi

    local mash_reads=$(find "${JOB_PATH}/input" -name "*.fast[q,a].gz" | xargs)
    local cmd="mash screen -w -p 8 ${mash_reference_sketches} ${mash_reads}"
    local mash_outfile="${JOB_PATH}/output/mash_screen.tab"

    if [[ "${SCHEDULER}" == "slurm" ]]; then
        cat >"${JOB_PATH}/input/run_mash.sh" <<EOM
#!/bin/bash
#SBATCH --mem 16G
#SBATCH --cpus-per-task=8
#SBATCH --time=30
#SBATCH --qos=shortq
#SBATCH --ntasks-per-node=1
#SBATCH --ntasks=1
#SBATCH --job-name="laxy:mash_${JOB_ID}"
#SBATCH --error="${JOB_PATH}/output/mash_screen.err"

${cmd} | sort -gr >${mash_outfile} && \
grep _ViralProj ${mash_outfile} >${JOB_PATH}/output/mash_screen_virus.tab && \
grep -v _ViralProj ${mash_outfile} >${JOB_PATH}/output/mash_screen_nonvirus.tab
EOM
        sbatch "${JOB_PATH}/input/run_mash.sh"
    else
        eval ${cmd} | sort -gr >"${mash_outfile}" && \
        grep _ViralProj "${mash_outfile}" >"${JOB_PATH}/output/mash_screen_virus.tab" && \
        grep -v _ViralProj "${mash_outfile}" >"${JOB_PATH}/output/mash_screen_nonvirus.tab"
    fi
}

#function filter_ena_urls() {
#    local urls
#    urls=$(get_input_data_urls)
#    local ena_urls
#    for u in ${urls}; do
#        if [[ $u = *"ebi.ac.uk"* ]]; then
#            ena_urls="${ena_urls}"'\n'"${u}"
#        fi
#    done
#    echo "${ena_urls}"
#}


####
#### Pull in reference data from S3
####

mkdir -p "${TMP}"
mkdir -p input
mkdir -p output

####
#### Setup and import a Conda environment
####

install_miniconda

# We import the environment early to ensure we have a recent version of curl (>=7.55)
init_conda_env "rnasik" "${PIPELINE_VERSION}"

update_laxydl

# get_reference_data_aws
get_igenome_aws "${REFERENCE_GENOME}"

# Make a copy of the bds.config in the $JOB_PATH, possibly modified for SLURM
setup_bds_config

# Make a copy of the sik.config into $JOB_PATH/input/sik.config
add_sik_config

####
#### Stage input data ###
####

if [[ "${JOB_INPUT_STAGED}" == "no" ]]; then

    # send_event "INPUT_DATA_DOWNLOAD_STARTED" "Input data download started."

    readonly PARALLEL_DOWNLOADS=8
    # one URL per line
    readonly urls=$(get_input_data_urls)

    mkdir -p "${JOB_PATH}/../cache"
    laxydl download \
           ${LAXYDL_INSECURE} \
           -vvv \
           --cache-path "${DOWNLOAD_CACHE_PATH}" \
           --no-progress \
           --untar \
           --parallel-downloads "${PARALLEL_DOWNLOADS}" \
           --event-notification-url "${JOB_EVENT_URL}" \
           --event-notification-auth-file "${AUTH_HEADER_FILE}" \
           --pipeline-config "${JOB_PATH}/input/pipeline_config.json" \
           --destination-path "${JOB_PATH}/input" || send_job_finished $?

    # send_event "INPUT_DATA_DOWNLOAD_FINISHED" "Input data download completed."

fi

cd output

env >job_env.out

####
#### Job happens in here
####

GENOME_FASTA="${REFERENCE_BASE}/${REFERENCE_GENOME}/Sequence/WholeGenomeFasta/genome.fa"
GENOME_GTF="${REFERENCE_BASE}/${REFERENCE_GENOME}/Annotation/Genes/genes.gtf"

send_event "JOB_PIPELINE_STARTING" "Pipeline starting."

run_mash_screen

# Don't exit on error, since we want to capture exit code and do an HTTP
# request with curl upon failure
set +o errexit

# quick and dirty detection of paired-end or not
PAIRIDS=""
EXTN=".fastq.gz"
detect_pairs

set_genome_index_arg

send_event "JOB_INFO" "Starting RNAsik."

EXIT_CODE=99
RETRY_COUNT=0
MAX_RETRIES=3
RETRY_DELAY=10
# Since BDS pipelines (in theory) can be just restarted and continue after a failure,
# this while loop might make things more robust in the face of temporary failures
# (eg transient SLURM queue submission errors)
while [[ "${EXIT_CODE}" -ne 0 ]] && [[ ${RETRY_COUNT} -le ${MAX_RETRIES} ]]; do

    if [[ ${RETRY_COUNT} -gt 0 ]]; then
        send_event "JOB_INFO" "Restarting RNAsik after (temporary?) failure (retry $RETRY_COUNT)."
        sleep ${RETRY_DELAY}
    fi

    if [[ -z "${PAIRIDS}" ]]; then
        ${PREFIX_JOB_CMD} \
           RNAsik \
               -configFile ${JOB_PATH}/input/sik.config \
               -align star \
               -fastaRef ${GENOME_FASTA} \
               ${GENOME_INDEX_ARG} \
               -fqDir ../input \
               -counts \
               -gtfFile ${GENOME_GTF} \
               -all \
               -extn ${EXTN} \
               >>rnasik.out 2>>rnasik.err
    else
        ${PREFIX_JOB_CMD} \
           RNAsik \
               -configFile ${JOB_PATH}/input/sik.config \
               -align star \
               -fastaRef ${GENOME_FASTA} \
               ${GENOME_INDEX_ARG} \
               -fqDir ../input \
               -counts \
               -gtfFile ${GENOME_GTF} \
               -all \
               -paired \
               -extn ${EXTN} \
               -pairIds ${PAIRIDS} \
               >>rnasik.out 2>>rnasik.err
    fi

    # Capture the exit code of the important process, to be returned
    # in the curl request below
    EXIT_CODE=$?

    RETRY_COUNT=$((RETRY_COUNT+1))
done

# Some job scripts might have things that occur after the main pipeline
# run - so we signal when the 'pipeline' computation completed, but this is
# considered a distinct event from the whole job completing (that will be
# generated as a side effect of calling JOB_COMPLETE_CALLBACK_URL)
if [[ ${EXIT_CODE} -ne 0 ]]; then
  send_event "JOB_PIPELINE_FAILED" "Pipeline failed." '{"exit_code":'${EXIT_CODE}'}'
else
  send_event "JOB_PIPELINE_COMPLETED" "Pipeline completed." '{"exit_code":'${EXIT_CODE}'}'
fi

update_permissions

cd "${JOB_PATH}"
register_files

####
#### Notify service we are done
####

# Authorization header passed to curl is stored in a @file so it doesn't leak in 'ps' etc.

send_job_finished "${EXIT_CODE}"

# Extra security: Remove the access token now that we don't need it anymore
if [[ ${DEBUG} != "yes" ]]; then
  rm "${AUTH_HEADER_FILE}"
fi
