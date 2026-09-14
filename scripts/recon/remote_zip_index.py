"""Read the central directory of every yearly SCR.data archive via HTTP Range requests.

Gives member names and compressed/uncompressed sizes for the full history without
downloading ~6 GB. Uses curl for transport (system Python lacks a CA bundle here).
"""

import json
import struct
import subprocess
from pathlib import Path

BASE = "https://www.bcb.gov.br/pda/desig"
UA = "br-credit-monitor/0.1 (public research)"


def fetch(url: str, rng: str) -> bytes:
    return subprocess.run(
        ["curl", "-sSL", "--fail", "-m", "120", "-A", UA, "-r", rng, url],
        check=True,
        capture_output=True,
    ).stdout


def size_of(url: str) -> int:
    out = subprocess.run(
        ["curl", "-sSIL", "-m", "60", "-A", UA, url], check=True, capture_output=True, text=True
    ).stdout
    lens = [
        line.split(":", 1)[1].strip()
        for line in out.splitlines()
        if line.lower().startswith("content-length")
    ]
    return int(lens[-1])


def members(url: str) -> list[dict]:
    total = size_of(url)
    tail = fetch(url, f"{max(total - 65536, 0)}-{total - 1}")
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("no EOCD in tail")
    _, _, _, _, n, cd_size, cd_off, _ = struct.unpack("<IHHHHIIH", tail[eocd : eocd + 22])
    if cd_off == 0xFFFFFFFF or n == 0xFFFF:  # zip64
        loc = tail.rfind(b"PK\x06\x07")
        (z64_off,) = struct.unpack("<Q", tail[loc + 8 : loc + 16])
        z64 = fetch(url, f"{z64_off}-{z64_off + 55}")
        n, cd_size, cd_off = struct.unpack("<QQQ", z64[32:56])
    cd = fetch(url, f"{cd_off}-{cd_off + cd_size - 1}")
    out, p = [], 0
    for _ in range(n):
        (sig, _, _, _, method, _, _, _, csize, usize, fnlen, exlen, cmlen) = struct.unpack(
            "<IHHHHHHIIIHHH", cd[p : p + 34]
        )
        assert sig == 0x02014B50, hex(sig)
        name = cd[p + 46 : p + 46 + fnlen].decode("cp437")
        extra = cd[p + 46 + fnlen : p + 46 + fnlen + exlen]
        if usize == 0xFFFFFFFF or csize == 0xFFFFFFFF:
            q = 0
            while q < len(extra):
                hid, hlen = struct.unpack("<HH", extra[q : q + 4])
                if hid == 1:
                    vals = struct.unpack("<" + "Q" * (hlen // 8), extra[q + 4 : q + 4 + hlen])
                    vi = 0
                    if usize == 0xFFFFFFFF:
                        usize = vals[vi]
                        vi += 1
                    if csize == 0xFFFFFFFF:
                        csize = vals[vi]
                q += 4 + hlen
        out.append({"name": name, "method": method, "csize": csize, "usize": usize})
        p += 46 + fnlen + exlen + cmlen
    return out


if __name__ == "__main__":
    result = {}
    for year in range(2012, 2027):
        for prefix in ("planilha", "scrdata"):
            key = f"{prefix}_{year}"
            try:
                result[key] = members(f"{BASE}/{key}.zip")
            except Exception as exc:  # noqa: BLE001
                result[key] = {"error": str(exc)}
            ms = result[key]
            if isinstance(ms, dict):
                print(key, "ERROR", ms["error"])
                continue
            c = sum(m["csize"] for m in ms) / 1e6
            u = sum(m["usize"] for m in ms) / 1e6
            print(f"{key}: {len(ms)} members, {c:,.0f} MB zipped, {u:,.0f} MB raw")
            for m in ms:
                print(f"    {m['name']:55} {m['csize'] / 1e6:7.1f} -> {m['usize'] / 1e6:8.1f} MB")
    Path("data/recon").mkdir(parents=True, exist_ok=True)
    with open("data/recon/remote_zip_index.json", "w") as fh:
        json.dump(result, fh, indent=1)
