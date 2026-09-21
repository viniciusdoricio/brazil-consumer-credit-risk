"""Discover and download BCB SCR.data monthly archives.

The BCB open-data portal is a CKAN instance, so resources are discoverable
through the CKAN action API rather than by guessing URL patterns. This script
asks the portal what exists and downloads what you ask for.

    # A three-month sample rather than the whole history.
    uv run python scripts/fetch_scr.py --recon

    # List what the portal actually offers, without downloading
    uv run python scripts/fetch_scr.py --list

    # Specific months
    uv run python scripts/fetch_scr.py --months 2013-06 2024-06 2026-07

FIRST-RUN CHECK: not yet verified against the live portal
----------------------------------------------------------
The CKAN endpoint below is the documented shape for this portal type but has
not been confirmed against dadosabertos.bcb.gov.br. On the first run:

  1. `--list` and confirm resources come back with usable URLs.
  2. If the API shape differs, fix `discover_resources()`; do not paper over
     it with hardcoded URLs, because they rot and the next person can't tell.
  3. If there is genuinely no API, document the manual download procedure in
     data/README.md and make this script consume a local directory instead.

Record whatever you find in docs/data-dictionary.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

PORTAL = "https://dadosabertos.bcb.gov.br"
CKAN_PACKAGE = f"{PORTAL}/api/3/action/package_show"
DATASET_ID = "scr_data"

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
TIMEOUT = 60
CHUNK = 1 << 20

# The reconnaissance deliberately samples the series rather than
# pulling fourteen years: one early month, one before the Res. 4.966 break,
# one after it. Three files answer the schema-drift and cross-tab questions.
RECON_MONTHS = ("2013-06", "2024-06")


@dataclass(frozen=True)
class Resource:
    name: str
    url: str
    fmt: str
    period: str | None  # YYYY-MM parsed from the name, when present

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1] or f"{self.name}.zip"


def _period_from(text: str) -> str | None:
    """Pull a YYYY-MM out of a resource name or URL, if one is there."""
    if m := re.search(r"(20\d{2})[-_/]?(0[1-9]|1[0-2])", text):
        return f"{m.group(1)}-{m.group(2)}"
    return None


def discover_resources(session: requests.Session) -> list[Resource]:
    """Ask the portal what it has. See FIRST-RUN CHECK in the module docstring."""
    resp = session.get(CKAN_PACKAGE, params={"id": DATASET_ID}, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    if not payload.get("success"):
        raise RuntimeError(f"CKAN returned success=false for {DATASET_ID!r}")

    out: list[Resource] = []
    for item in payload["result"].get("resources", []):
        url = item.get("url") or ""
        name = item.get("name") or ""
        if not url:
            continue
        out.append(
            Resource(
                name=name,
                url=url,
                fmt=(item.get("format") or "").upper(),
                period=_period_from(name) or _period_from(url),
            )
        )
    return out


def download(session: requests.Session, res: Resource, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / res.filename

    if dest.exists() and dest.stat().st_size > 0:
        print(f"  = {dest.name} (already present, skipping)")
        return dest

    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(res.url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        seen = 0
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(CHUNK):
                fh.write(chunk)
                seen += len(chunk)
                if total:
                    print(f"\r  ↓ {dest.name} {seen / total:6.1%}", end="", flush=True)
    tmp.rename(dest)
    print(f"\r  ✓ {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="show available resources, download nothing")
    g.add_argument(
        "--recon", action="store_true", help="fetch the reconnaissance sample (3 months)"
    )
    g.add_argument("--months", nargs="+", metavar="YYYY-MM", help="fetch specific months")
    g.add_argument("--all", action="store_true", help="fetch the full history (large)")
    ap.add_argument("--out", type=Path, default=RAW, help="destination directory")
    args = ap.parse_args()

    session = requests.Session()
    session.headers["User-Agent"] = "brazil-consumer-credit-risk/0.1 (public research)"

    try:
        resources = discover_resources(session)
    except Exception as exc:  # noqa: BLE001 (surface the real cause to the operator)
        print(f"discovery failed: {exc}\n", file=sys.stderr)
        print(
            "See FIRST-RUN CHECK in this file's docstring before working around it.",
            file=sys.stderr,
        )
        return 2

    archives = [r for r in resources if r.fmt in {"ZIP", "CSV", "CSV.ZIP"}]
    print(f"{len(resources)} resources, {len(archives)} archives\n")

    if args.list:
        for r in sorted(resources, key=lambda x: (x.period or "", x.name)):
            print(f"  {r.period or '    -  '}  {r.fmt:8}  {r.name[:70]}")
        print("\nIf periods are all '-', the naming doesn't encode YYYY-MM; fix _period_from().")
        return 0

    if args.all:
        wanted = archives
    else:
        months = set(RECON_MONTHS if args.recon else args.months)
        if args.recon:
            latest = max((r.period for r in archives if r.period), default=None)
            if latest:
                months.add(latest)
                print(f"recon sample: {sorted(months)}  (latest detected: {latest})\n")
        wanted = [r for r in archives if r.period in months]

    if not wanted:
        print("nothing matched. Run --list to see what the portal offers.", file=sys.stderr)
        return 1

    for res in sorted(wanted, key=lambda x: x.period or ""):
        download(session, res, args.out)

    print(f"\n{len(wanted)} file(s) in {args.out}")
    print("Next: profile them in DuckDB. Answer the cross-tab question before anything else.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
