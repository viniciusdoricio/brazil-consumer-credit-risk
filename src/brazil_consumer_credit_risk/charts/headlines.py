"""Each chart's headline, chosen from the data.

The v1 decision wrote every headline in advance as a claim with a slot, with the headline that
replaces it if the data says the opposite (docs/v1-decision.md, section 4). These functions fill
the slot and pick the branch from the analysis models, using thresholds fixed here rather than
chosen after looking. Each returns the headline, a subtitle that states the numbers behind it,
and those numbers as facts, which the write-up cites. The branch and the facts don't depend on
the language; only the wording does (`language`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .language import PT, Language
from .style import INCOME_BANDS

# A rate difference under 0.1 pp counts as no difference, as in analysis_gap_decomposition.
MATERIAL = 0.001
# The dbt test's definition of a visible January 2025 break
# (tests/dbt/assert_january_2025_break_exists.sql).
BREAK_D90_STEP = 0.0025
BREAK_D90_MULTIPLE = 5
BREAK_D15_TOLERANCE = 0.001
# The v1 decision's falsification rule: a product-mix part above half the gap means the gap is
# mostly about which products each group holds (docs/v1-decision.md, section 6).
PRODUCT_MIX_MAJORITY = 0.5
# At most a quarter of the gap counts as "little" of it; between a quarter and a half, as "less than
# half".
PRODUCT_MIX_LITTLE = 0.25
# A correlation at least this strong, either way, across the calendar years counts as the
# occupation spread moving with unemployment. Eight points can't support a finer reading.
UNEMPLOYMENT_CORRELATION = 0.5
# A component explains a change "mostly" when it has the change's sign and over half its size.
MOSTLY = 0.5

COMPONENTS = ("pure_rate", "product_mix", "borrower_mix")


@dataclass
class Headline:
    title: str
    subtitle: str
    facts: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A sentence that ends on "p.p." takes no second full stop.
        self.subtitle = self.subtitle.replace("p.p..", "p.p.")


def _at(frame: pd.DataFrame, column: str, month: str) -> float:
    rows = frame.loc[pd.to_datetime(frame["month"]) == pd.Timestamp(month), column]
    if len(rows) != 1:
        raise ValueError(f"expected one row for {month}, found {len(rows)}")
    return float(rows.iloc[0])


def the_trap(monthly: pd.DataFrame, lang: Language = PT) -> Headline:
    """Chart 1. monthly: mart_pf_monthly (month, d90_rate, d15_rate)."""
    d90 = _at(monthly, "d90_rate", "2025-01-01") - _at(monthly, "d90_rate", "2024-12-01")
    d90_before = _at(monthly, "d90_rate", "2024-01-01") - _at(monthly, "d90_rate", "2023-12-01")
    d15 = _at(monthly, "d15_rate", "2025-01-01") - _at(monthly, "d15_rate", "2024-12-01")
    d15_before = _at(monthly, "d15_rate", "2024-01-01") - _at(monthly, "d15_rate", "2023-12-01")
    visible = d90 >= BREAK_D90_STEP and d90 >= BREAK_D90_MULTIPLE * abs(d90_before)
    flat = abs(d15) <= BREAK_D15_TOLERANCE

    branch = "hidden" if not visible else ("flat" if flat else "jumped")
    subtitle = lang.t(
        "trap.subtitle",
        d90=lang.pp(d90, sign=True),
        d90_before=lang.pp(d90_before, sign=True),
        d15=lang.pp(d15, sign=True),
        d15_before=lang.pp(d15_before, sign=True),
    )
    return Headline(
        lang.t(f"trap.title.{branch}"),
        subtitle,
        {
            "d90_step_january_2025": d90,
            "d90_step_january_2024": d90_before,
            "d15_step_january_2025": d15,
            "d15_step_january_2024": d15_before,
            "break_visible": visible,
            "d15_flat": flat,
        },
    )


def the_grid(grid: pd.DataFrame, period: str, lang: Language = PT) -> Headline:
    """Chart 2. grid: analysis_grid rows for one window and the primary grid."""
    cells = grid[~grid["below_minimum_size"] & grid["income_band"].isin(INCOME_BANDS)]
    spreads = []
    for band, group in cells.groupby("income_band"):
        top = group.loc[group["d90_rate"].idxmax()]
        bottom = group.loc[group["d90_rate"].idxmin()]
        spreads.append(
            {
                "income_band": band,
                "highest": top["occupation"],
                "lowest": bottom["occupation"],
                "spread": float(top["d90_rate"] - bottom["d90_rate"]),
                "holds_with_lag": bool(top["d90_rate_lagged"] > bottom["d90_rate_lagged"]),
            }
        )
    held = [s for s in spreads if s["holds_with_lag"]]
    largest = max(held, key=lambda s: s["spread"], default=None)

    if largest is None or largest["spread"] < MATERIAL:
        subtitle = lang.t("grid.subtitle.flat", period=period, material=lang.pp(MATERIAL, 1))
        return Headline(lang.t("grid.title.flat"), subtitle, {"spreads": spreads})

    smallest = min(s["spread"] for s in spreads)
    subtitle = lang.t(
        "grid.subtitle",
        period=period,
        high=lang.label("occupation_in_text", largest["highest"]),
        low=lang.label("occupation_in_text", largest["lowest"]),
        band=lang.label("band_in_text", largest["income_band"]),
        smallest=lang.pp(smallest),
    )
    return Headline(
        lang.t("grid.title", spread=lang.pp(largest["spread"])),
        subtitle,
        {"largest_spread": largest, "smallest_spread": smallest, "spreads": spreads},
    )


def which_matters_more(dispersion: pd.DataFrame, lang: Language = PT) -> Headline:
    """Chart 3. dispersion: analysis_dispersion, primary variant."""
    d90 = dispersion[dispersion["measure"] == "d90"]
    windows = d90[d90["period_kind"] == "window"].sort_values("start_month")
    years = d90[d90["period_kind"] == "calendar_year"].sort_values("start_month")
    ratios = windows["occupation_to_income_ratio"].tolist()

    if all(r < 1 for r in ratios):
        verdict = "income"
    elif all(r > 1 for r in ratios):
        verdict = "occupation"
    else:
        verdict = "mixed"

    correlation = float(
        years["spread_across_occupations_within_bands"].corr(years["unemployment_rate"])
    )
    if correlation >= UNEMPLOYMENT_CORRELATION:
        clause = "with"
    elif correlation <= -UNEMPLOYMENT_CORRELATION:
        clause = "against"
    else:
        clause = "neither"

    d15_years = dispersion[
        (dispersion["measure"] == "d15")
        & (dispersion["period_kind"] == "calendar_year")
        & (dispersion["occupation_to_income_ratio"] > 1)
    ]["period_id"].tolist()
    subtitle = lang.t(
        "dispersion.subtitle",
        windows=", ".join(_window_name(row, lang) for _, row in windows.iterrows()),
        ratios=lang.join(lang.number(r) for r in ratios),
        first=years["period_id"].iloc[0],
        last=years["period_id"].iloc[-1],
        correlation=lang.number(correlation),
        years=lang.count(len(years)),
    )
    if d15_years:
        subtitle += lang.t("dispersion.d15", years=lang.join(d15_years))
    return Headline(
        lang.t(f"dispersion.title.{verdict}") + lang.t(f"dispersion.{clause}"),
        subtitle,
        {
            "verdict": verdict,
            "window_ratios": dict(zip(windows["period_id"], ratios, strict=True)),
            "unemployment_correlation": correlation,
            "d15_years_above_one": d15_years,
        },
    )


def _window_name(row, lang: Language) -> str:
    start, end = pd.Timestamp(row["start_month"]), pd.Timestamp(row["end_month"])
    if start.month == 1 and end.month == 12:
        return str(start.year)
    return lang.month_range(start, end)


def stable_bands(gaps: pd.DataFrame, pair: str, scope: str) -> pd.DataFrame:
    """The bands where a pair's split can be read: a material gap, above the minimum size, in the
    same order with lagged denominators, and stable under the alternative product mapping."""
    rows = gaps[
        (gaps["pair_id"] == pair)
        & (gaps["product_scope"] == scope)
        & gaps["income_band"].isin(INCOME_BANDS)
    ]
    return rows[
        ~rows["below_minimum_size"]
        & (rows["gap"].abs() >= MATERIAL)
        & rows["gap_sign_holds_with_lag"].fillna(False).astype(bool)
        & rows["split_holds_under_alternative_mapping"].fillna(False).astype(bool)
    ]


def product_mix_share(bands: pd.DataFrame) -> float | None:
    """The product-mix part of the gap summed over bands, as a share of the summed gap; None if
    there are no bands or the gap changes sign between them, where a share means nothing."""
    if bands.empty or not ((bands["gap"] > 0).all() or (bands["gap"] < 0).all()):
        return None
    return float(bands["product_mix_gap"].sum() / bands["gap"].sum())


def job_or_product(
    gaps: pd.DataFrame,
    period: str,
    pair: str = "retiree_vs_self_employed",
    lang: Language = PT,
) -> Headline:
    """Chart 4. gaps: analysis_gap_decomposition rows for one window."""
    a, b = lang.label("pair_a", pair), lang.label("pair_b", pair)
    bands = stable_bands(gaps, pair, "all_products")
    share = product_mix_share(bands)
    share_without_rural = product_mix_share(stable_bands(gaps, pair, "excluding_rural"))

    if share is None:
        branch = "unstable"
    elif share > PRODUCT_MIX_MAJORITY:
        branch = "most"
    elif share > PRODUCT_MIX_LITTLE:
        branch = "less"
    else:
        branch = "little"
    title = lang.t(f"split.title.{branch}", a=a, b=b)
    title = title[0].upper() + title[1:]

    subtitle = lang.t("split.subtitle", period=period, a=a, b=b)
    if share is not None:
        lower = a if bands["gap"].iloc[0] < 0 else b
        where = (
            lang.t("split.where.one")
            if len(bands) == 1
            else lang.t("split.where.many", n=lang.count(len(bands), feminine=True))
        )
        subtitle += lang.t("split.share", where=where, lower=lower, share=lang.pct(share, 0))
        subtitle += (
            lang.t("split.rural", share=lang.pct(share_without_rural, 0))
            if share_without_rural is not None
            else "."
        )
    return Headline(
        title,
        subtitle,
        {
            "pair": pair,
            "stable_bands": [b for b in INCOME_BANDS if b in set(bands["income_band"])],
            "product_mix_share": share,
            "product_mix_share_excluding_rural": share_without_rural,
        },
    )


def episode_name(row) -> str:
    return f"{pd.Timestamp(row['month_0']).year}–{pd.Timestamp(row['month_1']).year}"


def dominant_component(row) -> str | None:
    """The component that explains most of an episode's change, or None if none does."""
    change = row["change"]
    name = max(COMPONENTS, key=lambda c: abs(row[c]))
    value = row[name]
    if abs(change) >= MATERIAL and value * change > 0 and abs(value) > MOSTLY * abs(change):
        return name
    return None


def mix_versus_rate(episodes: pd.DataFrame, lang: Language = PT) -> Headline:
    """Chart 5. episodes: analysis_shift_share, 90-day episodes, all occupations."""
    episodes = episodes.sort_values("month_0")
    dominant = [dominant_component(row) for _, row in episodes.iterrows()]
    first = pd.Timestamp(episodes["month_0"].iloc[0]).year
    last = pd.Timestamp(episodes["month_1"].iloc[-1]).year

    if dominant and dominant[0] is not None and len(set(dominant)) == 1:
        title = lang.t(
            "mix.title.shared",
            n=lang.count(len(episodes)),
            first=first,
            last=last,
            component=lang.label("component", dominant[0]),
        )
    else:
        biggest = episodes.loc[episodes["change"].abs().idxmax()]
        which = dominant_component(biggest)
        title = lang.t(
            "mix.title.biggest",
            direction=lang.t("mix.rise" if biggest["change"] > 0 else "mix.fall"),
            size=lang.pp(abs(biggest["change"])),
            episode=episode_name(biggest),
        )
        title += (
            lang.t("mix.came", component=lang.label("component", which))
            if which
            else lang.t("mix.no_source")
        )

    changes = "; ".join(
        f"{episode_name(row)}, {lang.pp(row['change'], sign=True)}"
        for _, row in episodes.iterrows()
    )
    subtitle = lang.t("mix.subtitle", changes=changes)
    flagged = [
        episode_name(row)
        for _, row in episodes.iterrows()
        if row["spans_occupation_reclassification"]
    ]
    if flagged:
        subtitle += lang.t("mix.flagged", episodes=lang.join(f"{name}*" for name in flagged))
    return Headline(
        title,
        subtitle,
        {
            "dominant_component": dict(zip(episodes["comparison_id"], dominant, strict=True)),
            "episodes_with_reclassification": flagged,
        },
    )


def current_read(current: pd.DataFrame, lang: Language = PT) -> Headline:
    """Chart 6. current: analysis_current_read, named occupations."""
    latest = pd.Timestamp(current["latest_month"].iloc[0]).date()
    spread = float(current["d15_change"].max() - current["d15_change"].min())
    fastest = current.loc[current["d15_change"].idxmax()]
    fastest_lagged = current.loc[current["d15_change_lagged"].idxmax(), "occupation"]
    who = lang.label("occupation_in_text", fastest["occupation"])

    if spread < MATERIAL:
        title = lang.t("current.title.even")
    elif fastest_lagged != fastest["occupation"]:
        title = lang.t("current.title.depends")
    else:
        growth = "current.grew" if fastest["real_balance_growth"] > 0 else "current.shrank"
        title = lang.t("current.title.fastest", who=who, growth=lang.t(growth))
    subtitle = lang.t("current.base", latest=lang.month(latest)) + lang.t(
        "current.detail",
        who=who,
        change=lang.pp(fastest["d15_change"], sign=True),
        growth=lang.pct(fastest["real_balance_growth"], sign=True),
        low=lang.pp(current["d15_change"].min()),
        high=lang.pp(current["d15_change"].max()),
    )
    tightening = current.loc[current["possible_tightening"], "occupation"].tolist()
    if tightening:
        subtitle += lang.t(
            "current.tightening",
            who=lang.join(lang.label("occupation_in_text", o) for o in tightening),
        )
    return Headline(
        title,
        subtitle,
        {
            "latest_month": latest.isoformat(),
            "fastest": fastest["occupation"],
            "fastest_with_lagged_denominator": fastest_lagged,
            "spread": spread,
            "possible_tightening": tightening,
        },
    )
