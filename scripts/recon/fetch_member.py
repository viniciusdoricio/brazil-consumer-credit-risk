"""Fetch a single monthly CSV out of a yearly BCB archive using HTTP Range requests.

    uv run python scripts/recon/fetch_member.py OUT_DIR scrdata_202607 planilha_201306 ...

Integrity: the member is inflated in memory and checked against the CRC32 and uncompressed
size in the archive's central directory before anything is written; a SHA-256 of the
written CSV goes to OUT_DIR/SHA256SUMS. Names are validated against a strict pattern so a
hostile archive could not write outside OUT_DIR. Transport is curl over HTTPS (certificate
verification on).
"""

import hashlib
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

BASE = "https://www.bcb.gov.br/pda/desig"
UA = "brazil-consumer-credit-risk/0.1 (public research)"
NAME = re.compile(r"(planilha|scrdata)_(\d{4})(\d{2})")


def curl(args: list[str]) -> bytes:
    last = None
    for _ in range(4):
        try:
            return subprocess.run(
                [
                    "curl",
                    "-sSL",
                    "--fail",
                    "--http1.1",
                    "--proto",
                    "=https",
                    "-m",
                    "1800",
                    "-A",
                    UA,
                    *args,
                ],
                check=True,
                capture_output=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            last = exc
    raise last


def central_directory(url: str) -> dict[str, dict]:
    head = curl(["-I", url]).decode()
    total = int(
        [
            ln.split(":", 1)[1]
            for ln in head.splitlines()
            if ln.lower().startswith("content-length")
        ][-1]
    )
    tail = curl(["-r", f"{max(total - 65536, 0)}-{total - 1}", url])
    e = tail.rfind(b"PK\x05\x06")
    _, _, _, _, n, cd_size, cd_off, _ = struct.unpack("<IHHHHIIH", tail[e : e + 22])
    cd = curl(["-r", f"{cd_off}-{cd_off + cd_size - 1}", url])
    out, p = {}, 0
    for _ in range(n):
        (sig, _, _, flags, method, _, _, crc, csize, usize, fnlen, exlen, cmlen, _, _, _, off) = (
            struct.unpack("<IHHHHHHIIIHHHHHII", cd[p : p + 46])
        )
        assert sig == 0x02014B50
        name = cd[p + 46 : p + 46 + fnlen].decode("cp437")
        out[name] = dict(method=method, crc=crc, csize=csize, usize=usize, off=off, flags=flags)
        p += 46 + fnlen + exlen + cmlen
    return out, total


def fetch(out_dir: Path, stem: str) -> None:
    m = NAME.fullmatch(stem)
    if not m:
        raise ValueError(f"refusing unexpected member name {stem!r}")
    prefix, year = m.group(1), m.group(2)
    url = f"{BASE}/{prefix}_{year}.zip"
    cd, _ = central_directory(url)
    info = cd[f"{stem}.csv"]
    if info["usize"] > 2_000_000_000 or info["method"] != 8:
        raise ValueError(f"unexpected member metadata {info}")
    # local header is 30 bytes + variable name/extra; read generously then parse
    lh = curl(["-r", f"{info['off']}-{info['off'] + 29}", url])
    assert lh[:4] == b"PK\x03\x04"
    fnlen, exlen = struct.unpack("<HH", lh[26:30])
    start = info["off"] + 30 + fnlen + exlen
    # fetch in 4 MB ranges: long single transfers from this host get reset mid-stream
    step, parts = 4 << 20, []
    for lo in range(start, start + info["csize"], step):
        hi = min(lo + step, start + info["csize"]) - 1
        parts.append(curl(["-r", f"{lo}-{hi}", url]))
    comp = b"".join(parts)
    if len(comp) != info["csize"]:
        raise OSError(f"short read {len(comp)} != {info['csize']}")
    data = zlib.decompressobj(-15).decompress(comp)
    if len(data) != info["usize"] or zlib.crc32(data) != info["crc"]:
        raise OSError(f"{stem}: CRC/size mismatch, discarding")
    dest = out_dir / f"{stem}.csv"
    dest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    with (out_dir / "SHA256SUMS").open("a") as fh:
        fh.write(f"{digest}  {dest.name}\n")
    print(
        f"ok {stem} {len(comp) / 1e6:.1f}MB->{len(data) / 1e6:.1f}MB crc-ok sha256={digest[:16]}",
        flush=True,
    )


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[2:]:
        try:
            fetch(out, s)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {s}: {exc}", flush=True)
