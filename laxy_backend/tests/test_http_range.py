import io
import unittest
from unittest import TestCase

from ..http_range import parse_range_header, InvalidRange, RangeFileWrapper


class ParseRangeHeaderTest(TestCase):
    """
    Table-driven tests for parse_range_header, covering closed ranges,
    open-ended ranges, suffix ranges, clamping, and the various
    None/InvalidRange fall-back cases described in the HTTP Range plan.
    """

    SIZE = 1000

    # (range_header, expected_result_or_exception)
    CASES = [
        ("bytes=0-499", (0, 499)),
        ("bytes=500-", (500, 999)),
        ("bytes=-500", (500, 999)),
        ("bytes=0-0", (0, 0)),
        ("bytes=-0", InvalidRange),
        ("bytes=1000-", InvalidRange),  # start beyond EOF (size == 1000)
        ("bytes=999-", (999, 999)),  # last valid single byte
        ("bytes=0-99999", (0, 999)),  # last clamped to size - 1
        ("", None),
        (None, None),
        ("bytes=0-9,20-29", None),  # multi-range -> not attempted
        ("bytes=abc-def", None),  # malformed
        ("not a range header", None),  # malformed
        ("bytes=", None),
    ]

    def test_cases(self):
        for range_header, expected in self.CASES:
            with self.subTest(range_header=range_header):
                if expected is InvalidRange:
                    with self.assertRaises(InvalidRange):
                        parse_range_header(range_header, self.SIZE)
                else:
                    self.assertEqual(
                        parse_range_header(range_header, self.SIZE), expected
                    )

    def test_zero_size_file(self):
        # Any syntactically valid range against an empty file is unsatisfiable.
        with self.assertRaises(InvalidRange):
            parse_range_header("bytes=0-10", 0)

    def test_zero_size_file_no_range_header(self):
        # No Range header at all -> None regardless of size.
        self.assertIsNone(parse_range_header(None, 0))
        self.assertIsNone(parse_range_header("", 0))

    def test_suffix_range_larger_than_file(self):
        # bytes=-N where N > size -> clamp to the whole file.
        self.assertEqual(parse_range_header("bytes=-5000", self.SIZE), (0, 999))

    def test_start_after_end_is_invalid(self):
        with self.assertRaises(InvalidRange):
            parse_range_header("bytes=500-100", self.SIZE)

    def test_case_insensitive(self):
        self.assertEqual(parse_range_header("Bytes=0-9", self.SIZE), (0, 9))


class RangeFileWrapperTest(TestCase):
    def setUp(self):
        self.data = bytes(range(256)) * 4  # 1024 bytes, easy to verify by content
        self.size = len(self.data)

    def test_exact_byte_window(self):
        f = io.BytesIO(self.data)
        wrapper = RangeFileWrapper(f, offset=10, length=20)
        result = b"".join(chunk for chunk in wrapper)
        self.assertEqual(result, self.data[10:30])

    def test_chunking_respects_blksize(self):
        f = io.BytesIO(self.data)
        wrapper = RangeFileWrapper(f, offset=0, length=100, blksize=16)
        chunks = list(wrapper)
        self.assertEqual(b"".join(chunks), self.data[:100])
        # All but possibly the last chunk should be exactly blksize bytes.
        for chunk in chunks[:-1]:
            self.assertEqual(len(chunk), 16)
        self.assertLessEqual(len(chunks[-1]), 16)

    def test_length_none_reads_to_eof(self):
        f = io.BytesIO(self.data)
        wrapper = RangeFileWrapper(f, offset=500, length=None, blksize=64)
        result = b"".join(chunk for chunk in wrapper)
        self.assertEqual(result, self.data[500:])

    def test_offset_zero_length_zero(self):
        f = io.BytesIO(self.data)
        wrapper = RangeFileWrapper(f, offset=0, length=0)
        result = b"".join(chunk for chunk in wrapper)
        self.assertEqual(result, b"")

    def test_close_delegates_to_filelike(self):
        f = io.BytesIO(self.data)
        wrapper = RangeFileWrapper(f, offset=0, length=10)
        wrapper.close()
        self.assertTrue(f.closed)


class _LazyOpenFile:
    """
    Mimics django-storages' SFTPStorageFile: the real backing data is only
    opened on the first read(); until then it proxies an empty placeholder
    buffer. A seek() before that first read therefore hits the placeholder
    and is lost -- exactly the behaviour that made ranged SFTP downloads
    stream from byte 0 in the wild. RangeFileWrapper must prime the lazy
    open before seeking to work against this.
    """

    def __init__(self, data: bytes):
        self._data = data
        self._file = io.BytesIO()  # empty placeholder, like SFTPStorageFile
        self._is_read = False

    def read(self, num_bytes=-1):
        if not self._is_read:
            self._file = io.BytesIO(self._data)
            self._is_read = True
        return self._file.read(num_bytes)

    def seek(self, *args, **kwargs):
        return self._file.seek(*args, **kwargs)

    def tell(self):
        return self._file.tell()

    def close(self):
        self._file.close()


class RangeFileWrapperLazyOpenTest(TestCase):
    """
    Regression test for the SFTPStorageFile lazy-open seek bug: a naive
    seek()-before-read() streams from byte 0 for every range. Found via a
    live ranged BAM download; the io.BytesIO-based tests above can't catch
    it because BytesIO opens eagerly.
    """

    def setUp(self):
        self.data = bytes(range(256)) * 400  # 102400 bytes

    def test_mid_file_range_against_lazy_open_file(self):
        wrapper = RangeFileWrapper(
            _LazyOpenFile(self.data), offset=1000, length=256, blksize=64
        )
        result = b"".join(wrapper)
        self.assertEqual(result, self.data[1000:1256])

    def test_suffix_style_offset_against_lazy_open_file(self):
        offset = len(self.data) - 100
        wrapper = RangeFileWrapper(
            _LazyOpenFile(self.data), offset=offset, length=100
        )
        result = b"".join(wrapper)
        self.assertEqual(result, self.data[offset:])

    def test_offset_zero_against_lazy_open_file(self):
        wrapper = RangeFileWrapper(
            _LazyOpenFile(self.data), offset=0, length=50
        )
        self.assertEqual(b"".join(wrapper), self.data[:50])


if __name__ == "__main__":
    unittest.main()
