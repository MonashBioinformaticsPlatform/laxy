# Laxy REST API

These are some rough WIP docs describing ways you might use the REST API from the commandline.

The 'definative' API docs are the OpenAPI/Swagger definition here: https://api.laxy.io/swagger/v1/

## Get authentication tokens

Login and go to: https://api.laxy.io/api/v1/user/profile/ and copy the "Secret API token" to use in the authentication header.

```bash

```bash
AUTH_HEADER="Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoid1VIMnRUbGw2bnR6TGp4RmdhVFQ2IiwidXNlcm5hbWUiOiJhbmRyZXcucGVycnkiLCJleHAiOjE1OTQ0MjgwMzQsImVtYWlsIjoiYW5kcmV3LnBlcnJ5QG1vbmFzaC5lZHUiLCJvcmlnX2lhdCI6MTU5NDA4MjQzNH0.aqAfo4d1ovMwP6dwU558QXCxydIKTHi9PgxNJXEhrlA"

# .. or, if you have a DRF token via the /admin interface
# AUTH_HEADER="Authorization: Token d63af460ffb42548871aa60985c9862b21be633a"
```

Add `-H "${AUTH_HEADER}"` to `curl` command line to use your credentials (can then exclude any `access_token` in query params or cookies).

----
```bash
JOB_ID=78bK6O9S6DxtQg4WeANyfz
# If you don't have an AUTH_HEADER, or are accessing a job shared via a 'secret link', 
# set the access_token query parameter ?access_token=${ACCESS_TOKEN}
ACCESS_TOKEN=41eac616-dc15-4046-a10e-9a59408b0308

# Get the input and output fileset ID
INPUT_FILESET=$(curl -v -L -H "Content-Type: application/json" \
                 "https://api.laxy.io/api/v1/job/${JOB_ID}/?access_token=${ACCESS_TOKEN}" \
                 | jq '.input_fileset_id' | tr -d \")

OUTPUT_FILESET=$(curl -v -L -H "Content-Type: application/json" \
                 "https://api.laxy.io/api/v1/job/${JOB_ID}/?access_token=${ACCESS_TOKEN}" \
                 | jq '.output_fileset_id' | tr -d \")

echo $INPUT_FILESET
echo $OUTPUT_FILESET

# List all the output files
curl -v -L -H "Content-Type: application/json" \
                 "https://api.laxy.io/api/v1/fileset/${OUTPUT_FILESET}/?access_token=${ACCESS_TOKEN}" \
           | jq '.files'


# Download a specific file

FILE_ID=3rjzJC2UlCZRiPrBpC6mcJ
FPATH=output
FNAME=run_job.out
FILEPATH="${FPATH}/${FNAME}"
mkdir -p ${FPATH}
curl -v -L \
     -b "access_token__${JOB_ID}=${ACCESS_TOKEN}" \
     "https://api.laxy.io/api/v1/job/${JOB_ID}/files/${FILEPATH}?access_token=${ACCESS_TOKEN}" >"${FILEPATH}"
```

Or download only based on file_id and filename, with auth header (no access token):
```bash
curl -v -L \
     -H "${AUTH_HEADER}" \
     "https://api.laxy.io/api/v1/file/${FILE_ID}/content/${FNAME}"
```
