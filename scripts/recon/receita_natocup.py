"""Receita Federal IRPF filers by *natureza da ocupação*, by calendar year (2008-2020).

    uv run python scripts/recon/receita_natocup.py

Source: Receita Federal open data, "Natureza de Ocupação.csv"
(`gov.br/receitafederal/dados/natureza-de-ocupacao.csv`). Prints filers (thousands) per category
per ano-calendário, which shows when categories such as "Não informado" and the "Adaptação: ..."
codes disappear. Used in docs/data-dictionary.md section 10.4 as the lead on the January-2016 and
January-2017 SCR.data occupation reclassifications.
"""

import csv
import io
import subprocess

URL = "https://www.gov.br/receitafederal/dados/natureza-de-ocupacao.csv"
UA = "brazil-consumer-credit-risk/0.1 (public research)"

raw = subprocess.run(
    ["curl", "-sSL", "--fail", "--http1.1", "--proto", "=https", "-m", "180", "-A", UA, URL],
    check=True,
    capture_output=True,
).stdout
rows = [r for r in csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")][1:]

by_year: dict[str, dict[str, int]] = {}
for r in rows:
    if r:
        by_year.setdefault(r[0], {})[r[1]] = int(r[2])
years = sorted(by_year)
categories = sorted({c for y in years for c in by_year[y]})

print("filers (thousands) by ano-calendário; '-' = category absent that year")
print(f"{'natureza da ocupação':<62}", " ".join(f"{y:>6}" for y in years))
for c in categories:
    cells = " ".join(f"{by_year[y][c] / 1000:6.0f}" if c in by_year[y] else "     -" for y in years)
    print(f"{c[:62]:<62}", cells)
totals = {y: sum(by_year[y].values()) for y in years}
print(f"{'TOTAL (millions)':<62}", " ".join(f"{totals[y] / 1e6:6.1f}" for y in years))
share = {y: by_year[y].get("Não informado", 0) / totals[y] for y in years}
print(f"{'share Não informado':<62}", " ".join(f"{100 * share[y]:5.1f}%" for y in years))
