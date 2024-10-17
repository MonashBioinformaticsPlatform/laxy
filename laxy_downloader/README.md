# Laxy clientside downloader

A utility to download input data for jobs via parsing `pipeline_config.json`.
Intended to be run by the job script on a compute node.

### Install

```bash
pip install -e git+https://github.com/MonashBioinformaticsPlatform/laxy/laxy_downloader@master#egg=laxy_downloader
```

### Usage
See: `laxydl --help`

Example:
```bash
laxydl --pipeline-config pipeline_config.json --no-progress --destination-path /shared/jobs/XYZZY/input/


Or a more complex test, demonstrating concurrent downloads of the same URL(s) with multiple processes into the same cache directory (eg, in the case where two jobs have the same input file):
```bash
mkdir -p /tmp/laxydl_cache /tmp/laxydl_test /tmp/laxydl_test2 /tmp/laxydl_test3

laxydl download -vvv --cache-path /tmp/laxydl_cache --no-progress --unpack --parallel-downloads 4 --pipeline-config laxy_downloader/tests/test_data/pipeline_config_smaller.json --create-missing-directories --skip-existing --destination-path /tmp/laxydl_test --no-aria2c &

laxydl download -vvv --cache-path /tmp/laxydl_cache --no-progress --unpack --parallel-downloads 4 --pipeline-config laxy_downloader/tests/test_data/pipeline_config_smaller.json --create-missing-directories --skip-existing --destination-path /tmp/laxydl_test2 --no-aria2c &

laxydl download -vvv --cache-path /tmp/laxydl_cache --no-progress --unpack --parallel-downloads 4 --pipeline-config laxy_downloader/tests/test_data/pipeline_config_smaller.json --create-missing-directories --skip-existing --destination-path /tmp/laxydl_test3 --no-aria2c &

# Wait for all background jobs to finish
wait

ls -lah /tmp/laxydl_cache
ls -lah /tmp/laxydl_test*
```

### Development

```bash
git clone https://github.com/MonashBioinformaticsPlatform/laxy
cd laxy/laxy_downloader

mkdir -p ~/.virtualenvs
virtualenv -p python3 ~/.virtualenvs/laxydl
source ~/.virtualenvs/laxydl/bin/activate

# We need to pip install first, rather than `python setup.py install`, 
# since one of the dependencies (pyaria) fails otherwise
pip install .
# Running this symlinks the library installed in the virtualenv to your working copy
python setup.py develop

# Run tests
pip install pytest
pytest
```