# Laxy REST API

These are some rough WIP docs describing ways you might use the REST API from the commandline.

The definitive API docs are the OpenAPI/Swagger definition:

- Swagger UI: https://api.laxy.io/api/v1/schema/swagger-ui/
- Raw OpenAPI schema: https://api.laxy.io/api/v1/schema/
- ReDoc: https://api.laxy.io/api/v1/schema/redoc/

## Get authentication tokens

Create a named API key in the web UI (avatar menu → **API Keys**). The secret is shown once. Send it as:

```bash
AUTH_HEADER="Authorization: Bearer laxy_…"
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
