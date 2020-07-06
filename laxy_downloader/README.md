# Laxy clientside downloader

A utility to download input data for jobs via parsing `pipeline_config.json`.
Intended to be run by the job script on a compute node.

### Install

```bash
pip install -e git+https://github.com/MonashBioinformaticsPlatform/laxy/laxy_downloader#egg=laxy_downloader
```

### Usage
See: `laxydl --help`

Example:
```bash
laxydl --pipeline-config pipeline_config.json --no-progress --destination-path /shared/jobs/XYZZY/input/
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
```