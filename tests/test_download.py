import pytest
import requests

from brazil_consumer_credit_risk.download import RemoteFile, byte_ranges, download, get_range


class FakeResponse:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content


class FakeSession:
    """Serves byte ranges of `data`; the first requests fail in the ways listed in `faults`."""

    def __init__(self, data: bytes, faults: list[str] | None = None):
        self.data = data
        self.faults = list(faults or [])
        self.requests: list[tuple[int, int]] = []

    def get(self, url, headers, timeout):
        first, last = map(int, headers["Range"].removeprefix("bytes=").split("-"))
        self.requests.append((first, last))
        fault = self.faults.pop(0) if self.faults else None
        if fault == "reset":
            raise requests.ConnectionError("connection reset by peer")
        if fault == "short":
            return FakeResponse(206, self.data[first:last])
        if fault == "full":
            return FakeResponse(200, self.data)
        return FakeResponse(206, self.data[first : last + 1])


def no_sleep(_seconds: float) -> None:
    pass


def test_byte_ranges_cover_the_file_exactly():
    assert byte_ranges(0, 10, step=4) == [(0, 3), (4, 7), (8, 9)]
    assert byte_ranges(8, 10, step=4) == [(8, 9)]
    assert byte_ranges(10, 10, step=4) == []


def test_get_range_retries_resets_short_reads_and_ignored_ranges():
    data = bytes(range(100))
    session = FakeSession(data, faults=["reset", "short", "full"])
    assert get_range(session, "u", 10, 19, sleep=no_sleep) == data[10:20]
    assert len(session.requests) == 4


def test_get_range_gives_up_after_the_last_attempt():
    session = FakeSession(b"x" * 10, faults=["reset"] * 3)
    with pytest.raises(OSError, match="failed after 3 attempts"):
        get_range(session, "u", 0, 9, attempts=3, sleep=no_sleep)


def test_download_resumes_from_a_partial_file(tmp_path):
    data = bytes(range(256)) * 4
    dest = tmp_path / "scrdata_2024.zip"
    (tmp_path / "scrdata_2024.zip.part").write_bytes(data[:300])
    session = FakeSession(data)

    download(session, RemoteFile("u", len(data), ""), dest, step=256, sleep=no_sleep)

    assert dest.read_bytes() == data
    assert session.requests[0] == (300, 555)
    assert not (tmp_path / "scrdata_2024.zip.part").exists()


def test_download_starts_over_when_the_partial_file_is_longer_than_the_remote(tmp_path):
    data = b"abcdefghij"
    dest = tmp_path / "f.zip"
    (tmp_path / "f.zip.part").write_bytes(b"z" * 50)
    session = FakeSession(data)

    download(session, RemoteFile("u", len(data), ""), dest, step=4, sleep=no_sleep)

    assert dest.read_bytes() == data
    assert session.requests[0] == (0, 3)
