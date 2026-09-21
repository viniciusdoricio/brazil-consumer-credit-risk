"""What moved in 2025-07? Tests for the broad jump in PF "Acima de 20 salários mínimos".

    uv run python scripts/recon/income_step_2025_07.py data/parquet/scrdata data/recon/panel/pf_series.csv data/raw/months

Each block bears on one hypothesis:
1. New money or reallocation: PF and PJ totals (balance, operations, rows, -1 sentinels).
2. Persistence: every PF income band's share of balance, 2025-01..2026-07.
3. Balance or count: band shares of operations as well as of balance, and balance per operation.
4. A processing change common to other dimensions: PJ size and PF occupation shares around 2025-07.
5. Who moved: 15-90-day and 90-day rates by band before and after.
6. Breadth: share of PF balance in segment x modality x UF x occupation cells whose top-band share
   rose, compared with an ordinary month, a January and the 2026-05 bank event.
7. Where incomes are best known vs least known: band shares within each large sub-modality
   (payroll loans should barely move under a lender-data change; rural should move most if the band
   is now derived from a reported amount that mixes farm revenue with income).
8. Minimum-wage divisor: a changed divisor moves borrowers sitting on a band edge, above all
   retirees on exactly 1 SM ("Até 1" -> "1 a 2"). Band shares within each occupation.
9. PJ breadth: PJ size shares within each lender segment.
10. Cells: PF rows and -1 rows by band.
11. Upstream or V2-only: the same shares in the V1 files (planilha_202506/07.csv, optional third
    argument), which BCB publishes separately.
"""

import sys

import duckdb

src, panel = sys.argv[1], sys.argv[2]
TOP, LOW, ONE_TWO = (
    "Acima de 20 salários mínimos",
    "Até 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos",
)
M0, M1 = "2025-06", "2025-07"
con = duckdb.connect()
cols = [
    r[0]
    for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{src}/scrdata_*.parquet')"
    ).fetchall()
]
occ = next((c for c in cols if "ocup" in c), None)
if occ is None:
    sys.exit(f"no occupation column in {cols}")
con.execute(
    f"""CREATE VIEW s AS SELECT *, strftime(data_base, '%Y-%m') AS m
        FROM read_parquet('{src}/scrdata_*.parquet') WHERE data_base >= DATE '2023-12-01'"""
)


def short(label: str) -> str:
    return label.replace(" salários mínimos", " SM").replace(" salário mínimo", " SM")


def shares_by(dim: str, cliente: str, m_from: str, m_to: str, extra: str = "") -> list[tuple]:
    """Share (%) of each porte within each value of `dim`, one list per (dim value, porte), ordered by month."""
    return con.execute(
        f"""WITH x AS (SELECT {dim} AS k, m, porte, sum(carteira_ativa) AS b FROM s
                       WHERE cliente = '{cliente}' AND m BETWEEN '{m_from}' AND '{m_to}' {extra} GROUP BY ALL),
                 y AS (SELECT k, m, porte, b, 100 * b / sum(b) OVER (PARTITION BY k, m) AS sh FROM x)
            SELECT k, porte, list(round(sh, 2) ORDER BY m), CAST(max(b) FILTER (WHERE m = '{m_from}') / 1e9 AS DOUBLE)
            FROM y GROUP BY k, porte ORDER BY k, porte"""
    ).fetchall()


print("## 1. Totals (balance R$ bn, operations m, rows, rows with -1 operations)")
for r in con.execute(
    """SELECT cliente, m, round(CAST(sum(carteira_ativa) AS DOUBLE) / 1e9, 1),
              round(sum(numero_de_operacoes) FILTER (WHERE numero_de_operacoes > 0) / 1e6, 2),
              count(*), count(*) FILTER (WHERE numero_de_operacoes = -1)
       FROM s WHERE m BETWEEN '2025-04' AND '2025-10' GROUP BY ALL ORDER BY 1, 2"""
).fetchall():
    print("  ", r)

print("\n## 2. PF income band share of balance (%), month by month")
shares = con.execute(
    f"""SELECT m, value, share_pct FROM read_csv('{panel}', header=true)
        WHERE dim = 'income' AND m >= '2025-01' ORDER BY m"""
).fetchall()
bands = sorted({v for _, v, _ in shares})
months = sorted({m for m, _, _ in shares})
grid = {(m, v): s for m, v, s in shares}
print("  month   " + " | ".join(f"{short(b)[:14]:>14}" for b in bands))
for m in months:
    print(f"  {m} " + " | ".join(f"{grid.get((m, b), float('nan')):14.2f}" for b in bands))

print(
    f"\n## 3. PF bands, {M0} -> {M1}: share of balance, share of operations, balance per operation (R$ k)"
)
rows = con.execute(
    f"""SELECT m, porte, CAST(sum(carteira_ativa) AS DOUBLE),
              CAST(sum(numero_de_operacoes) FILTER (WHERE numero_de_operacoes > 0) AS DOUBLE)
       FROM s WHERE cliente = 'PF' AND m IN ('{M0}', '{M1}') GROUP BY ALL"""
).fetchall()
tb = {m: sum(r[2] for r in rows if r[0] == m) for m in (M0, M1)}
to = {m: sum(r[3] or 0 for r in rows if r[0] == m) for m in (M0, M1)}
d = {(r[0], r[1]): r for r in rows}
for b in sorted({r[1] for r in rows}):
    a, z = d[(M0, b)], d[(M1, b)]
    sb0, sb1 = 100 * a[2] / tb[M0], 100 * z[2] / tb[M1]
    so0, so1 = 100 * (a[3] or 0) / to[M0], 100 * (z[3] or 0) / to[M1]
    t0, t1 = a[2] / (a[3] or 1) / 1e3, z[2] / (z[3] or 1) / 1e3
    print(
        f"  {short(b):<22} balance {sb0:6.2f} -> {sb1:6.2f} ({sb1 - sb0:+.2f}) | "
        f"operations {so0:6.2f} -> {so1:6.2f} ({so1 - so0:+.2f}) | R$k/op {t0:7.1f} -> {t1:7.1f}"
    )

print("\n## 4a. PJ size share of PJ balance (%), 2025-04..09")
for r in con.execute(
    """WITH x AS (SELECT m, porte, sum(carteira_ativa) AS b FROM s
                  WHERE cliente = 'PJ' AND m BETWEEN '2025-04' AND '2025-09' GROUP BY ALL),
            y AS (SELECT m, porte, 100 * b / sum(b) OVER (PARTITION BY m) AS sh FROM x)
       SELECT porte, list(round(sh, 2) ORDER BY m) FROM y GROUP BY porte ORDER BY porte"""
).fetchall():
    print(f"  {r[0]:<14} {r[1]}")
print(f"\n## 4b. PF occupation ({occ}) share of PF balance (%), 2025-04..09")
for r in con.execute(
    f"""WITH x AS (SELECT m, {occ} AS o, sum(carteira_ativa) AS b FROM s
                   WHERE cliente = 'PF' AND m BETWEEN '2025-04' AND '2025-09' GROUP BY ALL),
             y AS (SELECT m, o, 100 * b / sum(b) OVER (PARTITION BY m) AS sh FROM x)
        SELECT o, list(round(sh, 2) ORDER BY m) FROM y GROUP BY o ORDER BY o"""
).fetchall():
    print(f"  {r[0][:40]:<40} {r[1]}")

print(
    "\n## 5. PF rates by band (%), 2025-05..2025-08: d15 = 15-90 days, d90 = carteira_inadimplencia"
)
for r in con.execute(
    f"""SELECT value, list(round(d15, 2) ORDER BY m), list(round(d90, 2) ORDER BY m)
        FROM read_csv('{panel}', header=true)
        WHERE dim = 'income' AND m BETWEEN '2025-05' AND '2025-08' GROUP BY value ORDER BY value"""
).fetchall():
    print(f"  {short(r[0]):<22} d15 {r[1]}  d90 {r[2]}")


def breadth(m0: str, m1: str, band: str) -> str:
    """Share of PF balance (at m1) in cells where the band's within-cell share rose / fell by >1 pp."""
    r = con.execute(
        f"""WITH c AS (
              SELECT segmento, modalidade, uf, {occ},
                sum(carteira_ativa) FILTER (WHERE m = '{m0}') AS t0,
                sum(carteira_ativa) FILTER (WHERE m = '{m1}') AS t1,
                coalesce(sum(carteira_ativa) FILTER (WHERE m = '{m0}' AND porte = '{band}'), 0) AS b0,
                coalesce(sum(carteira_ativa) FILTER (WHERE m = '{m1}' AND porte = '{band}'), 0) AS b1
              FROM s WHERE cliente = 'PF' AND m IN ('{m0}', '{m1}') GROUP BY ALL
              HAVING t0 > 0 AND t1 > 0)
            SELECT CAST(sum(t1) FILTER (WHERE 100 * (b1 / t1 - b0 / t0) > 1) / sum(t1) AS DOUBLE),
                   CAST(sum(t1) FILTER (WHERE 100 * (b1 / t1 - b0 / t0) < -1) / sum(t1) AS DOUBLE),
                   count(*)
            FROM c"""
    ).fetchone()
    return f"rose >1pp in cells holding {100 * r[0]:.0f}% of balance, fell >1pp in {100 * r[1]:.0f}% ({r[2]} cells)"


print("\n## 6. Breadth inside segment x modality x UF x occupation cells")
for m0, m1, band, label in [
    (M0, M1, TOP, "2025-07 event"),
    ("2025-05", "2025-06", TOP, "ordinary month"),
    ("2024-04", "2024-05", TOP, "ordinary month"),
    ("2023-12", "2024-01", TOP, "January (expect falls)"),
    ("2026-04", "2026-05", LOW, "2026-05 bank event (expect falls)"),
]:
    print(f"  {m0} -> {m1} {short(band)} [{label}]: {breadth(m0, m1, band)}")

print(
    f"\n## 7. Within PF sub-modality (15 largest in {M0}): share of Acima de 20 / 1 a 2 / Até 1 SM, {M0} -> {M1}"
)
sub = shares_by("submodalidade", "PF", M0, M1)
size = {}
for k, _p, _l, b in sub:
    size[k] = size.get(k, 0) + (b or 0)
for k in sorted(size, key=size.get, reverse=True)[:15]:
    cells = {p: lst for kk, p, lst, _ in sub if kk == k}
    out = " | ".join(
        f"{short(p)} {cells.get(p, [0, 0])[0]:.1f}->{cells.get(p, [0, 0])[-1]:.1f}"
        for p in (TOP, ONE_TWO, LOW)
    )
    print(f"  {k[:60]:<60} R${size[k]:7.1f}bn | {out}")

print(f"\n## 8. Within PF occupation: share of Acima de 20 / 1 a 2 / Até 1 SM, {M0} -> {M1}")
occ_rows = shares_by(occ, "PF", M0, M1)
for k in sorted({r[0] for r in occ_rows}):
    cells = {p: lst for kk, p, lst, _ in occ_rows if kk == k}
    out = " | ".join(
        f"{short(p)} {cells.get(p, [0, 0])[0]:.1f}->{cells.get(p, [0, 0])[-1]:.1f}"
        for p in (TOP, ONE_TWO, LOW)
    )
    print(f"  {k[:40]:<40} {out}")

print(f"\n## 9. Within lender segment: PJ size shares, {M0} -> {M1}")
for k, p, lst, b in shares_by("segmento", "PJ", M0, M1):
    if b and b > 5:
        print(f"  {k[:28]:<28} {p:<14} {lst}")

print(f"\n## 10. PF rows and rows with -1 operations, by band, {M0} -> {M1}")
for r in con.execute(
    f"""SELECT porte, list(n ORDER BY m), list(neg ORDER BY m) FROM (
          SELECT porte, m, count(*) AS n, count(*) FILTER (WHERE numero_de_operacoes = -1) AS neg
          FROM s WHERE cliente = 'PF' AND m IN ('{M0}', '{M1}') GROUP BY ALL)
        GROUP BY porte ORDER BY porte"""
).fetchall():
    print(f"  {short(r[0]):<22} rows {r[1]}  -1 rows {r[2]}")

if len(sys.argv) > 3:
    months_dir = sys.argv[3]
    print(f"\n## 11. V1 files ({months_dir}/planilha_*.csv): share of balance, {M0} -> {M1}")
    for dim, cliente in (("porte", "PF"), ("porte", "PJ"), ("ocupacao", "PF")):
        v1 = {}
        for m in (M0, M1):
            f = f"{months_dir}/planilha_{m.replace('-', '')}.csv"
            v1[m] = dict(
                con.execute(
                    f"""SELECT {dim}, sum(CAST(replace(carteira_ativa, ',', '.') AS DOUBLE))
                        FROM read_csv('{f}', delim=';', header=true, all_varchar=true)
                        WHERE cliente = '{cliente}' GROUP BY 1"""
                ).fetchall()
            )
        t0, t1 = sum(v1[M0].values()), sum(v1[M1].values())
        print(f"  {cliente} {dim}")
        for k in sorted(v1[M0]):
            s0, s1 = 100 * v1[M0][k] / t0, 100 * v1[M1].get(k, 0) / t1
            print(f"    {short(k)[:45]:<45} {s0:6.2f} -> {s1:6.2f} ({s1 - s0:+.2f})")
