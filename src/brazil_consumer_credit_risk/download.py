"""HTTPS downloads from BCB hosts, in byte ranges small enough to survive dropped connections.

BCB's file host resets long transfers, so a year's archive is fetched as a series of 4 MB range
requests into a ``.part`` file. Each range is retried with backoff, and the bytes already on disk
are kept, so an interrupted download resumes where it stopped.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

USER_AGENT = "brazil-consumer-credit-risk/0.1 (public research)"
TIMEOUT = 180
STEP = 4 << 20

Sleep = Callable[[float], None]


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


@dataclass(frozen=True)
class RemoteFile:
    url: str
    size: int
    last_modified: str


def head(session: requests.Session, url: str) -> RemoteFile:
    """Size and Last-Modified date of a remote file. HTTP errors raise requests.HTTPError."""
    response = session.head(url, allow_redirects=True, timeout=TIMEOUT)
    response.raise_for_status()
    length = response.headers.get("Content-Length")
    if length is None:
        raise OSError(f"{url}: no Content-Length")
    return RemoteFile(url, int(length), response.headers.get("Last-Modified", ""))


def byte_ranges(start: int, size: int, step: int = STEP) -> list[tuple[int, int]]:
    """Inclusive (first, last) byte ranges covering bytes start to size - 1."""
    return [(first, min(first + step, size) - 1) for first in range(start, size, step)]


def get_range(
    session: requests.Session,
    url: str,
    first: int,
    last: int,
    attempts: int = 8,
    sleep: Sleep = time.sleep,
) -> bytes:
    """One byte range, retried with exponential backoff until it arrives complete."""
    expected = last - first + 1
    problem = ""
    for attempt in range(attempts):
        try:
            response = session.get(url, headers={"Range": f"bytes={first}-{last}"}, timeout=TIMEOUT)
            if response.status_code == 206 and len(response.content) == expected:
                return response.content
            problem = f"HTTP {response.status_code}, {len(response.content)} of {expected} bytes"
        except requests.RequestException as exc:
            problem = str(exc)
        if attempt < attempts - 1:
            sleep(min(2**attempt, 60))
    raise OSError(f"{url}: bytes {first}-{last} failed after {attempts} attempts ({problem})")


def download(
    session: requests.Session,
    remote: RemoteFile,
    dest: Path,
    step: int = STEP,
    sleep: Sleep = time.sleep,
) -> None:
    """Fetch a remote file into dest through dest.part, resuming from the bytes already there."""
    part = dest.with_name(dest.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    if have > remote.size:
        part.unlink()
        have = 0
    with part.open("ab") as fh:
        for first, last in byte_ranges(have, remote.size, step):
            fh.write(get_range(session, remote.url, first, last, sleep=sleep))
            fh.flush()
    part.replace(dest)
