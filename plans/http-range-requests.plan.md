# Plan: HTTP Range Request support for file streaming (+ IGV BAM viewing)

Issue: https://github.com/MonashBioinformaticsPlatform/laxy/issues/8
Branch: `feature/http-range-requests` (off `develop`)

## Goal

Make Laxy's Django file-serving endpoints honour HTTP `Range` requests
(RFC 7233) so that byte-range-capable clients — chiefly **IGV** and
**igv.js** — can stream slices of large files (BAM + `.bai` index) without
downloading the whole file. This is the load-bearing feature.

Secondary, in priority order once Range works:
1. Path-traversal hardening + a small storage abstraction so `file://`,
   `s3://`/`local://` can be supported cleanly alongside `laxy+sftp://`.
2. An IGV session/config (`.xml`) link-out per BAM.
3. An embedded `igv.js` viewer in the Vue frontend.

Only item 0 (Range) is required for this issue to be "done"; 1–3 are
staged so they can land incrementally.

---

## Background: how file serving works today

Verified against the current tree (line numbers approximate, confirm before editing):

- **Entry views** (`laxy_backend/views.py`):
  - `FileContentDownload.get` (~L781) → route `file/<uuid>/content/<filename>`
    (`laxy_backend/urls.py` ~L211, name `file_download`).
  - `FileView.get` (~L883) → route `file/<uuid>/` (name `file`); streams
    bytes unless `Content-Type: application/json` is requested.
  - `JobFileView.get` (~L1050) → route `job/<uuid>/files/<file_path>`
    (`urls.py` ~L157, name `job_file`), decorated with `@etag_headers`
    (`laxy_backend/view_mixins.py` ~L34). **This is the primary IGV target**
    (BAM + `.bai` resolved by path within a job).
- **Shared streaming machinery** — `StreamFileMixin` (`views.py` ~L668):
  - `_stream_response(obj_ref, filename=None, download=True)` (~L710) builds
    a `StreamingHttpResponse(renderer.render(obj.file), ...)`, sets
    `Content-Disposition`, `Content-Type`, `Content-Length` (from
    `obj.file.size` / `obj.metadata["size"]`), and metalink headers
    (`Link`, `Digest`, strong `Etag` = checksum) via `_add_metalink_headers`
    (~L685). **It never reads `Range`, never sets `Accept-Ranges`, never
    returns 206.**
  - `download()` / `view()` (~L767) just call `_stream_response`.
  - `StreamingFileDownloadRenderer.render(filelike, ..., blksize=8192)`
    (~L461) wraps the file object in `wsgiref.util.FileWrapper` and yields
    8 KB chunks from the current position to EOF. **This is where the byte
    window must be applied.**
- **Resolving a File to a stream** — `laxy_backend/models.py`:
  - `File.file` property (~L1767) → `File._file(location)` (~L1722):
    - `laxy+sftp://` → `SFTPStorage.open(abs_path)` → paramiko-backed
      `SFTPStorageFile` — **seekable** (`paramiko.SFTPFile` supports
      `seek`/`read`/`prefetch`).
    - `file://` → `FileSystemStorage(location="/").open(full_path)` —
      **seekable** (regular file).
    - `http/https/ftp/ftps/data` → `requests(..., stream=True).raw` —
      **NOT seekable** (forward-only stream).
  - `File.size` (~L1787) returns `metadata["size"]` or lazily stats via the
    backend and caches it — use this for `Content-Range` total without
    opening the stream.
- **Deploy / proxy**: gunicorn with **gevent** async workers
  (`docker-compose.prod.yml`), behind **nginx**
  (`docker/laxy-static-nginx/nginx.conf.template`) which proxies the API to
  `django:8001` with `proxy_buffering off;` and `proxy_http_version 1.1`.
  There is **no `X-Accel-Redirect`/`internal;` offload** — all dynamic file
  bytes flow through Django. Good news: partial/streamed responses already
  pass through the proxy, and nginx does not rewrite `Range`/`206`/
  `Content-Range` by default.
- **Versions**: Django 5.2.x, DRF 3.16.x, django-storages 1.14.6,
  paramiko 2.12.0, Python 3.12-era. Tests are **pytest**
  (`DJANGO_SETTINGS_MODULE=laxy.test_settings`), backend tests in
  `laxy_backend/tests/`.

### Reference implementation

The dcwatson gist
(https://gist.github.com/dcwatson/cb5d8157a8fa5a4a046e) is the starting
point: a `RangeFileWrapper` that `seek()`s to an offset and yields at most
`length` bytes in `blksize` chunks, plus a view that returns `206` with
`Content-Range`/`Content-Length` and `Accept-Ranges: bytes` on `200`.
Adapt it — do **not** copy verbatim — because:
- It calls `.next()` (Py2); we need `__next__`.
- Its regex only matches `bytes=<int>-<int?>` and **misses suffix ranges**
  (`bytes=-500`), which htsjdk/IGV do use.
- It opens local paths with `open(path)`; we must go through
  `File.file` / the storage backend.
- It handles a single range only (fine for us — see below).

---

## Phase 0 — Branch (DONE)

`feature/http-range-requests` created off `origin/develop`.

---

## Phase 1 — Range support in Django (REQUIRED)

### 1a. New module `laxy_backend/http_range.py`

Contains a parser and a bounded file-wrapper, unit-testable in isolation.

```python
import re
from typing import List, Optional, Tuple

# Single-range only (we deliberately don't support multipart/byteranges).
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$", re.IGNORECASE)


class InvalidRange(Exception):
    """Range header present but unsatisfiable -> caller should return 416."""


def parse_range_header(range_header: str, size: int) -> Optional[Tuple[int, int]]:
    """
    Parse a single-range 'Range: bytes=...' header against a known total size.

    Returns (first_byte, last_byte) inclusive, or None if there is no usable
    range header (caller should serve full 200). Raises InvalidRange for a
    syntactically valid but unsatisfiable range (caller returns 416).

    Handles:
      bytes=0-499      -> (0, 499)
      bytes=500-       -> (500, size-1)
      bytes=-500       -> suffix: last 500 bytes -> (size-500, size-1)
    Multi-range (comma) is treated as "no usable single range" -> None
    (fall back to full 200) to keep things simple and correct.
    """
    if not range_header:
        return None
    if "," in range_header:      # multipart byteranges: don't attempt
        return None
    m = _RANGE_RE.match(range_header.strip())
    if not m:
        return None
    start_s, end_s = m.group(1), m.group(2)

    if start_s == "" and end_s == "":
        return None
    if size == 0:
        raise InvalidRange("empty file")

    if start_s == "":                       # suffix range: bytes=-N
        n = int(end_s)
        if n == 0:
            raise InvalidRange("zero-length suffix")
        first = max(0, size - n)
        last = size - 1
    else:
        first = int(start_s)
        last = int(end_s) if end_s != "" else size - 1
        last = min(last, size - 1)

    if first > last or first >= size:
        raise InvalidRange(f"range {first}-{last} outside 0-{size - 1}")
    return first, last


class RangeFileWrapper:
    """
    Iterable that seeks `filelike` to `offset` and yields at most `length`
    bytes in `blksize` chunks. `filelike` must be seekable.
    """

    def __init__(self, filelike, offset: int = 0, length: Optional[int] = None,
                 blksize: int = 8192):
        self.filelike = filelike
        try:
            self.filelike.seek(offset)
        except Exception:
            # Non-seekable backend: read-and-discard up to offset as a
            # fallback (correct but slow). Prefer to avoid by checking
            # seekability before choosing to serve a range at all.
            self._discard(offset)
        self.remaining = length
        self.blksize = blksize

    def _discard(self, n: int):
        while n > 0:
            chunk = self.filelike.read(min(n, self.blksize))
            if not chunk:
                break
            n -= len(chunk)

    def close(self):
        if hasattr(self.filelike, "close"):
            self.filelike.close()

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining is not None and self.remaining <= 0:
            raise StopIteration()
        read_size = self.blksize if self.remaining is None \
            else min(self.remaining, self.blksize)
        data = self.filelike.read(read_size)
        if not data:
            raise StopIteration()
        if self.remaining is not None:
            self.remaining -= len(data)
        return data
```

Notes for the implementer:
- Keep the parser **single-range**. IGV/htsjdk issue single-range requests;
  multipart/byteranges responses are complex and unnecessary. On a
  multi-range header we return `None` → full `200` (spec-compliant: a server
  MAY ignore Range).
- `paramiko.SFTPFile.seek()` is supported. To avoid a synchronous SSH
  round-trip per 8 KB chunk (slow for large ranges), consider calling
  `filelike.prefetch(<length>)` when the backend exposes it and the range is
  large — paramiko 2.12 `SFTPFile.prefetch(file_size=None)` pipelines reads.
  Guard with `hasattr(filelike, "prefetch")` and only prefetch the requested
  window, not the whole file. Treat as an optimisation, land correctness first.

### 1b. Determine seekability / whether a range can be served

Add a helper on `File` (in `models.py`) so the view doesn't sniff schemes:

```python
@property
def supports_range(self) -> bool:
    """True if the backing store can serve byte ranges by seeking."""
    scheme = urlparse(str(self.location)).scheme
    return scheme in ("laxy+sftp", "sftp", "file")
    # http/https/ftp/data go through requests' forward-only .raw stream.
```

(Deliberately conservative. Phase 2 can upgrade `s3://` to a native ranged
GET and flip this to `True` for it.)

### 1c. Teach the renderer to apply a byte window

Modify `StreamingFileDownloadRenderer.render` (`views.py` ~L461) to accept an
optional `(offset, length)` and use `RangeFileWrapper` instead of
`FileWrapper` when a window is set:

```python
def render(self, filelike, media_type=None, renderer_context=None,
           blksize=8192, offset=0, length=None):
    if offset or length is not None:
        iterable = RangeFileWrapper(filelike, offset=offset,
                                    length=length, blksize=blksize)
    else:
        iterable = FileWrapper(filelike, blksize=blksize)
    try:
        for chunk in iterable:
            yield chunk
    except ssh_exception.SSHException as ex:
        ...  # unchanged
```

Caveat: `render` is a **generator** wrapped by `@backoff.on_exception`.
`backoff` wraps the *call that creates the generator*, not iteration, so it
only retries construction, not mid-stream failures. This is pre-existing
behaviour — don't regress it, but note that a Range read that fails partway
still surfaces as a broken stream. No change required for this issue.

### 1d. Range logic in `_stream_response`

Rework `_stream_response` (`views.py` ~L710) to:

1. Resolve `obj` and `obj.file` as today (keep the 404 branches).
2. Set `Accept-Ranges: bytes` on **every** byte response (200 and 206) when
   `obj.supports_range` is true; set `Accept-Ranges: none` otherwise so
   clients don't attempt ranges the backend can't honour.
3. Read `request.headers.get("Range")`. If absent or `obj.supports_range` is
   false → serve full `200` exactly as today.
4. If present and supported:
   - Compute `total = obj.size` (needed for `Content-Range`). If `size` is
     `None` (backend can't stat) → fall back to full `200` (can't build a
     valid `Content-Range`).
   - `parse_range_header(range_header, total)`:
     - returns `None` → full `200`.
     - raises `InvalidRange` → return `416 Range Not Satisfiable` with
       `Content-Range: bytes */<total>` and an empty body.
     - returns `(first, last)` → `length = last - first + 1`; build:
       ```python
       response = StreamingHttpResponse(
           renderer.render(obj.file, offset=first, length=length),
           status=206,
           content_type=renderer.media_type,
       )
       response["Content-Range"] = f"bytes {first}-{last}/{total}"
       response["Content-Length"] = str(length)
       response["Accept-Ranges"] = "bytes"
       ```
5. Keep `Content-Disposition`/`Content-Type` logic. For `inline` (view) set
   the guessed content-type as today; for BAM the type is
   `application/octet-stream` which is fine for IGV.
6. Keep `_add_metalink_headers` (strong checksum `Etag`, `Digest`, `Link`).
   For `200` keep `Content-Length` from `obj.file.size`/metadata.
7. **`If-Range`**: optional but recommended for correctness. If the client
   sends `If-Range: <validator>` and it does **not** match the current
   strong `Etag` (checksum) or `Last-Modified`, ignore the Range and return
   the full `200`. Use the **strong** checksum `Etag` from
   `_add_metalink_headers`, not the weak `W/"..."` one added by
   `@etag_headers` (weak validators are invalid for `If-Range`). Note the
   comment at `view_mixins.py` ~L51 that nginx may strip strong ETags —
   verify end-to-end (Phase 3). If ETag survival is unreliable, prefer
   `Last-Modified`/`If-Range` on date. For a first cut it's acceptable to
   skip `If-Range` and always honour a well-formed Range (BAM content is
   immutable once written, so staleness risk is low).

### 1e. HEAD request support

IGV/htsjdk and browsers often issue a `HEAD` (or a `Range: bytes=0-0` probe)
to learn the size and `Accept-Ranges` before ranged GETs.

- `GetMixin` handles GET only. Add a `head()` on `StreamFileMixin` (and wire
  it through `FileContentDownload`, `FileView`, `JobFileView`) that returns
  an empty body with `Content-Length: <size>`, `Accept-Ranges: bytes`,
  `Content-Type`, and the metalink headers — **no** stream opened.
- Django will also answer HEAD by running GET and discarding the body if a
  `head()` isn't defined, but that needlessly opens an SFTP stream; an
  explicit `head()` is cheaper. Confirm DRF `APIView.http_method_names`
  includes `head` (it does by default) and that `@etag_headers` on
  `JobFileView` tolerates HEAD.

### 1f. Endpoint wiring

`FileContentDownload`, `FileView`, `JobFileView` all funnel through
`_stream_response`, so Range works for all three once the mixin is updated.
`JobFileView` is the one IGV will hit (`job/<uuid>/files/<path>` for both
`aln.bam` and `aln.bam.bai`). Confirm the `?access_token=` readonly-auth
query param still works for ranged/HEAD requests (IGV can append query
params to a URL).

### 1g. Non-seekable backends (http/ftp) — explicit decision

For `http/https/ftp/ftps/data` locations, `File._file` yields a forward-only
`requests` `.raw` stream. Do **not** attempt ranges there in this phase:
`supports_range` is false → `Accept-Ranges: none` and full `200`. Log at
`debug` when a Range is requested against such a file. (Phase 2 can add
pass-through: re-issue the upstream request with the client's `Range` header
and relay `206`/`Content-Range` — but that's out of scope for the issue.)

---

## Phase 2 — Path-traversal hardening + storage abstraction (easy wins)

These are opportunistic; land them if cheap, but don't block Range on them.

### 2a. Fix `..` traversal in `File._abs_path_on_compute` (models.py ~L1653)

Current code:
```python
file_path = str(Path(base_dir) / Path(url.path).relative_to("/"))
```
`Path(url.path)` is **not normalised**, so a `location` whose path contains
`../` escapes `base_dir`. Locations are normally server-generated
(`util.laxy_sftp_url`), but `File.location` is settable by clients via
`PUT /job/<uuid>/files/<path>` (`JobFileView.put` ~L1124) and File-create
serializers (`serializers.py` ~L202 validates the *scheme* only). Harden:

```python
base = Path(base_dir).resolve()
rel = Path(url.path).relative_to("/")
candidate = (base / rel)
# reject traversal without touching the remote FS
norm = os.path.normpath(str(candidate))
if not (norm == str(base) or norm.startswith(str(base) + os.sep)):
    raise SuspiciousFileOperation(f"path escapes base_dir: {url.path}")
file_path = norm
```
Add a unit test with a `../../etc/passwd`-style location. Also tighten the
`split_laxy_sftp_url` path guard (`util.py` ~L284) to reject `..` segments.

### 2b. Tighten the `job_file` URL / lookup

`JobFileView` already derives `Path(file_path).name` + `.parent` and does an
exact DB `filter(name=..., path=...)`, so lookups are DB-bound (good). Leave
the regex but make sure the traversal fix in 2a covers the resolved location.

### 2c. Small storage abstraction for `file://` / `s3://` / `local://`

Goal: centralise scheme → (open, size, seekable, ranged-open) so views never
branch on scheme. Minimal, non-disruptive shape:

- Keep `File._file` but add `File.open_range(first, last)` that returns a
  seekable window using the best method per backend:
  - `laxy+sftp`/`file`: `f = self.file; f.seek(first)` then bounded read
    (what Phase 1 already does).
  - `s3` (new, via django-storages `S3Boto3Storage`, already a dependency
    through `boto3`/`storages`): issue a native ranged
    `get_object(Range="bytes=first-last")` and return the body stream — this
    is the *correct* efficient path for S3; then flip `supports_range` true
    for `s3`.
  - `local://` — decide semantics: treat as an alias of `file://` rooted at
    a configured safe base dir (NOT `/`). The existing `file://` →
    `FileSystemStorage(location="/")` is flagged unsafe
    (`get_storage_class_for_location` ~L1205); rework so both `file://` and
    `local://` resolve against a settings-defined allow-listed root, closing
    the arbitrary-read TODO.
- Register schemes in `SCHEME_STORAGE_CLASS_MAPPING` (models.py ~L81) rather
  than in `if/elif` ladders.

Keep this additive — the RNAseq/BAM use case is `laxy+sftp` only, so ship
Phase 1 without waiting on S3.

---

## Phase 3 — Proxy / infra verification

- **nginx** (`docker/laxy-static-nginx/nginx.conf.template`): the API block
  already has `proxy_buffering off; proxy_http_version 1.1;`. Verify with a
  live ranged request through the proxy that:
  - The client `Range` header reaches Django (it should; nginx forwards
    unknown request headers by default).
  - The `206`, `Content-Range`, `Accept-Ranges` responses pass through
    unmodified.
  - The strong `Etag` survives (the code comment at `view_mixins.py` ~L51
    warns nginx may strip it — confirm and, if stripped, don't rely on it for
    `If-Range`).
  - `proxy_read_timeout 120;` doesn't truncate a large single ranged read on
    a slow SFTP link — bump if needed for the download location block only.
- **gunicorn gevent** workers stream fine; no change expected.
- No `X-Accel-Redirect` work needed. (If, later, `file://`/`local://` content
  lives on a path nginx can read, an `internal;` + `X-Accel-Redirect` offload
  would let nginx serve ranges natively and take load off Django — note as a
  future optimisation, not part of this issue.)

---

## Phase 4 — Tests

Add to `laxy_backend/tests/`. Follow existing pytest style
(`laxy.test_settings`).

Unit (no network) — `test_http_range.py` (new), against `http_range.py`:
- `parse_range_header` table: `bytes=0-499`, `bytes=500-`, `bytes=-500`,
  `bytes=0-0`, `bytes=-0` (→ InvalidRange), start beyond EOF (→ InvalidRange),
  `last` clamped to `size-1`, empty header (→ None), multi-range (→ None),
  malformed (→ None), zero-size file.
- `RangeFileWrapper` over a `io.BytesIO`: exact byte window returned;
  chunking respects `blksize`; `length=None` reads to EOF.

View-level — extend `test_views.py` (or new `test_range_views.py`), using
DRF `APIClient` and a `File` backed by a **local temp file** (`file://` or a
mocked seekable `File.file`) to avoid needing a live SFTP host:
- `GET` with no Range → `200`, body == full file, `Accept-Ranges: bytes`.
- `GET Range: bytes=0-9` → `206`, `Content-Range: bytes 0-9/<size>`,
  `Content-Length: 10`, body == first 10 bytes.
- `GET Range: bytes=<size-5>-` → `206`, last 5 bytes.
- `GET Range: bytes=-5` (suffix) → `206`, last 5 bytes.
- `GET Range: bytes=<size>-` (unsatisfiable) → `416` +
  `Content-Range: bytes */<size>`.
- `HEAD` → `200`, `Content-Length` set, `Accept-Ranges: bytes`, empty body,
  no stream opened (assert the storage `.open` wasn't called, or that no SSH
  happened).
- A non-seekable/`http://`-backed `File` → `Accept-Ranges: none`, Range
  ignored, full `200`.
- Path-traversal: a `File.location` with `../` → `_abs_path_on_compute`
  raises / `403`/`400` (Phase 2a).
- `?access_token=` readonly auth still works for ranged + HEAD.

Consider one integration test against the `docker/fake-cluster` SFTP host
(marked `integration`) that does a real ranged SFTP read, to catch paramiko
`seek` behaviour — but keep the default suite pure-Python.

---

## Phase 5 — IGV link-out via session/config XML (after Range works)

Once ranged `job/<uuid>/files/<path>` serving is verified with a real BAM +
`.bai` in IGV desktop:

- Add an endpoint (e.g. `job/<uuid>/igv-session.xml` or a per-file
  `?format=igv-session`) that emits an IGV session XML referencing the BAM
  and its index by absolute Laxy URLs (including `?access_token=` so IGV can
  fetch without interactive auth). IGV desktop can open a session URL
  directly and will issue ranged GETs against the BAM.
- Genome/reference: derive from the job's pipeline params
  (`laxy_genomes`/pipeline config) where available; otherwise let the session
  specify a genome id (e.g. hg38) or a reference URL.
- The `.bai` must be servable at the URL IGV derives (same path + `.bai`).
  Confirm the index File exists as a sibling in the job's output FileSet.

Provide it as a per-BAM "Open in IGV" link in the frontend file list (Phase
6), plus a "copy IGV session URL" action — directly addressing the issue's
"copy BAM link / set up session.xml for IGV" ask.

---

## Phase 6 — Embedded igv.js viewer (frontend, stretch)

The frontend is **Vue 2 + TypeScript** (`laxy_frontend/src/`), webpack, with
**no** igv.js/JBrowse today (only `ngl` for protein structures).

- Add `igv` (igv.js) as a dependency and a `IgvViewer.vue` component that
  mounts an igv.js browser configured with the BAM track URL
  (`WebAPI.viewJobFileByPathUrl` / `downloadJobFileByPathUrl` already build
  `/api/v1/job/<id>/files/<path>`; add an igv-oriented builder that appends
  `?access_token=`).
- Wire an "Open in genome browser" action into `FileList.vue` /
  `DownloadJobFilesTable.vue` for `.bam` files that have a sibling `.bai`.
- igv.js relies on Range GETs for BAM + `.bai`; Phase 1 is the prerequisite.
- Genome selection: reuse whatever reference metadata the job exposes; fall
  back to a genome picker.

---

## Suggested landing order (PRs)

1. **PR 1 (this issue):** Phase 1 (Range in Django) + Phase 4 unit/view tests
   + Phase 3 verification notes. This closes the core of #8.
2. **PR 2:** Phase 2a/2b path-traversal hardening + tests (small, security).
3. **PR 3:** Phase 2c storage abstraction incl. `s3://`/`local://` (optional).
4. **PR 4:** Phase 5 IGV session XML link-out.
5. **PR 5:** Phase 6 embedded igv.js.

## Risks / gotchas checklist for the implementer

- [ ] `obj.size` returning `None` (backend can't stat) → must fall back to
      full `200`; never emit a `Content-Range` with an unknown total.
- [ ] Don't set `Content-Length` twice / inconsistently on `206`.
- [ ] paramiko per-chunk round-trips can be slow for big ranges — measure;
      add bounded `prefetch(length)` if needed (guard with `hasattr`).
- [ ] `@backoff` on the render generator only retries construction, not
      mid-stream — pre-existing, don't regress.
- [ ] Weak vs strong ETag for `If-Range`; nginx may strip strong ETag.
- [ ] HEAD must not open an SFTP stream.
- [ ] `?access_token=` readonly auth must keep working for HEAD + ranged GET.
- [ ] Suffix range `bytes=-N` and open-ended `bytes=N-` both handled.
- [ ] 416 on unsatisfiable range with `Content-Range: bytes */<size>`.
- [ ] Multi-range header → serve full `200` (documented, not an error).
