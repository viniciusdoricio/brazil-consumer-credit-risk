"""Read the header line and first data row of EVERY monthly member, V1 and V2, 2012-2026.

Uses tiny HTTP range reads (a few KB per member) and partial inflation, so the whole-history
schema can be diffed without downloading 6 GB. Prints each point where the header changes and
writes header_scan.json with the first two lines of every month.
"""

import json
import struct
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetch_member import BASE, central_directory, curl


def first_lines(url: str, name: str, info: dict) -> tuple[str, str, str]:
    lh = curl(["-r", f"{info['off']}-{info['off'] + 29}", url])
    fnlen, exlen = struct.unpack("<HH", lh[26:30])
    start = info["off"] + 30 + fnlen + exlen
    chunk = curl(["-r", f"{start}-{start + 6000}", url])
    text = zlib.decompressobj(-15).decompress(chunk)
    lines = text.split(b"\n")
    enc = "utf-8"
    try:
        lines[0].decode("utf-8")
    except UnicodeDecodeError:
        enc = "latin-1"
    return (lines[0].decode(enc).strip("\r"), lines[1].decode(enc, "replace").strip("\r"), enc)


def scan_year(prefix: str, year: int) -> dict:
    url = f"{BASE}/{prefix}_{year}.zip"
    cd, _ = central_directory(url)
    out = {}
    for name, info in sorted(cd.items()):
        header, row, enc = first_lines(url, name, info)
        out[name[:-4]] = {
            "header": header,
            "row1": row,
            "encoding": enc,
            "bom": header.startswith("﻿"),
        }
    return out


jobs = [(p, y) for p in ("planilha", "scrdata") for y in range(2012, 2027)]
with ThreadPoolExecutor(max_workers=3) as ex:
    parts = list(ex.map(lambda j: scan_year(*j), jobs))
result = {k: v for part in parts for k, v in part.items()}
Path("data/recon").mkdir(parents=True, exist_ok=True)
with open("data/recon/header_scan.json", "w") as fh:
    json.dump(result, fh, indent=1, ensure_ascii=False)

for prefix in ("planilha", "scrdata"):
    prev = None
    months = sorted(k for k in result if k.startswith(prefix))
    print(f"\n==== {prefix}: {months[0]} .. {months[-1]} ({len(months)} months)")
    for m in months:
        r = result[m]
        h = r["header"].lstrip("﻿")
        sig = (h, r["encoding"], r["bom"])
        if sig != prev:
            cols = h.split(";")
            print(f"\n  {m}: encoding={r['encoding']} bom={r['bom']} {len(cols)} cols")
            if prev is None:
                print("    columns:", cols)
            else:
                old = prev[0].split(";")
                print("    added:  ", [c for c in cols if c not in old])
                print("    removed:", [c for c in old if c not in cols])
                if [c for c in cols if c in old] != [c for c in old if c in cols]:
                    print("    (order of common columns changed)")
            print("    row1:", r["row1"][:400])
            prev = sig
