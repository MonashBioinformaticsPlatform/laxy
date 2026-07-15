import re
from typing import Optional, Tuple

# Single-range only (we deliberately don't support multipart/byteranges).
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$", re.IGNORECASE)


class InvalidRange(Exception):
    """Range header present but unsatisfiable -> caller should return 416."""


def parse_range_header(range_header: Optional[str], size: int) -> Optional[Tuple[int, int]]:
    """
    Parse a single-range 'Range: bytes=...' header against a known total size.

    Returns (first_byte, last_byte) inclusive, or None if there is no usable
    range header (caller should serve full 200). Raises InvalidRange for a
    syntactically valid but unsatisfiable range (caller returns 416).

    Handles:
      bytes=0-499      -> (0, 499)
      bytes=500-       -> (500, size-1)
      bytes=-500       -> suffix: last 500 bytes -> (size-500, size-1)

    Multi-range (comma separated) is treated as "no usable single range"
    -> None (fall back to full 200) to keep things simple and correct; a
    server MAY ignore a Range header per RFC 7233.
    """
    if not range_header:
        return None
    if "," in range_header:
        return None
    m = _RANGE_RE.match(range_header.strip())
    if not m:
        return None
    start_s, end_s = m.group(1), m.group(2)

    if start_s == "" and end_s == "":
        return None
    if size == 0:
        raise InvalidRange("empty file")

    if start_s == "":  # suffix range: bytes=-N
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

    def __init__(
        self,
        filelike,
        offset: int = 0,
        length: Optional[int] = None,
        blksize: int = 8192,
    ):
        self.filelike = filelike
        self.remaining = length
        self.blksize = blksize
        self._seek_to(offset)

    def _seek_to(self, offset: int):
        # Some storage wrappers open their real backing file lazily on the
        # first read() -- notably django-storages' SFTPStorageFile, which
        # proxies an empty in-memory io.BytesIO() until then. A seek before
        # that first read is silently applied to the placeholder buffer and
        # lost, so every range would stream from byte 0. Force the lazy open
        # with a zero-length read, then seek the now-real underlying file.
        try:
            if offset:
                self.filelike.read(0)
            self.filelike.seek(offset)
        except (AttributeError, OSError, ValueError):
            # Non-seekable backend (eg requests' raw HTTP response): fall back
            # to reading and discarding up to the offset (correct but slow).
            # Callers should check File.supports_range before serving a range,
            # so this path is only a safety net.
            self._discard(offset)

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
        read_size = (
            self.blksize if self.remaining is None else min(self.remaining, self.blksize)
        )
        data = self.filelike.read(read_size)
        if not data:
            raise StopIteration()
        if self.remaining is not None:
            self.remaining -= len(data)
        return data
