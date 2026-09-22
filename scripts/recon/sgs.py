"""SGS reconciliation used in docs/: series names, coverage, and Dec->Jan seasonality.

    uv run python scripts/recon/sgs.py

1. Prints the official English name, unit and source of each SGS series cited in docs/, read
   from the SGS web-service metadata (so no series code is quoted from memory).
2. Prints first/last observation for each.
3. For the 90-day delinquency series 21082-21084, prints every December->January change since
   2012 and the distribution of month-on-month moves: the seasonal baseline against which the
   January-2025 step is judged in docs/data-landscape.md.
"""

from __future__ import annotations

import json
import re
import subprocess

UA = "brazil-consumer-credit-risk/0.1 (public research)"
SERIES = [
    432,
    4189,
    1619,
    433,
    13522,
    24369,
    20539,
    20540,
    20541,
    20631,
    20632,
    20633,
    20714,
    20716,
    20783,
    20785,
    21082,
    21083,
    21084,
    21085,
    21086,
    21112,
    21113,
    21129,
    21114,
    20575,
    29034,
    29035,
    29037,
    29038,
]


def curl(url: str) -> str:
    for _ in range(4):
        r = subprocess.run(
            ["curl", "-sS", "--http1.1", "-m", "90", "-A", UA, url], capture_output=True, text=True
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout
    raise RuntimeError(f"failed: {url}")


def metadata(code: int) -> dict[str, str]:
    xml = curl(
        "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
        f"?method=getUltimoValorVO&codigoSerie={code}"
    )
    out = {}
    for tag in ("fullName", "periodicidadeSigla", "unidadePadraoIngles", "fonte"):
        m = re.search(rf"<{tag}[^>]*>([^<]*)<", xml)
        out[tag] = m.group(1) if m else ""
    return out


def values(code: int) -> list[tuple[str, float]]:
    data = json.loads(
        curl(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json")
    )
    return [(f"{d['data'][6:]}-{d['data'][3:5]}", float(d["valor"])) for d in data]


if __name__ == "__main__":
    print("code | freq | unit | source | name | first | last")
    cache = {}
    for code in SERIES:
        md = metadata(code)
        cache[code] = values(code)
        print(
            f"{code} | {md['periodicidadeSigla']} | {md['unidadePadraoIngles']} | {md['fonte']} | "
            f"{md['fullName']} | {cache[code][0][0]} | {cache[code][-1][0]}"
        )

    for code in (21082, 21083, 21084):
        s = dict(cache[code])
        print(f"\nSGS {code}: December -> January changes (pp)")
        for y in range(2012, 2027):
            dec, jan = s.get(f"{y - 1}-12"), s.get(f"{y}-01")
            if dec is not None and jan is not None:
                print(f"  Dec{y - 1}->Jan{y}: {dec:.2f} -> {jan:.2f}  {jan - dec:+.2f}")
        keys = sorted(s)
        mom = sorted(abs(s[keys[i]] - s[keys[i - 1]]) for i in range(1, len(keys)))
        n = len(mom)
        print(
            f"  |month-on-month| p50 {mom[n // 2]:.2f}  p90 {mom[int(n * 0.9)]:.2f}  "
            f"p99 {mom[int(n * 0.99)]:.2f}  max {mom[-1]:.2f}"
        )

    mw = dict(cache[1619])
    print(
        "\nMinimum wage (SGS 1619), January values:",
        {y: mw.get(f"{y}-01") for y in (2012, 2013, 2016, 2024, 2025, 2026)},
    )
