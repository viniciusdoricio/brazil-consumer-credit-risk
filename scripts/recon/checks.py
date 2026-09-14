"""Structural checks on loaded SCR.data months.

    python checks.py recon.duckdb profile scrdata_202607
    python checks.py recon.duckdb recon planilha_202406 scrdata_202406

profile: grain, per-dimension values (split PF/PJ), cross-tab completeness of occupation x
income for PF, accounting identities, sentinels, national PF aggregates.
recon:   same month in V1 and V2 — do portfolio, overdue and problem-asset totals agree, by
occupation and by income band?
"""

import sys

import duckdb

con = duckdb.connect(sys.argv[1], read_only=True)
mode, tables = sys.argv[2], sys.argv[3:]


def q(sql):
    return con.execute(sql).fetchall()


def show(title, sql, limit=80):
    rows = con.execute(sql)
    names = [d[0] for d in rows.description]
    data = rows.fetchall()
    print(f"\n### {title}  ({len(data)} rows)")
    print("    " + " | ".join(names))
    for r in data[:limit]:
        print("    " + " | ".join(f"{v:,.2f}" if isinstance(v, float) else str(v) for v in r))
    if len(data) > limit:
        print(f"    ... {len(data) - limit} more")


def cols(t):
    return [r[0] for r in q(f"DESCRIBE {t}")]


def version(t):
    return "V2" if "submodalidade" in cols(t) else "V1"


def dims(t):
    return [
        c
        for c in cols(t)
        if not c.startswith(
            ("raw_", "a_vencer", "vencido", "carteira", "ativo_", "numero_de_operacoes")
        )
    ]


def profile(t):
    v = version(t)
    d = dims(t)
    occ = "cnae_ocupacao" if v == "V2" else "ocupacao"
    n = q(f"SELECT count(*) FROM {t}")[0][0]
    print(f"\n======== {t} ({v}) rows={n:,} dims={d}")

    distinct = q(f"SELECT count(*) FROM (SELECT DISTINCT {', '.join(d)} FROM {t})")[0][0]
    print(
        f"GRAIN: {n:,} rows, {distinct:,} distinct dimension tuples -> "
        f"{'UNIQUE' if n == distinct else 'NOT UNIQUE'}"
    )
    if n != distinct:
        show(
            "duplicate grain examples",
            f"SELECT {', '.join(d)}, count(*) k FROM {t} GROUP BY ALL HAVING k > 1 "
            "ORDER BY k DESC LIMIT 10",
        )

    # raw vs trimmed differences (whitespace traps)
    for c in d:
        if c == "data_base":
            continue
        k = q(f"SELECT count(*) FROM {t} WHERE raw_{c} <> {c}")[0][0]
        if k:
            print(f"WHITESPACE TRAP: {c} has {k:,} values with leading/trailing spaces")

    for c in d:
        if c == "data_base":
            show(f"{c}", f"SELECT data_base, count(*) FROM {t} GROUP BY 1")
            continue
        nd = q(f"SELECT count(DISTINCT {c}) FROM {t}")[0][0]
        nulls = q(f"SELECT count(*) FILTER (WHERE {c} IS NULL OR {c} = '') FROM {t}")[0][0]
        print(f"\n-- {c}: distinct={nd} null/empty={nulls}")
        if nd <= 120:
            show(
                f"{c} by cliente",
                f"SELECT cliente, {c}, count(*) n_rows, round(sum(carteira_ativa)/1e9, 3) ativa_bi "
                f"FROM {t} GROUP BY ALL ORDER BY cliente, ativa_bi DESC",
                limit=130,
            )

    print("\n======== CROSS-TAB TEST (PF): occupation x income")
    show(
        "PF occupation x income: rows and R$ bi per cell",
        f"PIVOT (SELECT {occ} occ, porte, round(sum(carteira_ativa)/1e9,1) bi FROM {t} "
        f"WHERE cliente='PF' GROUP BY ALL) ON porte USING first(bi) GROUP BY occ ORDER BY occ",
    )
    cells = q(
        f"SELECT count(DISTINCT {occ}), count(DISTINCT porte), "
        f"count(DISTINCT ({occ}, porte)) FROM {t} WHERE cliente='PF'"
    )[0]
    print(
        f"PF: {cells[0]} occupations x {cells[1]} income bands = {cells[0] * cells[1]} possible, "
        f"{cells[2]} populated"
    )
    show(
        "PF rows where occupation or income looks like a total/marginal placeholder",
        f"SELECT {occ}, porte, count(*) n, round(sum(carteira_ativa)/1e9,2) bi FROM {t} "
        f"WHERE cliente='PF' AND (lower({occ}) SIMILAR TO '.*(total|todos|-|indispon|não inf|"
        f"nao inf|n/a).*' OR lower(porte) SIMILAR TO '.*(total|todos|indispon|não inf|nao inf).*' "
        f"OR {occ} IN ('-','') OR porte IN ('-','')) GROUP BY ALL ORDER BY bi DESC",
    )

    print("\n======== IDENTITIES (row-level mismatches > R$0.05)")
    av = (
        "a_vencer_ate_90_dias + a_vencer_de_91_ate_360_dias + a_vencer_de_361_ate_1080_dias + "
        "a_vencer_de_1081_ate_1800_dias + a_vencer_de_1801_ate_5400_dias + "
        "a_vencer_acima_de_5400_dias"
    )
    if v == "V2":
        checks = {
            "carteira_a_vencer = sum(a_vencer_*)": f"abs(carteira_a_vencer - ({av}))",
            "carteira_vencida = v15_90 + v90": "abs(carteira_vencida - (vencido_de_15_ate_90_dias + vencido_acima_de_90_dias))",
            "carteira_ativa = a_vencer + vencida": "abs(carteira_ativa - (carteira_a_vencer + carteira_vencida))",
            "carteira_inadimplencia = vencido_acima_de_90_dias": "abs(carteira_inadimplencia - vencido_acima_de_90_dias)",
        }
        extra = {
            "ativo_problematico < carteira_inadimplencia": "ativo_problematico < carteira_inadimplencia - 0.05",
            "ativo_problematico > carteira_ativa": "ativo_problematico > carteira_ativa + 0.05",
            "any negative measure": " OR ".join(
                f"{c} < 0"
                for c in cols(t)
                if c.startswith(("a_vencer", "vencido", "carteira", "ativo_problematico"))
            ),
        }
    else:
        checks = {
            "carteira_ativa = sum(a_vencer_*) + vencido_acima_de_15_dias": f"abs(carteira_ativa - ({av} + vencido_acima_de_15_dias))",
        }
        extra = {
            "carteira_inadimplida_arrastada > carteira_ativa": "carteira_inadimplida_arrastada > carteira_ativa + 0.05",
            "ativo_problematico < carteira_inadimplida_arrastada": "ativo_problematico < carteira_inadimplida_arrastada - 0.05",
            "vencido_acima_de_15_dias > carteira_inadimplida_arrastada": "vencido_acima_de_15_dias > carteira_inadimplida_arrastada + 0.05",
            "any negative measure": " OR ".join(
                f"{c} < 0"
                for c in cols(t)
                if c.startswith(("a_vencer", "vencido", "carteira", "ativo_problematico"))
            ),
        }
    for name, expr in checks.items():
        k, worst, gap = q(
            f"SELECT count(*) FILTER (WHERE {expr} > 0.05), max({expr}), sum({expr}) FROM {t}"
        )[0]
        print(f"  {name}: {k:,} rows off; max gap {worst}; total abs gap {gap}")
    for name, cond in extra.items():
        k = q(f"SELECT count(*) FROM {t} WHERE {cond}")[0][0]
        print(f"  {name}: {k:,} rows")

    print("\n======== SENTINELS")
    show(
        "numero_de_operacoes raw values that are not positive integers",
        f"SELECT raw_numero_de_operacoes, count(*) n, round(sum(carteira_ativa)/1e9,2) bi FROM {t} "
        "WHERE numero_de_operacoes IS NULL OR numero_de_operacoes <= 0 GROUP BY 1 ORDER BY n DESC",
    )
    show(
        "numero_de_operacoes numeric range",
        f"SELECT min(numero_de_operacoes) FILTER (WHERE numero_de_operacoes > 0), "
        f"max(numero_de_operacoes), sum(numero_de_operacoes) FILTER (WHERE numero_de_operacoes > 0) FROM {t}",
    )

    print("\n======== NATIONAL AGGREGATES")
    if v == "V2":
        m = (
            "round(sum(carteira_ativa)/1e9,1) ativa_bi, "
            "round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa),3) pct_15_90, "
            "round(100*sum(vencido_acima_de_90_dias)/sum(carteira_ativa),3) pct_90, "
            "round(100*sum(carteira_inadimplencia)/sum(carteira_ativa),3) pct_inad, "
            "round(100*sum(ativo_problematico)/sum(carteira_ativa),3) pct_ap"
        )
    else:
        m = (
            "round(sum(carteira_ativa)/1e9,1) ativa_bi, "
            "round(100*sum(vencido_acima_de_15_dias)/sum(carteira_ativa),3) pct_venc15, "
            "round(100*sum(carteira_inadimplida_arrastada)/sum(carteira_ativa),3) pct_arrastada, "
            "round(100*sum(ativo_problematico)/sum(carteira_ativa),3) pct_ap"
        )
    show("by cliente", f"SELECT cliente, {m} FROM {t} GROUP BY 1 ORDER BY 1")
    show(
        "PF by occupation",
        f"SELECT {occ}, {m} FROM {t} WHERE cliente='PF' GROUP BY 1 ORDER BY 2 DESC",
    )
    show("PF by income", f"SELECT porte, {m} FROM {t} WHERE cliente='PF' GROUP BY 1 ORDER BY 1")


def recon(t1, t2):
    print(f"\n======== RECON {t1} (V1) vs {t2} (V2)")
    norm = "trim(regexp_replace({c}, '^P[FJ] - ', ''))"
    for label, c1, c2 in [
        ("cliente", "cliente", "cliente"),
        ("PF occupation", "ocupacao", "cnae_ocupacao"),
        ("PF income", "porte", "porte"),
        ("modalidade", "modalidade", "modalidade"),
        ("uf", "uf", "uf"),
    ]:
        where = "WHERE cliente='PF'" if label.startswith("PF") or label == "modalidade" else ""
        k1, k2 = norm.format(c=c1), norm.format(c=c2)
        show(
            f"{label}: carteira_ativa, >90 and problem assets, V1 vs V2 (R$ bi)",
            f"""
            WITH a AS (SELECT {k1} k, sum(carteira_ativa)/1e9 ativa, sum(carteira_inadimplida_arrastada)/1e9 inad,
                              sum(vencido_acima_de_15_dias)/1e9 v15, sum(ativo_problematico)/1e9 ap
                       FROM {t1} {where} GROUP BY 1),
                 b AS (SELECT {k2} k, sum(carteira_ativa)/1e9 ativa, sum(carteira_inadimplencia)/1e9 inad,
                              sum(vencido_acima_de_90_dias)/1e9 v90, sum(carteira_vencida)/1e9 venc,
                              sum(ativo_problematico)/1e9 ap
                       FROM {t2} {where} GROUP BY 1)
            SELECT coalesce(a.k, b.k) k,
                   round(a.ativa,2) v1_ativa, round(b.ativa,2) v2_ativa, round(b.ativa - a.ativa, 3) d_ativa,
                   round(a.inad,3) v1_arrastada, round(b.inad,3) v2_inad, round(b.v90,3) v2_v90,
                   round(a.v15,3) v1_venc15, round(b.venc,3) v2_vencida,
                   round(a.ap,3) v1_ap, round(b.ap,3) v2_ap
            FROM a FULL OUTER JOIN b ON a.k = b.k ORDER BY v2_ativa DESC NULLS LAST""",
            limit=60,
        )


if mode == "profile":
    for t in tables:
        profile(t)
elif mode == "recon":
    recon(*tables)
