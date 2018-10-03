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
