"""The numbers the write-up quotes, computed once for both languages.

The Portuguese write-up (analysis/index.qmd, the reference version) and its English translation
(analysis/en/index.qmd) both call `facts`, `check` and `values`:

- `facts` computes every figure the text quotes, from the dbt models and the same headline rules
  the charts use, so the two versions can't quote different numbers;
- `check` asserts every qualitative claim the text makes, so a data release that reverses one
  stops both renders instead of publishing a sentence that is no longer true;
- `values` formats the figures in one language.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

from .charts import cli, figures
from .charts import headlines as h
from .charts.language import PT, Language
from .charts.style import INCOME_BANDS, PAIRS

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "brazil_consumer_credit_risk.duckdb"

RETIREES = "Aposentado/pensionista"
SELF_EMPLOYED = "Autônomo"
NON_PROFIT = "Empregado de entidades sem fins lucrativos"


def facts(database: Path = DATABASE) -> dict:
    """Every figure the write-up quotes, in no particular language."""
    with duckdb.connect(str(database), read_only=True) as con:
        return _facts(con)


def _facts(con: duckdb.DuckDBPyConnection) -> dict:
    frames = cli.load(con)
    design = yaml.safe_load((ROOT / "dbt_project.yml").read_text())["vars"]

    def one(sql, *params):
        return con.execute(sql, list(params)).fetchone()

    trap = h.the_trap(frames["monthly"])
    grid = h.the_grid(frames["grid"], cli.HEADLINE_PERIOD)
    dispersion = h.which_matters_more(frames["dispersion"])
    split = h.job_or_product(frames["gaps"], cli.HEADLINE_PERIOD)
    episodes = h.mix_versus_rate(frames["episodes"])
    current = h.current_read(frames["current"])
    f: dict = {}

    # The data
    f["first_month"], f["latest_month"], f["months"] = one(
        "select min(month), max(month), count(*) from mart_pf_monthly"
    )
    (f["portfolio_bn"],) = one(
        "select carteira_ativa / 1e9 from mart_pf_monthly where month = ?", f["latest_month"]
    )
    f["sgs_gap_low"], f["sgs_gap_high"] = one(
        """select min(d90_gap_to_sgs), max(d90_gap_to_sgs) from mart_pf_monthly
        where month between cast(? as date) and cast(? as date)""",
        design["first_comparable_month"],
        design["d90_last_comparable_month"],
    )
    (f["rural_self_employed"],) = one(
        """select sum(carteira_ativa) filter (where product_group = 'Rural')
            / sum(carteira_ativa)
        from mart_pf_cells where year(month) = 2024 and occupation = ?""",
        SELF_EMPLOYED,
    )
    f["outros_low"], f["outros_high"] = one(
        """select min(share), max(share) from (
            select year(month),
                sum(carteira_ativa) filter (where occupation = 'Outros') / sum(carteira_ativa)
                    as share
            from mart_pf_cells
            where month between cast(? as date) and cast(? as date)
            group by 1)""",
        design["first_comparable_month"],
        design["d90_last_comparable_month"],
    )
    (f["unexplained_jumps"],) = one(
        "select count(*) from classification_events "
        "where description like '%cause not established%'"
    )
    f["occupations"], f["income_bands"], f["product_groups"] = one(
        """select count(distinct occupation), count(distinct income_band),
            count(distinct product_group)
        from mart_pf_cells where year(month) = 2024"""
    )
    f["min_cell_balance_bn"] = design["min_cell_balance_bn"]
    f["max_crosswalk_shift"] = design["max_crosswalk_shift"]
    f["weight_jump_threshold"] = design["weight_jump_threshold"]
    f["material"] = h.MATERIAL

    # Chart 1
    f.update(trap.facts)
    f["bcb_regulatory_pp"] = figures.BCB_REGULATORY_PP
    f["bcb_total_pp"] = figures.BCB_TOTAL_PP

    # Chart 2
    grid_rows = frames["grid"]
    shown = grid_rows[~grid_rows["below_minimum_size"]]
    f["largest_spread"] = grid.facts["largest_spread"]
    f["smallest_spread"] = grid.facts["smallest_spread"]
    f["small_cells"] = int(grid_rows["below_minimum_size"].sum())
    f["small_cell_occupations"] = sorted(
        set(grid_rows.loc[grid_rows["below_minimum_size"], "occupation"])
    )
    f["bands_shown"] = shown["income_band"].nunique()
    f["top_two_riskiest"] = 0
    f["safest"] = 0
    for _, band in shown.groupby("income_band"):
        ranked = band.sort_values("d90_rate")["occupation"].tolist()
        f["top_two_riskiest"] += set(ranked[-2:]) == {"MEI", SELF_EMPLOYED}
        f["safest"] += ranked[0] in {"Servidor ou empregado público", RETIREES}

    # Chart 3
    calendar = frames["dispersion"][
        (frames["dispersion"]["measure"] == "d90")
        & (frames["dispersion"]["period_kind"] == "calendar_year")
    ]
    f.update(dispersion.facts)
    f["ratios"] = list(dispersion.facts["window_ratios"].values())
    f["years"] = len(calendar)
    f["every_year_below_one"] = bool((calendar["occupation_to_income_ratio"] < 1).all())

    # Chart 4
    gaps = frames["gaps"]
    named = gaps[
        (gaps["product_scope"] == "all_products")
        & gaps["income_band"].isin(INCOME_BANDS)
        & ~gaps["below_minimum_size"]
    ]
    f.update(split.facts)
    f["material_splits"] = int((named["gap"].abs() >= h.MATERIAL).sum())
    f["stable_by_pair"] = {pair: len(h.stable_bands(gaps, pair, "all_products")) for pair in PAIRS}
    f["pair_shares"] = {
        pair: h.product_mix_share(h.stable_bands(gaps, pair, "all_products")) for pair in PAIRS
    }
    by_product = (
        con.execute(
            """select product_group,
                sum(carteira_inadimplencia) filter (where occupation = $retirees)
                    / sum(carteira_ativa) filter (where occupation = $retirees) as retirees,
                sum(carteira_inadimplencia) filter (where occupation = $self_employed)
                    / sum(carteira_ativa) filter (where occupation = $self_employed)
                    as self_employed
            from int_cross_section_by_mapping
            where window_id = $window and product_scope = 'all_products'
                and product_mapping = 'primary' and list_contains($bands, income_band)
            group by 1""",
            {
                "retirees": RETIREES,
                "self_employed": SELF_EMPLOYED,
                "window": cli.HEADLINE_WINDOW,
                "bands": split.facts["stable_bands"],
            },
        )
        .df()
        .set_index("product_group")
    )
    same_product = (
        con.execute(
            """select product_group, sum(same_product_term) as term
            from int_gap_terms
            where pair_id = 'retiree_vs_self_employed' and window_id = ?
                and product_scope = 'all_products' and product_mapping = 'primary'
                and list_contains(?, income_band)
            group by 1""",
            [cli.HEADLINE_WINDOW, split.facts["stable_bands"]],
        )
        .df()
        .set_index("product_group")["term"]
    )
    f["product_rates"] = {
        product: (row["self_employed"], row["retirees"]) for product, row in by_product.iterrows()
    }
    f["top_product"] = same_product.abs().idxmax()
    f["top_product_share"] = float(same_product[f["top_product"]] / same_product.sum())
    f["widest_rate_gap"] = (by_product["self_employed"] - by_product["retirees"]).idxmax()
    f["self_employed_higher_everywhere"] = bool(
        (by_product["self_employed"] > by_product["retirees"]).all()
    )

    # Chart 5
    eps = frames["episodes"].sort_values("month_0")
    f["episodes"] = len(eps)
    f["dominant_components"] = sorted(set(episodes.facts["dominant_component"].values()))
    f["episodes_with_reclassification"] = episodes.facts["episodes_with_reclassification"]
    f["pure_low"] = float((eps["pure_rate"] / eps["change"]).min())
    f["pure_high"] = float((eps["pure_rate"] / eps["change"]).max())
    f["mix_max"] = float(((eps["product_mix"] + eps["borrower_mix"]) / eps["change"]).abs().max())
    flagged = eps[eps["spans_occupation_reclassification"]]
    f["flagged_borrower_mix"] = float(flagged["borrower_mix"].iloc[0]) if len(flagged) else None

    # Chart 6
    cur = frames["current"].set_index("occupation")
    f["fastest"] = current.facts["fastest"]
    f["fastest_with_lagged_denominator"] = current.facts["fastest_with_lagged_denominator"]
    f["slowest"] = cur["d15_change"].idxmin()
    for who in ("fastest", "slowest"):
        f[f"{who}_change"] = float(cur.loc[f[who], "d15_change"])
        f[f"{who}_growth"] = float(cur.loc[f[who], "real_balance_growth"])
    f["all_rising"] = bool((cur["d15_change"] > 0).all())
    return f


def check(f: dict) -> None:
    """The results the text is written for. Each failure names the claim that no longer holds."""
    claims = {
        "the January 2025 break shows in the 90-day rate and not the 15-90-day one": (
            f["break_visible"] and f["d15_flat"]
        ),
        "the undersized cells are all non-profit employees": (
            f["small_cell_occupations"] == [NON_PROFIT]
        ),
        "income separates risk more in all three windows": f["verdict"] == "income",
        "income separates risk more in every calendar year": f["every_year_below_one"],
        "the 15-90-day rate disagrees in exactly one year": len(f["d15_years_above_one"]) == 1,
        "the occupation spread doesn't track unemployment": (
            abs(f["unemployment_correlation"]) < h.UNEMPLOYMENT_CORRELATION
        ),
        "little of the retiree-self-employed gap comes from product mix": (
            f["product_mix_share"] is not None and f["product_mix_share"] <= h.PRODUCT_MIX_LITTLE
        ),
        "without rural credit, product mix is larger but under half": (
            f["product_mix_share_excluding_rural"] is not None
            and f["product_mix_share"]
            < f["product_mix_share_excluding_rural"]
            < h.PRODUCT_MIX_MAJORITY
        ),
        "the self-employed have the higher rate in every product": (
            f["self_employed_higher_everywhere"]
        ),
        "the product contributing most also has the widest rate gap": (
            f["widest_rate_gap"] == f["top_product"]
        ),
        "the other pairs' stable bands point the same way": all(
            share is not None and share < h.PRODUCT_MIX_MAJORITY
            for share in f["pair_shares"].values()
        ),
        "most bands of the other two pairs are unstable": all(
            f["stable_by_pair"][pair] < len(INCOME_BANDS) / 2
            for pair in ("public_vs_private_employee", "mei_vs_business_owner")
        ),
        "every episode moved mostly within occupation and product": (
            f["dominant_components"] == ["pure_rate"]
        ),
        "exactly one episode contains a reclassification": (
            len(f["episodes_with_reclassification"]) == 1
        ),
        "15-90-day delinquency rose for every occupation": f["all_rising"],
        "the fastest riser is the same with the lagged denominator": (
            f["fastest"] == f["fastest_with_lagged_denominator"]
        ),
        "lending to the fastest riser kept growing": f["fastest_growth"] > 0,
    }
    broken = [claim for claim, holds in claims.items() if not holds]
    if broken:
        raise AssertionError("no longer true, so the text needs rewriting: " + "; ".join(broken))


def values(f: dict, lang: Language = PT) -> dict[str, str]:
    """Every figure the text quotes, formatted in one language."""
    L = lang
    occupation = lambda key: L.label("occupation_in_text", key)  # noqa: E731
    largest = f["largest_spread"]
    card = f["product_rates"]["Cartão"]
    payroll = f["product_rates"]["Consignado"]
    return {
        "months": str(f["months"]),
        "first_month": L.month(f["first_month"]),
        "latest_month": L.month(f["latest_month"]),
        "portfolio": L.t("report.trillion", value=L.number(f["portfolio_bn"] / 1000, 1)),
        "sgs_gap_low": L.pp(f["sgs_gap_low"], sign=True),
        "sgs_gap_high": L.pp(f["sgs_gap_high"], sign=True),
        "rural_self_employed": L.pct(f["rural_self_employed"], 0),
        "outros_low": L.pct(f["outros_low"], 0),
        "outros_high": L.pct(f["outros_high"], 0),
        "unexplained_jumps": L.count(f["unexplained_jumps"]),
        "occupations": L.count(f["occupations"], feminine=True),
        "income_bands": L.count(f["income_bands"], feminine=True),
        "product_groups": L.count(f["product_groups"]),
        "min_cell": L.t("report.billion", value=L.number(f["min_cell_balance_bn"], 0)),
        "material": L.pp(f["material"], 1),
        "crosswalk_shift": L.pct(f["max_crosswalk_shift"], 0),
        "weight_jump": L.pp(f["weight_jump_threshold"], 1),
        "bcb_regulatory": f"{L.number(f['bcb_regulatory_pp'])} {L.pp_unit}",
        "bcb_total": f"{L.number(f['bcb_total_pp'])} {L.pp_unit}",
        "d90_step": L.pp(f["d90_step_january_2025"], sign=True),
        "d90_step_before": L.pp(f["d90_step_january_2024"], sign=True),
        "d15_step": L.pp(f["d15_step_january_2025"], sign=True),
        "d15_step_before": L.pp(f["d15_step_january_2024"], sign=True),
        "grid_spread": L.pp(largest["spread"], 1),
        "grid_high": occupation(largest["highest"]),
        "grid_low": occupation(largest["lowest"]),
        "grid_band": L.label("band_in_text", largest["income_band"]),
        "grid_smallest": L.pp(f["smallest_spread"]),
        "small_cells": L.count(f["small_cells"], feminine=True),
        "bands_shown": L.count(f["bands_shown"], feminine=True),
        "top_two_riskiest": L.count(f["top_two_riskiest"], feminine=True),
        "safest": L.count(f["safest"]),
        "ratio_low": L.number(min(f["ratios"])),
        "ratio_high": L.number(max(f["ratios"])),
        "correlation": L.number(f["unemployment_correlation"]),
        "years": L.count(f["years"]),
        "d15_years": L.join(f["d15_years_above_one"]),
        "split_bands": L.count(len(f["stable_bands"]), feminine=True),
        "split_band_names": L.t(
            "report.bands", bands=L.join(L.label("band", b).lower() for b in f["stable_bands"])
        ),
        "mix_share": L.pct(f["product_mix_share"], 0),
        "mix_share_no_rural": L.pct(f["product_mix_share_excluding_rural"], 0),
        "material_splits": str(f["material_splits"]),
        "stable_splits": L.count(sum(f["stable_by_pair"].values())),
        "public_share": L.pct(f["pair_shares"]["public_vs_private_employee"], 0),
        "mei_share": L.pct(f["pair_shares"]["mei_vs_business_owner"], 0),
        "top_product": L.label("product_in_text", f["top_product"]),
        "top_product_share": L.pct(f["top_product_share"], 0),
        "card_self_employed": L.pct(card[0]),
        "card_retirees": L.pct(card[1]),
        "payroll_self_employed": L.pct(payroll[0]),
        "payroll_retirees": L.pct(payroll[1]),
        "episodes": L.count(f["episodes"]),
        "pure_low": L.pct(f["pure_low"], 0),
        "pure_high": L.pct(f["pure_high"], 0),
        "mix_max": L.pct(f["mix_max"], 0),
        "flagged_episode": f["episodes_with_reclassification"][0],
        "flagged_borrower_mix": L.pp(f["flagged_borrower_mix"], sign=True),
        "fastest": occupation(f["fastest"]),
        "fastest_change": L.pp(f["fastest_change"], sign=True),
        "fastest_growth": L.pct(f["fastest_growth"], sign=True),
        "slowest": occupation(f["slowest"]),
        "slowest_change": L.pp(f["slowest_change"], sign=True),
        "slowest_growth": L.pct(f["slowest_growth"], sign=True),
    }
