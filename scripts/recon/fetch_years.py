"""Download SCR.data yearly archives in 4 MB range requests, resumably, and verify them.

    uv run python scripts/recon/fetch_years.py data/raw/zips scrdata 2012 2026 --jobs 3

For each year:
  1. HEAD for size and Last-Modified (the publication vintage).
  2. Fetch missing byte ranges into <name>.zip.part. Bytes already on disk are kept, so an
     interrupted run resumes where it stopped. The host resets long transfers, so each range
     is small and retried with backoff.
  3. Verify before accepting: every member is named <prefix>_YYYYMM.csv, uses deflate or no
     compression, is < 2 GB uncompressed, and passes a CRC32 check (zipfile.testzip). Failure
     deletes the file.
  4. Append size, Last-Modified, SHA-256, member count and month range to MANIFEST.tsv.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://www.bcb.gov.br/pda/desig"
UA = "brazil-consumer-credit-risk/0.1 (public research)"
STEP = 4 << 20
MEMBER = re.compile(r"(planilha|scrdata)_(\d{6})\.csv")


def log(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {msg}", flush=True)


def curl(args: list[str], attempts: int = 8) -> bytes:
    for i in range(attempts):
        r = subprocess.run(
            [
                "curl",
                "-sSL",
                "--fail",
                "--http1.1",
                "--proto",
                "=https",
                "-m",
                "180",
                "-A",
                UA,
                *args,
            ],
            capture_output=True,
        )
        if r.returncode == 0:
            return r.stdout
        time.sleep(min(2**i, 60))
    raise OSError(
        f"curl failed after {attempts} attempts: {args[-1]} ({r.stderr.decode().strip()})"
    )


def head(url: str) -> tuple[int, str]:
    text = curl(["-I", url]).decode()
    size = modified = None
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key.lower() == "content-length":
            size = int(value.strip())
        elif key.lower() == "last-modified":
            modified = value.strip()
    if size is None:
        raise OSError(f"no content-length for {url}")
    return size, modified or ""


def verify(path: Path, prefix: str) -> tuple[int, str, str]:
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        months = []
        for i in infos:
            m = MEMBER.fullmatch(i.filename)
            if not m or m.group(1) != prefix:
                raise ValueError(f"unexpected member {i.filename!r}")
            if i.compress_type not in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
                raise ValueError(f"unexpected compression in {i.filename}")
            if i.file_size > 2_000_000_000:
                raise ValueError(f"member too large: {i.filename}")
            months.append(m.group(2))
        bad = z.testzip()
        if bad is not None:
            raise ValueError(f"CRC failure in {bad}")
    return len(infos), min(months), max(months)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(out: Path, prefix: str, year: int) -> str:
    name = f"{prefix}_{year}.zip"
    url = f"{BASE}/{name}"
    dest, part = out / name, out / f"{name}.part"
    size, modified = head(url)
    if dest.exists() and dest.stat().st_size == size:
        return f"= {name} already complete"
    have = part.stat().st_size if part.exists() else 0
    if have > size:
        part.unlink()
        have = 0
    log(
        f"start {name}: {size / 1e6:.1f} MB, resuming at {have / 1e6:.1f} MB, Last-Modified {modified}"
    )
    last_report = have
    with part.open("ab") as fh:
        while have < size:
            hi = min(have + STEP, size) - 1
            chunk = curl(["-r", f"{have}-{hi}", url])
            if len(chunk) != hi - have + 1:
                continue  # short read: retry the same range
            fh.write(chunk)
            fh.flush()
            have += len(chunk)
            if have - last_report >= 40 << 20:
                log(f"  {name} {have / size:6.1%}")
                last_report = have
    part.rename(dest)
    try:
        members, first, last = verify(dest, prefix)
    except Exception:
        dest.unlink()
        raise
    digest = sha256(dest)
    row = [
        name,
        str(size),
        modified,
        digest,
        str(members),
        first,
        last,
        datetime.now(UTC).isoformat(),
    ]
    with (out / "MANIFEST.tsv").open("a") as fh:
        fh.write("\t".join(row) + "\n")
    return f"ok {name} {size / 1e6:.1f} MB, {members} months {first}-{last}, CRC ok, sha256 {digest[:16]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("prefix", choices=["scrdata", "planilha"])
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = args.out / "MANIFEST.tsv"
    if not manifest.exists():
        manifest.write_text(
            "file\tbytes\tlast_modified\tsha256\tmembers\tfirst_month\tlast_month\tdownloaded_utc\n"
        )

    failures = 0

    def run(year: int) -> None:
        nonlocal failures
        try:
            log(fetch(args.out, args.prefix, year))
        except Exception as exc:  # noqa: BLE001 (report and continue with the other years)
            failures += 1
            log(f"FAILED {args.prefix}_{year}: {exc}")

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        list(ex.map(run, range(args.last, args.first - 1, -1)))
    log(f"DONE failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
