"""Recompute the report's headline numbers from the raw monthly files and compare.

    uv run python scripts/audit.py        (or: make audit)

The report's numbers come from the dbt models, through the headline rules in
src/brazil_consumer_credit_risk. This script takes none of that path: it reads the monthly Parquet
files that fetch-data writes, with its own SQL and its own arithmetic, and checks that it arrives
at the same values as `report.facts()`. It uses only two inputs from the pipeline, both design
choices rather than computations: the product grouping seed, and which pairs, bands and months
the report quotes. It exits with an error if any value differs by more than 1e-9.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from brazil_consumer_credit_risk import report

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "parquet" / "scrdata" / "scrdata_*.parquet"
BANDS = [
    "Até 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos",
    "Mais de 2 a 3 salários mínimos",
    "Mais de 3 a 5 salários mínimos",
    "Mais de 5 a 10 salários mínimos",
    "Mais de 10 a 20 salários mínimos",
    "Acima de 20 salários mínimos",
]
RETIREES, SELF_EMPLOYED = "Aposentado/pensionista", "Autônomo"
TOLERANCE = 1e-9


def household(con: duckdb.DuckDBPyConnection) -> None:
    # The two label defects BCB's files carry (docs/data-dictionary.md, section 2.1): a
    # Windows-1252 en dash read as U+0096, and a doubled space in the rural modality.
    con.execute(
        f"""create view pf as select * replace (
            regexp_replace(replace(modalidade, chr(150), '–'), ' {{2,}}', ' ', 'g') as modalidade,
            regexp_replace(replace(submodalidade, chr(150), '–'), ' {{2,}}', ' ', 'g')
                as submodalidade)
        from '{PARQUET}' where cliente = 'PF'"""
    )


def rate(con, measure: str, where: str) -> float:
    return con.execute(
        f"select sum({measure}) / sum(carteira_ativa) from pf where {where}"
    ).fetchone()[0]


def january_steps(con) -> dict[str, float]:
    def step(measure, december, january):
        return rate(con, measure, f"data_base = '{january}'") - rate(
            con, measure, f"data_base = '{december}'"
        )

    return {
        "d90_step_january_2025": step("carteira_inadimplencia", "2024-12-31", "2025-01-31"),
        "d90_step_january_2024": step("carteira_inadimplencia", "2023-12-31", "2024-01-31"),
        "d15_step_january_2025": step("vencido_de_15_ate_90_dias", "2024-12-31", "2025-01-31"),
        "d15_step_january_2024": step("vencido_de_15_ate_90_dias", "2023-12-31", "2024-01-31"),
    }


def largest_gap(con, spread: dict) -> float:
    in_band = f"year(data_base) = 2024 and porte = '{spread['income_band']}'"
    high = rate(
        con, "carteira_inadimplencia", f"{in_band} and cnae_ocupacao = '{spread['highest']}'"
    )
    low = rate(con, "carteira_inadimplencia", f"{in_band} and cnae_ocupacao = '{spread['lowest']}'")
    return high - low


def dispersion_ratio_2024(con, min_cell_bn: float) -> float:
    """Spread of occupation rates within bands over spread of band rates within occupations,
    each a balance-weighted standard deviation around the group's own rate, averaged by balance."""
    cells = con.execute(
        """select cnae_ocupacao as occupation, porte as band,
            sum(carteira_ativa) as balance, sum(carteira_inadimplencia) as overdue
        from pf where year(data_base) = 2024 group by all"""
    ).df()
    cells = cells[
        cells["band"].isin(BANDS)
        & (cells["occupation"] != "Outros")
        & (cells["balance"] / 12 / 1e9 >= min_cell_bn)
    ].assign(rate=lambda c: c["overdue"] / c["balance"])

    def average_spread(by: str) -> float:
        weights, spreads = [], []
        for _, group in cells.groupby(by):
            centre = group["overdue"].sum() / group["balance"].sum()
            variance = (group["balance"] * (group["rate"] - centre) ** 2).sum()
            weights.append(group["balance"].sum())
            spreads.append(np.sqrt(variance / group["balance"].sum()))
        return float(np.average(spreads, weights=weights))

    return average_spread("band") / average_spread("occupation")


def retiree_split(con, bands: list[str]) -> tuple[float, tuple[float, float]]:
    """The product-mix share of the retiree-self-employed gap summed over the given bands, and
    each group's card rate pooled over them."""
    con.register("groups", pd.read_csv(ROOT / "seeds" / "pf_product_groups.csv"))
    cells = con.execute(
        """select cnae_ocupacao as occupation, porte as band, g.product_group as product,
            sum(carteira_ativa) as balance, sum(carteira_inadimplencia) as overdue
        from pf join groups as g using (modalidade, submodalidade)
        where year(data_base) = 2024 and cnae_ocupacao in (?, ?) and list_contains(?, porte)
        group by all""",
        [RETIREES, SELF_EMPLOYED, bands],
    ).df()
    gap = mix = 0.0
    for _, band in cells.groupby("band"):
        table = band.pivot_table(
            index="product", columns="occupation", values=["balance", "overdue"]
        )
        table = table.fillna(0)
        share = table["balance"] / table["balance"].sum()
        rates = (table["overdue"] / table["balance"]).replace([np.inf], np.nan)
        rates = rates.apply(lambda row: row.fillna(row.mean()), axis=1)
        gap += (
            table["overdue"][RETIREES].sum() / table["balance"][RETIREES].sum()
            - table["overdue"][SELF_EMPLOYED].sum() / table["balance"][SELF_EMPLOYED].sum()
        )
        mix += (
            (rates[RETIREES] + rates[SELF_EMPLOYED]) / 2 * (share[RETIREES] - share[SELF_EMPLOYED])
        ).sum()
    cards = cells[cells["product"] == "Cartão"].groupby("occupation")[["overdue", "balance"]].sum()
    card_rates = cards["overdue"] / cards["balance"]
    return mix / gap, (float(card_rates[SELF_EMPLOYED]), float(card_rates[RETIREES]))


def early_arrears_change(con, occupation: str, latest: date) -> float:
    last_12 = f"data_base > date '{latest}' - interval 11 month and cnae_ocupacao = '{occupation}'"
    in_2024 = f"year(data_base) = 2024 and cnae_ocupacao = '{occupation}'"
    return rate(con, "vencido_de_15_ate_90_dias", last_12) - rate(
        con, "vencido_de_15_ate_90_dias", in_2024
    )


def main() -> int:
    facts = report.facts()
    con = duckdb.connect()
    household(con)
    latest = pd.Timestamp(facts["latest_month"]).date()
    split, cards = retiree_split(con, facts["stable_bands"])

    checks = {**{k: (facts[k], v) for k, v in january_steps(con).items()}}
    checks["largest_spread"] = (
        facts["largest_spread"]["spread"],
        largest_gap(con, facts["largest_spread"]),
    )
    checks["window_ratio_cs_2024"] = (
        facts["window_ratios"]["cs_2024"],
        dispersion_ratio_2024(con, facts["min_cell_balance_bn"]),
    )
    checks["product_mix_share"] = (facts["product_mix_share"], split)
    checks["card_rate_self_employed"] = (facts["product_rates"]["Cartão"][0], cards[0])
    checks["card_rate_retirees"] = (facts["product_rates"]["Cartão"][1], cards[1])
    for who in ("fastest", "slowest"):
        checks[f"{who}_change"] = (
            facts[f"{who}_change"],
            early_arrears_change(con, facts[who], latest),
        )

    failed = 0
    print(f"{'value':28} {'report':>14} {'recomputed':>14}")
    for name, (published, recomputed) in checks.items():
        ok = abs(published - recomputed) <= TOLERANCE
        failed += not ok
        print(f"{name:28} {published:14.10f} {recomputed:14.10f}  {'ok' if ok else 'DIFFERENT'}")
    print(f"\n{len(checks) - failed} of {len(checks)} agree to {TOLERANCE:g}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
