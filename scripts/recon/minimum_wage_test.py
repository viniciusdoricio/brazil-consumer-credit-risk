"""Test: do PF income-band shares respond to minimum-wage resets? Use the two mid-year resets.

    uv run python scripts/recon/minimum_wage_test.py data/recon/panel/pf_series.csv

The minimum wage (SGS 1619) changed in January every year, and also in 2020-02 (+0.6%) and
2023-05 (+1.4%). If lenders reclassify bands when it changes, those months should show a small
shift in the January direction (top band down, bottom bands up). Neighbouring months are shown as
controls, alongside the median month-on-month change of each band outside January.
"""

import sys

import duckdb

con = duckdb.connect()
con.execute(
    f"CREATE VIEW p AS SELECT * FROM read_csv('{sys.argv[1]}', header=true) WHERE dim = 'income'"
)
bands = [
    "Acima de 20 salários mínimos",
    "Mais de 10 a 20 salários mínimos",
    "Mais de 1 a 2 salários mínimos",
    "Até 1 salário mínimo",
]
con.execute(
    """CREATE TEMP TABLE d AS SELECT m, value, share_pct - lag(share_pct) OVER (PARTITION BY value ORDER BY m) AS d
       FROM p WHERE value IN ('Acima de 20 salários mínimos', 'Mais de 10 a 20 salários mínimos',
                              'Mais de 1 a 2 salários mínimos', 'Até 1 salário mínimo')"""
)
months = [
    "2019-12",
    "2020-01",
    "2020-02",
    "2020-03",
    "2023-03",
    "2023-04",
    "2023-05",
    "2023-06",
    "2023-07",
]
print(
    "month | "
    + " | ".join(
        b.replace(" salários mínimos", " SM").replace(" salário mínimo", " SM") for b in bands
    )
)
for m in months:
    vals = []
    for b in bands:
        v = con.execute("SELECT d FROM d WHERE m = ? AND value = ?", [m, b]).fetchone()
        vals.append(f"{v[0]:+.3f}" if v and v[0] is not None else "")
    print(f"{m} | " + " | ".join(vals))
print(
    "\nOutside January, 2017-02..2024-12 (months with no minimum-wage change): median and p90 of |change|, pp"
)
for b in bands:
    r = con.execute(
        """SELECT median(d), quantile_cont(abs(d), 0.9) FROM d
           WHERE value = ? AND m BETWEEN '2017-02' AND '2024-12' AND substr(m, 6, 2) <> '01'
             AND m NOT IN ('2020-02', '2023-05', '2019-03', '2018-11', '2021-09', '2020-08')""",
        [b],
    ).fetchone()
    print(f"  {b}: median {r[0]:+.3f}  p90|d| {r[1]:.3f}")
print("\nJanuaries 2017..2024, change in pp")
for b in bands:
    r = con.execute(
        "SELECT list(round(d, 2) ORDER BY m) FROM d WHERE value = ? AND substr(m, 6, 2) = '01' AND m BETWEEN '2017-01' AND '2024-01'",
        [b],
    ).fetchone()
    print(f"  {b}: {r[0]}")
