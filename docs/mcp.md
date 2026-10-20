# Laxy MCP 2.0

Endpoint: **`POST /api/v1/mcp/`** (MCP protocol version `2026-07-28`, sessionless).

## Client config

Add this (or equivalent) to your agent config:

```json
{
  "mcpServers": {
    "laxy": {
      "type": "http",
      "url": "https://api.laxy.io/api/v1/mcp/",
      "headers": { "Authorization": "Bearer ${LAXY_API_TOKEN}" }
    }
  }
}
```

For Claude Code, you can run:
```bash
claude mcp add --transport http --scope user laxy \
  https://api.laxy.io/api/v1/mcp/ \
  --header "Authorization: Bearer ${LAXY_API_TOKEN}"
```
The `LAXY_API_TOKEN` should be a **named API key** created in the Laxy web UI (**API Keys** in the avatar menu). Paste it into the JSON config, or export `LAXY_API_TOKEN` in `.bashrc` / `.zshrc`. The profile JWT expires after 14 days; the legacy DRF authtoken from `GET /api/v1/user/profile/` still works but is not recommended for new agent configs.

## Details

### Why MCP instead of just the REST API?

MCP does not replace the REST API. Agents still use REST for large file downloads (and anything outside the tool set). The advantage is for **interactive agent sessions** (Cursor, Claude Desktop, and similar):

1. **Native tool wiring** — Clients register one URL + bearer token and expose Laxy as first-class tools. The agent does not need to invent `curl` against OpenAPI, remember auth schemes, or paste endpoint docs into the prompt.
2. **Discoverable, task-shaped surface** — `tools/list` returns a small set of named operations with descriptions and schemas (`laxy_list_jobs`, `laxy_get_job_eventlogs`, …). That is easier for an LLM to choose correctly than the full REST catalogue (pagination, nested creates, FileSet filters, etc.).
3. **Curated multi-step flows** — One tool call often replaces several REST round-trips and response shaping (e.g. resolve a relative path → file id → safe read-or-download-url). Tool copy documents limits (inline size caps, write gating) so agents fail closed instead of hanging on a multi-megabyte SFTP stream.
4. **Safer write boundary** — Submit/clone/start can stay off by default (`LAXY_MCP_ENABLE_WRITE_TOOLS`) and carry `destructiveHint`, without exposing every REST write verb to the agent by default.
5. **Server instructions** — MCP carries product-level guidance in the protocol; OpenAPI alone does not.

Prefer MCP for browse / diagnose / light mutate workflows with an agent. Prefer REST (or `laxycli`) for scripts, CI, bulk transfer, and any operation not covered by a tool. When MCP returns a `download_url`, fetch that URL over REST (no Authorization header required — see below).

### File download URLs

`laxy_list_job_files` and `laxy_read_job_file` return **metadata** (and, for read, optional text). They do not mint tokens. Use `laxy_get_download_urls` (by `file_ids` / `paths` / `path_glob` / `path_prefix`) or `laxy_get_job_tarball_urls` to mint one short-lived **job-scoped** `mcpdl.*` `AccessToken` (default TTL **1 hour**, max **3 hours** via `LAXY_MCP_JOB_DOWNLOAD_TOKEN_MAX_HOURS` / `expires_in_seconds`). List pagination is `page` and `page_size`.

UI share tokens and `mcpdl.*` download tokens are separate. `/job/{id}/accesstoken/` ignores `mcpdl.*`. After downloads finish, call `laxy_revoke_download_tokens(job_id)`. `laxy_revoke_job_share` only removes the UI share link.

- Agents should download with `curl -fL -o <name> '<download_url>'` (`-f` so a 504/HTML error page is not saved as the file). Do **not** put the long-lived MCP/DRF token in the curl command.
- File rows include `availability`: `online` or `archive` (default location is an archive host; downloads may stall or 504 while staging). Nginx read timeout for `/api/v1/file/*/content/` is 1 hour.
- Or append `?access_token=<token>` to `download_path` / `api_base_url`.
- Re-call `laxy_get_download_urls` before expiry to refresh.

### Authentication

| Credential | Source | Expiry | Recommended for MCP |
|------------|--------|--------|---------------------|
| Named API key (`laxy_…`) | Web UI **API Keys**, or `POST /api/v1/user/api-keys/` | Optional (7/30/90 days, never, or custom) | **Yes** |
| DRF authtoken | `GET /api/v1/user/profile/` → `drf_authtoken` | None | Legacy |
| SimpleJWT access | same profile → `token`, or `POST /api/v1/auth/jwt/get/` | 14 days | No (no MCP refresh) |

Clients must send:

```http
Authorization: Bearer <api_key_or_drf_or_jwt>
```

Named API keys and DRF tokens normally use different REST schemes; the MCP verifier (and REST `UserApiKeyAuthentication`) accept `laxy_…` keys over `Bearer`. DRF tokens are still accepted over Bearer for MCP so existing configs keep working.

Missing/invalid tokens receive `401` with `WWW-Authenticate: Bearer`.

### Tools

| Tool | Access | Notes |
|------|--------|-------|
| `laxy_list_jobs` | read | `page` / `page_size` (default 10). `status` schema enum includes null plus created, hold, starting, running, failed, cancelled, complete |
| `laxy_diagnose_job` | read | Status, recent events, tail of `output/run_job.out` |
| `laxy_list_compute_resources` | admin | Staff only (`is_staff`). Omitted from `tools/list` otherwise. `page` / `page_size`. Same fields as `GET /api/v1/compute-resource/`, which omits `extra` (no SSH keys) |
| `laxy_get_job` | read | Full job + `job_url`. Optional `include_log_tail` |
| `laxy_get_job_eventlogs` | read | `page` / `page_size` or `offset`; `event` substring filter |
| `laxy_list_job_files` | read | Metadata only. `page` / `page_size`. No download tokens |
| `laxy_get_download_urls` | read | One `mcpdl.*` token + URLs. `max_files` caps the selection |
| `laxy_read_job_file` | read | `tail_lines` and `grep`. Downloads via `laxy_get_download_urls` |
| `laxy_list_pipelines` | read | `versions`, `default_version`, `params_schema`, `param_defaults` |
| `laxy_list_reference_genomes` | read | `search`, `page`, `page_size` |
| `laxy_get_pipeline_run` | read | Inspect a PipelineRun (e.g. after clone) |
| `laxy_get_sample_cart` | read | Inspect a SampleCart (e.g. after clone) |
| `laxy_ena_query` | read | ENA metadata. Optional `fields` prunes the JSON |
| `laxy_ena_fastq_urls` | read | ENA run table / FASTQ FTP URLs |
| `laxy_samples_from_ena` | read | Accessions → `samples` for `laxy_submit_job` |
| `laxy_remote_browse` | read | One-level FTP/HTTP(S)/Zenodo/Nextcloud listing |
| `laxy_submit_job` | write | Typed samples `{name, files: [{R1, R2?}]}`. `dry_run=true` validates only |
| `laxy_clone_job` | write | Copies cart + run (not destructive). Optional `params` / `samples` / `start=true`. `dry_run=true` creates nothing |
| `laxy_update_pipeline_run` | write | PATCH params/description before start |
| `laxy_update_sample_cart` | write | PUT samples before start |
| `laxy_start_job` | write | Queue a Job. `dry_run=true` checks the run without creating it |
| `laxy_cancel_job` | write | `PATCH status=cancelled` |
| `laxy_get_job_share` | read | Current UI share token + URL. Does not write |
| `laxy_share_job` | write | Mint or update the UI share token |
| `laxy_revoke_job_share` | write | UI share token only |
| `laxy_revoke_download_tokens` | write | `mcpdl.*` download tokens only |
| `laxy_get_job_tarball_urls` | read | tar.gz URLs with `mcpdl.*` token |
| `laxy_send_to_degust` | write | `job_id` auto-picks featureCounts; `file_id` overrides |

### Clone → edit → run

`laxy_clone_job` matches the REST `/job/{id}/clone/` endpoint: it duplicates the sample cart and pipeline run and returns `pipelinerun_id` / `samplecart_id`. It does not create a Job unless `start=true`.

To re-run (optionally with edits):

1. `laxy_clone_job(job_id)` → `pipelinerun_id`, `samplecart_id`
2. Optional: `laxy_get_pipeline_run` / `laxy_update_pipeline_run`, `laxy_get_sample_cart` / `laxy_update_sample_cart`, or pass `params` / `samples` on the clone call
3. `laxy_start_job(pipeline_run_id)` or `laxy_clone_job(..., start=true)` queues the job

`dry_run=true` on submit or start validates without queueing. Samples are `{name, files: [{R1, R2?}]}` per lane. `laxy_samples_from_ena` builds that list. `laxy_list_pipelines` returns allowed `versions` and any `params_schema`.

`laxy_list_compute_resources` is only listed when the MCP token belongs to a Django staff user.


## Development

The MCP feature is implementated using: [`django-stateless-mcp`](https://pypi.org/project/django-stateless-mcp/) + official `mcp` 2.0 SDK, tools in [`laxy_backend/mcp.py`](../laxy_backend/mcp.py), auth in [`laxy_backend/mcp_auth.py`](../laxy_backend/mcp_auth.py).

Quick check with curl (replace token and host):

```bash
curl -sk -X POST 'https://localhost:8001/api/v1/mcp/' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H "Authorization: Bearer $LAXY_API_TOKEN" \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/list' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"curl","version":"0.1"}}}}'
```

### Development history

Two designs were considered and tested:

1. **In-Django** (`django-stateless-mcp`) — chosen. Direct ORM + guardian, one process, GA `mcp` 2.0.
2. **Sidecar** (`laxy_mcp/`) — REST proxy over uvicorn. Works, but extra service, auth scheme translation, and N+1 REST calls for diagnostics. Removed from the tree after the spike; the code remains in git history. It was never wired into Compose.

`django-mcp-server` was ruled out: it targets handshake-era MCP (`mcp` 1.x), not `2026-07-28`.

## Production serving notes

- Local `runserver` and gunicorn **`gthread`** / sync workers serve the async MCP view without special flags.
- Gunicorn **`--worker-class gevent`** (current prod default) monkey-patches threads; MCP auth sets `DJANGO_ALLOW_ASYNC_UNSAFE` for the token lookup only. Prefer routing `/api/v1/mcp/` to a `gthread` replica if that becomes an issue.
- `subscriptions/listen` streams require ASGI and return `501` under WSGI (not needed for the current tool surface).

## Possible future work for the MCP feature

- OAuth2 + Dynamic Client Registration + RFC 9728 protected-resource metadata for hosted clients (Claude web, etc.). `django-oauth-toolkit` is already installed.
- Optional elicitation confirm before `laxy_submit_job`.
