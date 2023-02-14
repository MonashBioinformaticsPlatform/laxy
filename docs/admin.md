
## Adding a new ComputeResource

The private key used to access the compute resource is provided as a Base64 encoded string.
Generate a new SSH private key for use with Laxy, copy and paste it as the `private_key` 
variable in the `extra` JSON blob for the new compute resource.
```
# ssh-keygen -t rsa -b 4096 -m PEM -f ~/.ssh/laxy-compute-resource
ssh-keygen -t rsa -b 4096 -f ~/.ssh/laxy-compute-resource
echo; echo; base64 -f ~/.ssh/laxy-compute-resource | tr -d '[[:space:]]'; echo; echo
```

Ensure the associated public key (eg `~/.ssh/laxy-compute-resource.pub`) is added to
`~/.ssh/authorized_keys` on the compute resource host. It's a good idea to test that
you can login manually using SSH with the generated private key and username.

### Directory structure on a compute node

This is the directory structure that pipeline `run_job.sh` scripts should expect, relative to
the `base_dir` defined for a `ComputeResource`.

```
{base_dir}.
          ├── tmp
          ├── cache
          │   ├── singularity
          │   ├── pipelines
          │   └── downloads
          │               ├── .laxydl_cache
          │               └── .aria2_rpc_secret-{hostname}
          ├── config
          │   ├── nextflow.config
          │   └── rnasik
          ├── jobs
              ├── {job_ids}
              └── miniconda3
```
Cached input download files are stored in `cache/downloads` with filenames based on a hash of the URL. 
The empty file `.laxydl_cache` must be present here to allow `laxydl` to expire old cached files.
The `aria2c` RPC secret is also stored here (if the `aria2c` daemon reports `Unauthorized` when `laxydl`
attempts to connect, this file may have somehow got out of sync with the running server. Remove this file 
and kill the running `aria2c` daemon process).

Cached Singularity images and nf-core pipelines are stored in `cache/singularity` and `cache/pipelines` respectively.

Config files specific to this `ComputeResource` that a `run_job.sh` script may depend on are kept in `config` (and 
pipeline-specific sub-directories inside `config`).

Job folders are created in `jobs`, with the `{job_id}` as a directory name.
The `miniconda3` directory contains a conda installation and enviroments for specific pipeline versions.
(This conda location is deprecated - in the future the `miniconda3` directory will be moved into `cache`)

The `tmp` path should have _enough_ storage and is generally used by `run_job.sh` and pipelines in preference 
to the usual default `/tmp` which is often size contrained. 

## Adding additional pipelines

Example pipelines exist in `laxy_pipeline_apps`.

A pipeline consists of:
- a Django app containing:
  - an apps.py defining `LAXY_JOB_TEMPLATES` and `LAXY_PIPELINE_NAME`
  - skeleton job template(s) (eg a `run_job.sh` in `templates/job_scripts/{{ pipeline name }}/default/input/scripts`)
  - the pipeline app needs to be added to `INSTALLED_APPS` in Django settings (eg `laxy/default_settings.py`)
- a `Pipeline` record in the database with JSON `metadata` blob (`{"versions": ["1.0"], "default_version": "1.0", "short_description": "thepipelinename"}`)
  - for Pipeline objects not set as `public`, you need to add Object Permissions for Users and/or Groups, `view_pipeline` and `run_pipeline` (this can be done in Django admin - eg, create a group `guinea.pigs`, add users to it, then on the `Pipeline` record add those object permissions for the `guinea.pigs` group)
  - (TODO: Django app for each pipleline should probably automatically create the a initial Pipeline object)
- **TODO:** an npm package containing UI components, a Vuex store module defining job parameters, default routes
  - the frontend parts of each pipeline currently live in `laxy_frontend/src/components/pipelines`, but in the future this should be modularized
  - a mapping between the pipeline name and it's initial setup page Vue component needs to be made in `laxy_frontend/src/routes.ts` (inside `addPipelineRoutes`). The backend sends a list of available pipelines and metadata via a REST request. The pipeline name (with dashes replacing underscores) is used in the URL.


### TBD - details for npm package and pipeline plugin API:
- The frontend parts of a pipeline currently live in `laxy_frontend/src/components/pipelines`. 
  These need to be moved out into installable npm packages that can be integrated into the frontend with `npm build`.
- Need to define details of npm package - UI, Vuex store, default routes, pipeline 'plugin' registration
  - Vuex module should add specific values to the existing pipelineParams
  - route might be added via a Vuex mutation / action, to a route mapping in the root store ? (plugin can call routes.addPipelineRoutes itself)
  - a simple mechanism to register this module (ideally some imports and a single line in 'pipelines_config.ts')
